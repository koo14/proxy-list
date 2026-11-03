"""Unit tests for upload_to_gist.py."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.upload_to_gist import (
    extract_gist_id,
    find_proxy_files,
    find_socks5_files,
    prepare_gist_payload,
)


class TestUploadToGist(unittest.TestCase):
    def test_extract_gist_id_from_urls(self) -> None:
        url1 = "https://gist.github.com/octocat/6cad326836d38bd3a7ae"
        self.assertEqual(extract_gist_id(url1), "6cad326836d38bd3a7ae")

        url2 = "https://gist.github.com/myuser/b26bdf3b8277beaf431c9bf9ef0079e2/"
        self.assertEqual(extract_gist_id(url2), "b26bdf3b8277beaf431c9bf9ef0079e2")

        url3 = "https://gist.github.com/user/6cad326836d38bd3a7ae#file-test-txt"
        self.assertEqual(extract_gist_id(url3), "6cad326836d38bd3a7ae")

        raw_id = "6cad326836d38bd3a7ae"
        self.assertEqual(extract_gist_id(raw_id), "6cad326836d38bd3a7ae")

    def test_extract_gist_id_invalid(self) -> None:
        with self.assertRaises(ValueError):
            extract_gist_id("https://github.com/octocat/repo")

    def test_find_socks5_files(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            dir_path = Path(tmp_dir)
            (dir_path / "US-SOCKS5.txt").write_text("dummy", encoding="utf-8")
            (dir_path / "de-socks5.txt").write_text("dummy", encoding="utf-8")
            (dir_path / "all_socks5_proxies.txt").write_text("dummy", encoding="utf-8")
            (dir_path / "README.md").write_text("dummy", encoding="utf-8")
            (dir_path / "config.json").write_text("dummy", encoding="utf-8")

            found = find_socks5_files([dir_path])
            names = [p.name for p in found]
            self.assertEqual(len(names), 3)
            self.assertIn("US-SOCKS5.txt", names)
            self.assertIn("de-socks5.txt", names)
            self.assertIn("all_socks5_proxies.txt", names)
            self.assertNotIn("README.md", names)

    def test_find_proxy_files_multi_protocols(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            dir_path = Path(tmp_dir)
            (dir_path / "US-SOCKS5.txt").write_text("dummy", encoding="utf-8")
            (dir_path / "US-HTTP.txt").write_text("dummy", encoding="utf-8")
            (dir_path / "US-HTTPS.txt").write_text("dummy", encoding="utf-8")
            (dir_path / "US-SOCKS4.txt").write_text("dummy", encoding="utf-8")
            (dir_path / "ignore.log").write_text("dummy", encoding="utf-8")

            found = find_proxy_files(
                [dir_path], keywords=["socks5", "socks4", "http", "https"]
            )
            names = [p.name for p in found]
            self.assertEqual(len(names), 4)
            self.assertIn("US-SOCKS5.txt", names)
            self.assertIn("US-HTTP.txt", names)
            self.assertIn("US-HTTPS.txt", names)
            self.assertIn("US-SOCKS4.txt", names)
            self.assertNotIn("ignore.log", names)

    def test_prepare_gist_payload(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            dir_path = Path(tmp_dir)
            f1 = dir_path / "US-SOCKS5.txt"
            f1.write_text("socks5://1.2.3.4:1080#US-SOCKS5-1\n", encoding="utf-8")

            payload = prepare_gist_payload([f1], description="Test description")
            self.assertEqual(payload["description"], "Test description")
            self.assertIn("US-SOCKS5.txt", payload["files"])
            self.assertEqual(
                payload["files"]["US-SOCKS5.txt"]["content"],
                "socks5://1.2.3.4:1080#US-SOCKS5-1\n",
            )


if __name__ == "__main__":
    unittest.main()
