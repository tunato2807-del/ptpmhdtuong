"""Collect public JSON-LD catalogue facts from the official 30Shine website.

Writes a local evidence pack, never business rows or invented filler records.
Run from the project: .venv/bin/python scripts/collect_30shine.py --target 100
"""

import argparse
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from urllib.robotparser import RobotFileParser
from defusedxml import ElementTree

BASE = "https://30shine.com/"
HOSTS = {"30shine.com", "www.30shine.com"}
CATEGORIES = ("branches", "services", "products")
AGENT = "GentlemanOfficialCatalogue/1.0"
MAX_BYTES = 5 * 1024 * 1024
KINDS = {
    "HairSalon": "branches",
    "BarberShop": "branches",
    "BeautySalon": "branches",
    "Service": "services",
    "Product": "products",
}


class CollectionError(ValueError):
    pass


def official_url(value, base=BASE):
    parts = urlsplit(urljoin(base, value))
    try:
        port = parts.port
    except ValueError as error:
        raise CollectionError("Cổng URL không hợp lệ.") from error
    if (
        parts.scheme != "https"
        or parts.hostname not in HOSTS
        or parts.username
        or parts.password
        or port not in (None, 443)
        or parts.query
    ):
        raise CollectionError(
            "Chỉ nhận trang HTTPS công khai trên tên miền chính thức, không có query hoặc thông tin đăng nhập."
        )
    return urlunsplit(("https", parts.hostname, parts.path or "/", "", ""))


class OfficialRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        url = official_url(newurl, req.full_url)
        return super().redirect_request(req, fp, code, msg, headers, url)


@dataclass
class Page:
    url: str
    body: bytes
    content_type: str


class OfficialClient:
    def __init__(self):
        self.opener = build_opener(OfficialRedirectHandler())

    def fetch(self, url):
        url = official_url(url)
        request = Request(url, headers={"User-Agent": AGENT, "Accept-Encoding": "identity"})
        try:
            with self.opener.open(request, timeout=20) as response:
                final = official_url(response.url)
                body = response.read(MAX_BYTES + 1)
                if len(body) > MAX_BYTES:
                    raise CollectionError("Trang nguồn vượt giới hạn 5 MiB.")
                return Page(final, body, response.headers.get_content_type())
        except HTTPError as error:
            if error.code == 404 and urlsplit(url).path in ("/robots.txt", "/sitemap.xml"):
                return Page(url, b"", "text/plain")
            raise CollectionError(f"Nguồn trả HTTP {error.code}.") from error
        except URLError as error:
            raise CollectionError(f"Không kết nối được nguồn: {error.reason}") from error


class PublicPageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scripts = []
        self.links = []
        self.current = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "script" and attrs.get("type", "").lower().split(";")[0] == "application/ld+json":
            self.current = []
        elif tag == "a" and attrs.get("href"):
            self.links.append(attrs["href"])

    def handle_data(self, data):
        if self.current is not None:
            self.current.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self.current is not None:
            self.scripts.append("".join(self.current))
            self.current = None


def type_names(node):
    values = node.get("@type", [])
    if not isinstance(values, list):
        values = [values]
    return {x.rsplit("/", 1)[-1].rsplit("#", 1)[-1] for x in values if isinstance(x, str)}


def public_value(value):
    """Keep declared catalogue conditions, excluding nested person/review/transaction data."""
    if isinstance(value, dict):
        if type_names(value) & {"Person", "Review", "Rating", "Order", "Invoice", "Reservation"}:
            return None
        return {k: v for k, raw in value.items() if (v := public_value(raw)) is not None}
    if isinstance(value, list):
        return [v for raw in value if (v := public_value(raw)) is not None]
    return value


