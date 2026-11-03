"""Unit tests for fetch_proxies.py."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.fetch_proxies import (
    build_proxyscrape_url,
    format_proxy_lines,
    normalize_country_code,
    normalize_protocol,
    parse_proxy_line,
    save_proxy_file,
)


class TestFetchProxies(unittest.TestCase):
    def test_normalize_country_code(self) -> None:
        self.assertEqual(normalize_country_code("us"), "US")
        self.assertEqual(normalize_country_code(" DE "), "DE")
        self.assertEqual(normalize_country_code("cn"), "CN")
        self.assertEqual(normalize_country_code("all"), "ALL")

    def test_normalize_protocol(self) -> None:
        self.assertEqual(normalize_protocol("SOCKS5"), "socks5")
        self.assertEqual(normalize_protocol(" HTTP "), "http")
        self.assertEqual(normalize_protocol("Socks4"), "socks4")
        self.assertEqual(normalize_protocol("https"), "https")

    def test_parse_proxy_line_valid(self) -> None:
        self.assertEqual(parse_proxy_line("192.168.1.1:1080"), "192.168.1.1:1080")
        self.assertEqual(
            parse_proxy_line("socks5://1.2.3.4:8080"), "1.2.3.4:8080"
        )
        self.assertEqual(
            parse_proxy_line("http://1.2.3.4:3128"), "1.2.3.4:3128"
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
        url_without_token = build_proxyscrape_url("US", protocol="socks5")
        self.assertIn("country=us", url_without_token)
        self.assertIn("protocol=socks5", url_without_token)
        self.assertNotIn("serialkey", url_without_token)

        url_http = build_proxyscrape_url("JP", protocol="http")
        self.assertIn("country=jp", url_http)
        self.assertIn("protocol=http", url_http)

        url_with_token = build_proxyscrape_url("DE", protocol="https", token="my_secret_token")
        self.assertIn("country=de", url_with_token)
        self.assertIn("protocol=https", url_with_token)
        self.assertIn("serialkey=my_secret_token", url_with_token)

    def test_format_proxy_lines(self) -> None:
        proxies = ["1.1.1.1:1080", "2.2.2.2:1080"]

        formatted_socks5 = format_proxy_lines("US", "socks5", proxies)
        self.assertEqual(
            formatted_socks5,
            [
                "socks5://1.1.1.1:1080#US-SOCKS5-1",
                "socks5://2.2.2.2:1080#US-SOCKS5-2",
            ],
        )

        formatted_http = format_proxy_lines("DE", "http", proxies)
        self.assertEqual(
            formatted_http,
            [
                "http://1.1.1.1:1080#DE-HTTP-1",
                "http://2.2.2.2:1080#DE-HTTP-2",
            ],
        )

    def test_save_proxy_file(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            out_path = Path(tmp_dir)
            lines = [
                "socks5://1.1.1.1:1080#HK-SOCKS5-1",
                "socks5://2.2.2.2:1080#HK-SOCKS5-2",
            ]
            saved_file = save_proxy_file("HK", "socks5", lines, out_path)
            self.assertEqual(saved_file.name, "HK-SOCKS5.txt")
            self.assertTrue(saved_file.exists())

            content = saved_file.read_text(encoding="utf-8")
            self.assertIn("socks5://1.1.1.1:1080#HK-SOCKS5-1", content)
            self.assertIn("socks5://2.2.2.2:1080#HK-SOCKS5-2", content)


if __name__ == "__main__":
    unittest.main()
