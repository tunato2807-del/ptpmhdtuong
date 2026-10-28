"""Native PostgreSQL custom-format backup, verified restore into a NEW database."""

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import psycopg
from psycopg import sql
from django.conf import settings
from django.core.management.base import CommandError


def binary(name):
    folder = os.getenv("POSTGRES_BIN", "")
    candidates = [Path(folder) / name, Path(folder) / (name + ".exe")] if folder else []
    found = shutil.which(name)
    if found:
        candidates.append(Path(found))
    if os.name == "nt":
        for directory in sorted(Path("C:/Program Files/PostgreSQL").glob("*/bin"), reverse=True):
            candidates.append(directory / (name + ".exe"))
    for path in candidates:
        if path.is_file():
            return str(path)
    raise CommandError(
        "Không tìm thấy " + name + ". Đặt POSTGRES_BIN trỏ tới thư mục bin của PostgreSQL."
    )


def params(database=None):
    config = settings.DATABASES["default"]
    return dict(
        dbname=database or config["NAME"],
        host=config["HOST"],
        port=config["PORT"],
        user=config["USER"],
        password=config["PASSWORD"],
        connect_timeout=10,
    )


def run(name, args, database=None):
    config = settings.DATABASES["default"]
    env = os.environ.copy()
    env["PGPASSWORD"] = str(config["PASSWORD"])
    result = subprocess.run(
        [
            binary(name),
            "--host",
            str(config["HOST"]),
            "--port",
            str(config["PORT"]),
            "--username",
            str(config["USER"]),
            "--no-password",
            *map(str, args),
        ],
        env=env,
        capture_output=True,
    )
    if result.returncode:
        # Avoid echoing environment values or a connection string into public logs.
        raise CommandError(
            name
            + " thất bại. Kiểm tra kết nối, quyền và phiên bản PostgreSQL; database đang dùng không bị thay thế."
        )
    return result


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def counts(conn):
    result = {}
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
        )
        tables = [row[0] for row in cursor.fetchall()]
        for table in tables:
            cursor.execute(sql.SQL("SELECT count(*) FROM public.{}").format(sql.Identifier(table)))
            result[table] = cursor.fetchone()[0]
    return result


def backup(output):
    output = Path(output).resolve()
    metadata_path = output.with_suffix(output.suffix + ".json")
    if output.exists() or metadata_path.exists():
        raise CommandError("File đích đã tồn tại. Chọn tên mới để giữ bản sao lưu cũ.")
    output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = output.with_suffix(output.suffix + ".partial")
    if temporary.exists():
        raise CommandError("Đã có file .partial. Chọn tên sao lưu khác.")
    try:
        with psycopg.connect(**params()) as conn:
            conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            table_counts = counts(conn)
            snapshot = conn.execute("SELECT pg_export_snapshot()").fetchone()[0]
            # pg_dump and the row counts use the SAME snapshot even during writes.
            run(
                "pg_dump",
                [
                    "--format=custom",
                    "--no-owner",
                    "--no-acl",
                    "--snapshot",
                    snapshot,
                    "--file",
                    temporary,
                    "--dbname",
                    settings.DATABASES["default"]["NAME"],
                ],
            )
        run("pg_restore", ["--list", temporary])
        temporary.chmod(0o600)
        metadata = {
            "format": 1,
            "created": datetime.now(timezone.utc).isoformat(),
            "source_database": settings.DATABASES["default"]["NAME"],
            "sha256": digest(temporary),
            "counts": table_counts,
        }
        metadata_path.write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        metadata_path.chmod(0o600)
        temporary.replace(output)
        return output, table_counts
    except BaseException:
        temporary.unlink(missing_ok=True)
        metadata_path.unlink(missing_ok=True)
        raise


def restore(source, target, confirmation):
    source = Path(source).resolve()
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,62}", target or "") or confirmation != target:
        raise CommandError(
            "Tên database mới phải hợp lệ; --confirm phải trùng chính xác --target-db."
        )
    current = str(settings.DATABASES["default"]["NAME"])
    if target.casefold() in (current.casefold(), "postgres", "template0", "template1"):
        raise CommandError("Không phục hồi đè database đang dùng hoặc database hệ thống.")
    try:
        metadata = json.loads(
            source.with_suffix(source.suffix + ".json").read_text(encoding="utf-8")
        )
        if metadata.get("format") != 1 or digest(source) != metadata["sha256"]:
            raise CommandError("File sao lưu không khớp SHA256 hoặc sai định dạng metadata.")
    except (OSError, ValueError, KeyError) as error:
        raise CommandError("Cần đủ file .dump và .dump.json hợp lệ.") from error
    run("pg_restore", ["--list", source])
    with psycopg.connect(**params(), autocommit=True) as conn:
        if conn.execute("SELECT 1 FROM pg_database WHERE datname=%s", [target]).fetchone():
            raise CommandError(
                "Database đích đã tồn tại. Chỉ phục hồi vào database mới, không ghi đè dữ liệu."
            )
        conn.execute(
            sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(sql.Identifier(target))
        )
    run(
        "pg_restore",
        [
            "--single-transaction",
            "--exit-on-error",
            "--no-owner",
            "--no-acl",
            "--dbname",
            target,
            source,
        ],
    )
    with psycopg.connect(**params(target)) as conn:
        actual = counts(conn)
    if actual != metadata["counts"]:
        raise CommandError(
            "Số dòng sau phục hồi không khớp metadata. Giữ nguyên database gốc, kiểm tra database thử."
        )
    return actual
