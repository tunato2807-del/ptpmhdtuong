"""Synthetic fixtures test extraction only; none are application seed data."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from django.test import SimpleTestCase
from scripts.collect_30shine import (
    CollectionError,
    Page,
    collect,
    extract_listings,
    official_url,
    OfficialRedirectHandler,
)

BASE = "https://30shine.com/"


def page(nodes, links=""):
    return (
        '<html><script type="application/ld+json">'
        + json.dumps(nodes)
        + "</script>"
        + links
        + "</html>"
    ).encode()


class OfficialCollectionTests(SimpleTestCase):
    def test_only_https_official_hosts_are_accepted(self):
        self.assertEqual(official_url("/salon/test", BASE), BASE + "salon/test")
        for url in (
            "http://30shine.com/",
            "https://30shine.com.evil.test/",
            "https://evil.test/",
            "https://user@30shine.com/",
            "https://30shine.com:444/",
            "file:///etc/passwd",
        ):
            with self.subTest(url=url), self.assertRaises(CollectionError):
                official_url(url, BASE)

    def test_redirect_cannot_leave_official_host(self):
        from urllib.request import Request

        handler = OfficialRedirectHandler()
        with self.assertRaises(CollectionError):
            handler.redirect_request(Request(BASE), None, 302, "Found", {}, "https://other.test/")

    def test_extracts_only_public_catalogue_types_and_preserves_price_qualifiers(self):
        nodes = {
            "@graph": [
                {
                    "@type": "HairSalon",
                    "name": "Fixture salon",
                    "address": {"streetAddress": "Fixture address"},
                },
                {
                    "@type": "Service",
                    "name": "Fixture service",
                    "offers": {
                        "@type": "AggregateOffer",
                        "lowPrice": "99000",
                        "priceCurrency": "VND",
                    },
                },
                {"@type": "Product", "name": "Fixture product", "sku": "fixture-1"},
                {
                    "@type": "Person",
                    "name": "Never collect this person",
                    "telephone": "private fixture",
                },
                {"@type": "Review", "reviewBody": "Never collect reviews"},
            ]
        }
        records = extract_listings(page(nodes), BASE)
        self.assertEqual({r["category"] for r in records}, {"branches", "services", "products"})
        service = next(r for r in records if r["category"] == "services")
        self.assertEqual(service["facts"]["offers"]["lowPrice"], "99000")
        self.assertNotIn("price", service["facts"]["offers"])
        self.assertNotIn("duration", service["facts"])
        self.assertNotIn("Never collect", json.dumps(records))

    def test_target_shortfall_is_reported_without_padding_or_duplicate_rows(self):
        nodes = {"@type": "Service", "name": "Fixture single service"}
        body = page(nodes, '<a href="/dich-vu/one">Service</a>')

        def fetch(url):
            if url.endswith("robots.txt"):
                return Page(url, b"User-agent: *\nAllow: /", "text/plain")
            if url.endswith("sitemap.xml"):
                return Page(url, b"<urlset></urlset>", "application/xml")
            return Page(url, body, "text/html")

        with TemporaryDirectory() as directory:
            report = collect(fetch, Path(directory), target=100, max_pages=4, delay=0)
        self.assertEqual(report["counts"]["services"], 1)
        self.assertEqual(report["shortfalls"]["services"], 99)
        self.assertFalse(report["targets_met"])
        self.assertEqual(len(report["records"]), 1)
        self.assertEqual(len(report["records"][0]["source_sha256"]), 64)

    def test_network_denial_is_not_presented_as_an_empty_verified_source(self):
        def blocked(url):
            raise CollectionError("Connection denied")

        with TemporaryDirectory() as directory:
            report = collect(blocked, Path(directory), target=100, max_pages=3, delay=0)
        self.assertFalse(report["targets_met"])
        self.assertEqual(report["counts"], {"branches": 0, "services": 0, "products": 0})
        self.assertTrue(report["errors"])
        self.assertFalse(report["sources"])

    def test_robots_disallow_is_honoured(self):
        fetched = []

        def fetch(url):
            fetched.append(url)
            if url.endswith("robots.txt"):
                return Page(url, b"User-agent: *\nDisallow: /", "text/plain")
            raise AssertionError("Disallowed pages must not be fetched")

        with TemporaryDirectory() as directory:
            report = collect(fetch, Path(directory), target=100, max_pages=3, delay=0)
        self.assertTrue(all(u.endswith("robots.txt") for u in fetched))
        self.assertFalse(report["targets_met"])

    def test_invalid_json_does_not_invent_records(self):
        self.assertEqual(
            extract_listings(b'<script type="application/ld+json">not JSON</script>', BASE), []
        )

    def test_quota_is_a_cap_not_permission_to_repeat_rows(self):
        nodes = [{"@type": "Service", "name": f"Fixture service {i}"} for i in range(105)]

        def fetch(url):
            if url.endswith("robots.txt"):
                return Page(url, b"User-agent: *\nAllow: /", "text/plain")
            return Page(url, page(nodes), "text/html")

        with TemporaryDirectory() as directory:
            report = collect(fetch, Path(directory), target=100, max_pages=2, delay=0)
        self.assertEqual(report["counts"]["services"], 100)
        self.assertEqual(len({r["id"] for r in report["records"]}), 100)
        self.assertEqual(report["counts"]["branches"], 0)
        self.assertFalse(report["targets_met"])

    def test_provider_metadata_differences_do_not_inflate_service_count(self):
        nodes = [
            {
                "@type": "Service",
                "name": "Fixture service",
                "provider": {"@type": "Organization", "name": "Fixture provider", "logo": "a"},
            },
            {
                "@type": "Service",
                "name": "Fixture service",
                "provider": {"@type": "Organization", "name": "Fixture provider", "logo": "b"},
            },
        ]

        def fetch(url):
            if url.endswith("robots.txt"):
                return Page(url, b"User-agent: *\nAllow: /", "text/plain")
            return Page(url, page(nodes), "text/html")

        with TemporaryDirectory() as directory:
            report = collect(fetch, Path(directory), target=100, max_pages=2, delay=0)
        self.assertEqual(report["counts"]["services"], 1)
