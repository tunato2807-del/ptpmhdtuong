from contextlib import redirect_stdout
from io import StringIO
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from django.test import SimpleTestCase
from scripts import cap_nhat_du_an as updater


class SourceUpdaterTests(SimpleTestCase):
    def test_spec_kit_public_files_are_allowed_but_machine_state_is_not(self):
        public = (
            ".specify/.gitignore",
            ".specify/LICENSE",
            ".specify/source.json",
            ".specify/integration.json",
            ".specify/init-options.json",
            ".specify/integrations/copilot.manifest.json",
            ".specify/integrations/codex.manifest.json",
            ".specify/integrations/speckit.manifest.json",
            ".specify/memory/constitution.md",
            ".specify/scripts/python/common.py",
            ".specify/templates/spec-template.md",
            ".specify/workflows/speckit/workflow.yml",
            ".specify/workflows/workflow-registry.json",
            ".github/skills/speckit-specify/SKILL.md",
            ".agents/skills/speckit-plan/SKILL.md",
            "specs/001-adopt-spec-kit/spec.md",
        )
        updater.validate_manifest(self.manifest(dict.fromkeys(public, b"public workflow")))
        for private in (
            ".specify/feature.json",
            ".specify/auth.json",
            ".specify/integrations/packages.json",
            ".specify/integrations/packages/adapter.py",
            ".specify/extensions/private/local-config.yml",
            ".specify/memory/.env",
            ".github/skills/speckit-specify/.env",
            ".codex/auth.json",
        ):
            with self.subTest(path=private), self.assertRaises(ValueError):
                updater.validate_manifest(self.manifest({private: b"private"}))

    def test_manifest_can_grow_with_specs_but_is_still_bounded(self):
        files = {f"docs/spec-{n}.md": b"spec" for n in range(401)}
        updater.validate_manifest(self.manifest(files))
        with self.assertRaises(ValueError):
            updater.validate_manifest(
                self.manifest({f"docs/spec-{n}.md": b"spec" for n in range(1001)})
            )

    def test_portable_workflows_are_allowed_but_credentials_remain_blocked(self):
        files = {
            name: b"workflow"
            for name in (
                "AGENTS.md",
                "ruff.toml",
                "requirements-quality.txt",
                ".agents/skills/security-and-hardening/SKILL.md",
                ".agents/references/security-checklist.md",
                ".agents/LICENSE.agent-skills",
                ".agents/agent-skills-source.json",
                ".github/copilot-instructions.md",
                ".github/workflows/ci.yml",
            )
        }
        updater.validate_manifest(self.manifest(files))
        for name in (".agents/.env", ".github/secrets.json", ".git/config", ".aws/credentials"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                updater.validate_manifest(self.manifest({name: b"private"}))

    def manifest(self, files):
        return {
            "ref": "a" * 40,
            "files": [
                {"path": name, "sha256": hashlib.sha256(data).hexdigest()}
                for name, data in files.items()
            ],
        }

    def test_paths_cannot_escape_or_replace_private_configuration(self):
        for name in (
            "../secrets",
            "/absolute",
            "templates/../../.env",
            ".env",
            "salon/../manage.py",
            "C:/file",
            "salon/.env",
            "salon\\file.py",
        ):
            with self.subTest(name=name), self.assertRaises(ValueError):
                updater.validate_manifest(self.manifest({name: b"bad"}))

    def test_complete_update_backups_missing_templates_and_keeps_private_files(self):
        files = {
            "manage.py": b"# current\n",
            "templates/features/page.html": b"<h1>Ready</h1>",
            "docs/report.docx": b"PK binary document",
            ".specify/memory/constitution.md": b"project rules",
            ".github/skills/speckit-plan/SKILL.md": b"plan workflow",
            "specs/001-adopt-spec-kit/spec.md": b"feature specification",
        }
        manifest = self.manifest(files)

        def fetch(url):
            if url.endswith("update_manifest.json"):
                return json.dumps(manifest).encode()
            return files[url.split("/" + "a" * 40 + "/")[1]]

        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "manage.py").write_bytes(b"# old\n")
            (root / ".env").write_bytes(b"private sentinel")
            (root / ".specify").mkdir()
            (root / ".specify/feature.json").write_bytes(b"local feature sentinel")
            with (
                patch.object(updater, "fetch", side_effect=fetch),
                patch("sys.argv", ["updater", "--project", tmp]),
                redirect_stdout(StringIO()),
            ):
                self.assertEqual(updater.main(), 0)
                self.assertEqual(updater.main(), 0)
            self.assertEqual(
                (root / "templates/features/page.html").read_bytes(),
                files["templates/features/page.html"],
            )
            self.assertEqual((root / ".env").read_bytes(), b"private sentinel")
            self.assertEqual(
                (root / ".specify/feature.json").read_bytes(), b"local feature sentinel"
            )
            for name in files:
                self.assertEqual((root / name).read_bytes(), files[name])
            self.assertEqual((root / "docs/report.docx").read_bytes(), b"PK binary document")
            backups = list((root / ".local").glob("*/sao-luu/manage.py"))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_bytes(), b"# old\n")

    def test_hash_error_stops_before_replacing_any_source(self):
        files = {"manage.py": b"new", "templates/features/page.html": b"valid"}
        manifest = self.manifest(files)
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "manage.py").write_bytes(b"old")

            def fetch(url):
                return (
                    json.dumps(manifest).encode()
                    if url.endswith("update_manifest.json")
                    else b"corrupted"
                )

            with (
                patch.object(updater, "fetch", side_effect=fetch),
                patch("sys.argv", ["updater", "--project", tmp]),
                redirect_stdout(StringIO()),
                self.assertRaises(ValueError),
            ):
                updater.main()
            self.assertEqual((root / "manage.py").read_bytes(), b"old")
            self.assertFalse((root / "templates/features/page.html").exists())

    def test_write_failure_restores_prior_sources(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            root.mkdir()
            stage = Path(tmp) / "stage"
            stage.mkdir()
            backup = Path(tmp) / "backup"
            (root / "manage.py").write_bytes(b"old")
            (stage / "manage.py").write_bytes(b"new")
            (stage / "other.py").write_bytes(b"new file")
            real_replace = updater.os.replace

            def replace(source, target):
                if str(target).endswith("other.py"):
                    raise OSError("simulated disk error")
                return real_replace(source, target)

            with (
                patch.object(updater.os, "replace", side_effect=replace),
                self.assertRaises(OSError),
            ):
                updater.apply_files(root, stage, ["manage.py", "other.py"], backup)
            self.assertEqual((root / "manage.py").read_bytes(), b"old")
            self.assertFalse((root / "other.py").exists())
