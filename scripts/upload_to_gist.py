"""Upload proxy list files to a GitHub Gist.

Target files: all files whose name contains 'socks5' (case-insensitive).
Files are uploaded with their original basenames, overwriting existing files in the Gist.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Final, List, Optional, Pattern

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger: logging.Logger = logging.getLogger("upload_to_gist")

GIST_ID_PATTERN: Final[Pattern[str]] = re.compile(r"([a-f0-9]{20,32})", re.IGNORECASE)
GITHUB_API_BASE: Final[str] = "https://api.github.com"
GITHUB_API_VERSION: Final[str] = "2022-11-28"


def extract_gist_id(gist_input: str) -> str:
    """Extract Gist ID from a full Gist URL or raw ID string.

    Examples:
        - "https://gist.github.com/octocat/6cad326836d38bd3a7ae" -> "6cad326836d38bd3a7ae"
        - "6cad326836d38bd3a7ae" -> "6cad326836d38bd3a7ae"

    Args:
        gist_input: Gist URL or Gist ID string.

    Returns:
        Cleaned Gist ID string.

    Raises:
        ValueError: If no valid Gist ID can be parsed.
    """
    cleaned = gist_input.strip()
    # Remove URL fragment or query string if present
    cleaned = cleaned.split("#")[0].split("?")[0].rstrip("/")

    # If it is a URL, take the last segment
    last_segment = cleaned.split("/")[-1]

    match = GIST_ID_PATTERN.search(last_segment)
    if match:
        return match.group(1)

    # Fallback to searching the whole input
    match = GIST_ID_PATTERN.search(cleaned)
    if match:
        return match.group(1)

    raise ValueError(f"Could not parse a valid Gist ID from input: '{gist_input}'")


def find_proxy_files(
    directories: List[Path],
    keywords: Optional[List[str]] = None,
) -> List[Path]:
    """Find all proxy files matching any of the specified keywords (case-insensitive).

    Args:
        directories: List of directories to search in.
        keywords: Optional list of keywords to match in filenames
                  (default matches socks5, socks4, http, https, or any .txt proxy file).

    Returns:
        Sorted list of matching Path objects.
    """
    matched_files: List[Path] = []
    seen_basenames: set[str] = set()

    lowered_kws = [k.strip().lower() for k in keywords if k.strip()] if keywords else []

    for directory in directories:
        if not directory.exists() or not directory.is_dir():
            continue
        for file_path in directory.iterdir():
            if not file_path.is_file():
                continue
            name_lower = file_path.name.lower()
            if not name_lower.endswith(".txt"):
                continue

            # If keywords specified, check if any keyword is present
            if lowered_kws:
                if any(kw in name_lower for kw in lowered_kws):
                    if file_path.name not in seen_basenames:
                        seen_basenames.add(file_path.name)
                        matched_files.append(file_path)
            else:
                # Include any non-empty txt proxy file
                if file_path.name not in seen_basenames:
                    seen_basenames.add(file_path.name)
                    matched_files.append(file_path)

    matched_files.sort(key=lambda p: p.name)
    return matched_files


def find_socks5_files(directories: List[Path], keyword: str = "socks5") -> List[Path]:
    """Backward-compatible wrapper for finding files with a single keyword."""
    return find_proxy_files(directories, keywords=[keyword])


def prepare_gist_payload(file_paths: List[Path], description: Optional[str] = None) -> Dict[str, Any]:
    """Build the GitHub Gist PATCH payload dictionary.

    Args:
        file_paths: List of file paths to include.
        description: Optional updated description for the Gist.

    Returns:
        Dictionary payload ready for JSON serialization.
    """
    files_payload: Dict[str, Dict[str, str]] = {}

    for file_path in file_paths:
        content = file_path.read_text(encoding="utf-8")
        # Gist API does not allow completely empty file content, provide fallback comment if empty
        if not content.strip():
            content = f"# Empty proxy list for {file_path.name}\n"
        files_payload[file_path.name] = {"content": content}

    payload: Dict[str, Any] = {"files": files_payload}
    if description:
        payload["description"] = description

    return payload


def upload_to_gist(
    gist_id: str,
    token: str,
    files_payload: Dict[str, Any],
    timeout: int = 20,
) -> Dict[str, Any]:
    """Send PATCH request to update files in the target GitHub Gist.

    Args:
        gist_id: Target Gist ID.
        token: GitHub Personal Access Token (with 'gist' permission scope).
        files_payload: JSON payload containing files to overwrite.
        timeout: Network timeout in seconds.

    Returns:
        Response JSON dictionary from GitHub API.

    Raises:
        RuntimeError: If API call fails.
    """
    url = f"{GITHUB_API_BASE}/gists/{gist_id}"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": GITHUB_API_VERSION,
        "User-Agent": "ProxyList-GistUploader/1.0",
        "Content-Type": "application/json; charset=utf-8",
    }

    data = json.dumps(files_payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="PATCH")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            res_data = response.read().decode("utf-8")
            return json.loads(res_data)
    except urllib.error.HTTPError as err:
        err_msg = err.read().decode("utf-8", errors="replace")
        if err.code == 401:
            raise RuntimeError(
                "GitHub API 401 Unauthorized: Please verify GIST_TOKEN secret has the 'gist' scope."
            ) from err
        if err.code == 404:
            raise RuntimeError(
                f"GitHub API 404 Not Found: Gist ID '{gist_id}' was not found or the token lacks permission to edit it."
            ) from err
        raise RuntimeError(
            f"GitHub API error {err.code}: {err.reason}\nResponse: {err_msg}"
        ) from err
    except urllib.error.URLError as err:
        raise RuntimeError(f"Network error connecting to GitHub API: {err.reason}") from err


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Upload SOCKS5 proxy files to a GitHub Gist."
    )
    parser.add_argument(
        "--gist-url",
        type=str,
        # TODO: [HUMAN] Provide your Gist URL or GIST_ID via environment variable or CLI argument
        default=os.getenv("GIST_URL", os.getenv("GIST_ID", "")),
        help="Gist URL (e.g. https://gist.github.com/user/gist-id) or Gist ID",
    )
    parser.add_argument(
        "--token",
        type=str,
        # TODO: [HUMAN] Configure GIST_TOKEN (GitHub PAT with 'gist' scope) in GitHub Secrets
        default=os.getenv("GIST_TOKEN", os.getenv("GH_TOKEN", "")),
        help="GitHub Personal Access Token with 'gist' scope",
    )
    parser.add_argument(
        "--dir",
        type=str,
        action="append",
        default=[],
        help="Directory to scan for proxy files (can specify multiple, defaults to ['proxies', '.'])",
    )
    parser.add_argument(
        "--keywords",
        type=str,
        default=os.getenv("PROXY_KEYWORDS", "socks5,socks4,http,https"),
        help="Comma-separated keywords to filter proxy filenames (default: 'socks5,socks4,http,https')",
    )
    parser.add_argument(
        "--keyword",
        type=str,
        default="",
        help="Single keyword filter (legacy/backward compatibility)",
    )
    return parser.parse_args()


def main() -> int:
    """Main CLI entrypoint."""
    args = parse_args()

    gist_raw: str = args.gist_url.strip()
    token: str = args.token.strip()

    if not gist_raw:
        logger.error(
            "Missing Gist identifier. Please set GIST_URL or pass --gist-url (e.g. https://gist.github.com/<user>/<gist-id>)."
        )
        return 1

    if not token:
        logger.error(
            "Missing GitHub Token. Please set GIST_TOKEN secret or pass --token (PAT with 'gist' scope)."
        )
        return 1

    try:
        gist_id = extract_gist_id(gist_raw)
        logger.info("Target Gist ID: %s", gist_id)
    except ValueError as err:
        logger.error(str(err))
        return 1

    # Directories to search
    raw_dirs = args.dir if args.dir else ["proxies", "."]
    search_dirs = [Path(d) for d in raw_dirs]

    # Combine keywords
    keywords_list: List[str] = []
    if args.keyword:
        keywords_list.append(args.keyword)
    if args.keywords:
        keywords_list.extend([k.strip() for k in args.keywords.split(",") if k.strip()])

    files = find_proxy_files(search_dirs, keywords=keywords_list if keywords_list else None)
    if not files:
        logger.error("No matching proxy files found in %s with keywords %s", raw_dirs, keywords_list)
        return 1

    logger.info("Found %d proxy files to upload:", len(files))
    for f in files:
        logger.info(" - %s (%.2f KB)", f.name, f.stat().st_size / 1024)

    payload = prepare_gist_payload(
        files,
        description="Automated Proxy Lists (Updated by GitHub Actions)",
    )

    logger.info("Uploading to Gist https://gist.github.com/%s ...", gist_id)
    try:
        result = upload_to_gist(gist_id=gist_id, token=token, files_payload=payload)
        html_url = result.get("html_url", f"https://gist.github.com/{gist_id}")
        logger.info("Successfully updated Gist: %s", html_url)
        logger.info("Updated files in Gist: %s", ", ".join(result.get("files", {}).keys()))
        return 0
    except Exception as err:
        logger.error("Upload failed: %s", err)
        return 1


if __name__ == "__main__":
    sys.exit(main())