def extract_listings(body, source_url):
    source_url = official_url(source_url)
    parser = PublicPageParser()
    parser.feed(body.decode("utf-8", errors="replace"))
    records = []
    for index, script in enumerate(parser.scripts):
        try:
            document = json.loads(script)
        except (ValueError, RecursionError):
            continue
        stack = [(document, f"jsonld[{index}]")]
        visited = 0
        while stack and visited < 10000:
            node, locator = stack.pop()
            visited += 1
            if isinstance(node, list):
                stack.extend((v, f"{locator}[{i}]") for i, v in enumerate(node))
                continue
            if not isinstance(node, dict):
                continue
            types = type_names(node)
            if types & {"Person", "Review", "Order", "Invoice", "Reservation"}:
                continue
            name = node.get("name")
            category = next((KINDS[t] for t in KINDS if t in types), None)
            if category and isinstance(name, str) and name.strip():
                # A generic organization without an address is not evidence of a salon location.
                if category == "branches" and not node.get("address"):
                    category = None
                if category:
                    keys = (
                        "description",
                        "address",
                        "telephone",
                        "openingHours",
                        "openingHoursSpecification",
                        "offers",
                        "sku",
                        "gtin",
                        "gtin13",
                        "brand",
                        "provider",
                        "url",
                        "areaServed",
                    )
                    facts = {k: public_value(node[k]) for k in keys if k in node}
                    records.append(
                        {
                            "category": category,
                            "name": name.strip(),
                            "facts": facts,
                            "source_url": source_url,
                            "source_sha256": hashlib.sha256(body).hexdigest(),
                            "source_locator": locator,
                        }
                    )
            stack.extend(
                (v, f"{locator}.{k}") for k, v in node.items() if isinstance(v, (dict, list))
            )
    return records


def catalogue_links(body, base, content_type):
    if "xml" in content_type or body.lstrip().startswith(b"<?xml"):
        try:
            tree = ElementTree.fromstring(body)
            candidates = [
                e.text for e in tree.iter() if e.tag.rsplit("}", 1)[-1] == "loc" and e.text
            ]
        except (ElementTree.ParseError, ValueError):
            return []
    else:
        parser = PublicPageParser()
        parser.feed(body.decode("utf-8", errors="replace"))
        candidates = parser.links
    urls = []
    for value in candidates:
        if value.startswith("#"):
            continue
        try:
            url = official_url(value, base)
        except CollectionError:
            continue
        path = urlsplit(url).path.lower()
        if any(
            term in path
            for term in (
                "dang-nhap",
                "dang-ky",
                "login",
                "logout",
                "dat-lich",
                "booking",
                "khach-hang",
                "lich-hen",
                "account",
                "customer",
                "checkout",
                "/api/",
                "/cart",
            )
        ):
            continue
        if any(
            term in path
            for term in (
                "salon",
                "chi-nhanh",
                "he-thong",
                "dich-vu",
                "service",
                "san-pham",
                "product",
                "bang-gia",
                "sitemap",
            )
        ):
            if not path.endswith((".jpg", ".jpeg", ".png", ".webp", ".svg", ".js", ".css", ".pdf")):
                urls.append(url)
    return urls


def entity_identity(value):
    if isinstance(value, dict):
        value = value.get("name", "")
    if isinstance(value, str):
        return " ".join(value.casefold().split())
    return None


