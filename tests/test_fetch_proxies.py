"""Unit tests for fetch_proxies.py."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.fetch_proxies import (
    build_proxyscrape_url,
    format_proxy_lines,
    normalize_country_code,
    parse_proxy_line,
    save_proxy_file,
)


class TestFetchProxies(unittest.TestCase):
    def test_normalize_country_code(self) -> None:
        self.assertEqual(normalize_country_code("us"), "US")
        self.assertEqual(normalize_country_code(" DE "), "DE")
        self.assertEqual(normalize_country_code("all"), "ALL")

    def test_parse_proxy_line_valid(self) -> None:
        self.assertEqual(parse_proxy_line("192.168.1.1:1080"), "192.168.1.1:1080")
        self.assertEqual(
            parse_proxy_line("socks5://1.2.3.4:8080"), "1.2.3.4:8080"
        )
        self.assertEqual(
            parse_proxy_line("user:pass@1.2.3.4:9050/"), "1.2.3.4:9050"
        )
        self.assertEqual(parse_proxy_line("proxy.example.com:443"), "proxy.example.com:443")

    def test_parse_proxy_line_invalid(self) -> None:
        self.assertIsNone(parse_proxy_line(""))
        self.assertIsNone(parse_proxy_line("# comment line"))
        self.assertIsNone(parse_proxy_line("not_a_proxy"))
        self.assertIsNone(parse_proxy_line("1.2.3.4:999999"))  # invalid port

    def test_build_proxyscrape_url(self) -> None:
        url_without_token = build_proxyscrape_url("US")
        self.assertIn("country=us", url_without_token)
        self.assertIn("protocol=socks5", url_without_token)
        self.assertNotIn("serialkey", url_without_token)

        url_with_token = build_proxyscrape_url("DE", token="my_secret_token")
        self.assertIn("country=de", url_with_token)
        self.assertIn("serialkey=my_secret_token", url_with_token)

    def test_format_proxy_lines(self) -> None:
        proxies = ["1.1.1.1:1080", "2.2.2.2:1080", "3.3.3.3:1080"]
        formatted = format_proxy_lines("US", proxies)
        expected = [
            "socks5://1.1.1.1:1080#US-SOCKS5-1",
            "socks5://2.2.2.2:1080#US-SOCKS5-2",
            "socks5://3.3.3.3:1080#US-SOCKS5-3",
        ]
        self.assertEqual(formatted, expected)

    def test_save_proxy_file(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            out_path = Path(tmp_dir)
            lines = [
                "socks5://1.1.1.1:1080#HK-SOCKS5-1",
                "socks5://2.2.2.2:1080#HK-SOCKS5-2",
            ]
            saved_file = save_proxy_file("HK", lines, out_path)
            self.assertEqual(saved_file.name, "HK-SOCKS5.txt")
            self.assertTrue(saved_file.exists())

            content = saved_file.read_text(encoding="utf-8")
            self.assertIn("socks5://1.1.1.1:1080#HK-SOCKS5-1", content)
            self.assertIn("socks5://2.2.2.2:1080#HK-SOCKS5-2", content)


if __name__ == "__main__":
    unittest.main()