def identity(record):
    facts = record["facts"]
    key = [record["category"], " ".join(record["name"].casefold().split())]
    if record["category"] == "branches":
        key.append(facts.get("address"))
    elif record["category"] == "products":
        key.extend(
            (
                facts.get("sku") or facts.get("gtin13") or facts.get("gtin"),
                entity_identity(facts.get("brand")),
            )
        )
    else:
        key.append(entity_identity(facts.get("provider")))
    return hashlib.sha256(json.dumps(key, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def collect(fetch, output, target=100, max_pages=300, delay=0.75, seeds=None):
    if not 1 <= target <= 1000 or not 1 <= max_pages <= 1000:
        raise CollectionError("Target và số trang phải trong khoảng 1–1000.")
    output.mkdir(parents=True, exist_ok=True)
    evidence = output / "sources"
    evidence.mkdir(exist_ok=True)
    robots = {}
    report = {
        "schema_version": 1,
        "publisher": "30Shine",
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "target_per_category": target,
        "counts": dict.fromkeys(CATEGORIES, 0),
        "sources": [],
        "errors": [],
        "records": [],
        "database_written": False,
        "scope": "Public JSON-LD catalogue facts only; not operational users, employees, bookings, invoices or stock.",
    }
    queue = deque(official_url(url) for url in (seeds or [BASE, BASE + "sitemap.xml"]))
    seen = set()
    unique = set()
    requests = 0
    while queue and len(seen) < max_pages:
        url = queue.popleft()
        if url in seen:
            continue
        seen.add(url)
        host = urlsplit(url).hostname
        try:
            if host not in robots:
                robot_url = f"https://{host}/robots.txt"
                page = fetch(robot_url)
                policy = RobotFileParser(robot_url)
                policy.parse(page.body.decode("utf-8", "replace").splitlines())
                robots[host] = policy
            if not robots[host].can_fetch(AGENT, url):
                report["errors"].append({"url": url, "reason": "robots_disallow"})
                continue
            if requests and delay:
                time.sleep(delay)
            page = fetch(url)
            requests += 1
            final_url = official_url(page.url)
            if len(page.body) > MAX_BYTES:
                raise CollectionError("Trang vượt giới hạn dung lượng.")
        except (CollectionError, OSError) as error:
            report["errors"].append({"url": url, "reason": str(error)})
            # An unavailable robots endpoint is a blocked source, not permission to bypass it.
            if host not in robots:
                break
            continue
        digest = hashlib.sha256(page.body).hexdigest()
        relative = f"sources/{digest}.bin"
        (output / relative).write_bytes(page.body)
        report["sources"].append(
            {
                "url": final_url,
                "sha256": digest,
                "evidence_file": relative,
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        for record in extract_listings(page.body, final_url):
            category = record["category"]
            key = identity(record)
            if key in unique or report["counts"][category] >= target:
                continue
            unique.add(key)
            record["id"] = key
            record["retrieved_at"] = report["sources"][-1]["retrieved_at"]
            report["records"].append(record)
            report["counts"][category] += 1
        if all(n >= target for n in report["counts"].values()):
            break
        for candidate in catalogue_links(page.body, final_url, page.content_type):
            if candidate not in seen and len(queue) < max_pages * 3:
                queue.append(candidate)
    report["shortfalls"] = {k: max(0, target - n) for k, n in report["counts"].items()}
    report["targets_met"] = all(n == 0 for n in report["shortfalls"].values())
    report["pages_fetched"] = len(report["sources"])
    report["notes"] = [
        "Only explicitly published structured fields are copied; absent fields are not guessed.",
        "Repeated listings are not added to fill a target. Low/range/promotional prices retain their original keys and conditions.",
        "This is a collection/evidence pack for review, not an automatic import into owned salon operations.",
        "No JSON-LD or fewer published entries means a shortfall, never synthetic filler.",
    ]
    (output / "catalogue.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=int, default=100)
    parser.add_argument("--max-pages", type=int, default=300)
    parser.add_argument("--output", type=Path, default=Path(".local/30shine"))
    parser.add_argument(
        "--url", action="append", help="Public official catalogue URL; repeat for additional pages"
    )
    args = parser.parse_args()
    try:
        report = collect(
            OfficialClient().fetch, args.output, args.target, args.max_pages, seeds=args.url
        )
    except (CollectionError, OSError) as error:
        parser.exit(1, f"Không thu thập được dữ liệu: {error}\n")
    print("Đã ghi gói nguồn vào:", args.output / "catalogue.json")
    for category in CATEGORIES:
        print(
            f"{category}: {report['counts'][category]}/{args.target}; thiếu {report['shortfalls'][category]}"
        )
    if report["errors"]:
        print("Có nguồn bị chặn/lỗi; xem errors trong catalogue.json. Không tạo dữ liệu thay thế.")
    print("Chưa ghi bản ghi vào database. Gói nguồn cần được đối chiếu trước khi nhập.")
    return 0 if report["targets_met"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
