"""Fetch SOCKS5 proxy lists from ProxyScrape and format them.

File format: socks5://xxx:yyy #COUNTRY_CODE-SOCKS5-Number
File naming: COUNTRY_CODE-SOCKS5.txt
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Final, List, Optional, Pattern

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger: logging.Logger = logging.getLogger("fetch_proxies")

# Regex to validate host:port (IPv4 or hostname)
HOST_PORT_PATTERN: Final[Pattern[str]] = re.compile(
    r"^(?:(?:[0-9]{1,3}\.){3}[0-9]{1,3}|(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}|localhost):([0-9]{1,5})$"
)

DEFAULT_BASE_URL: Final[str] = "https://api.proxyscrape.com/v4/free-proxy-list/get"
DEFAULT_TIMEOUT: Final[int] = 15
MAX_RETRIES: Final[int] = 3
RETRY_DELAY: Final[float] = 2.0


def normalize_country_code(code: str) -> str:
    """Normalize country code string to trimmed uppercase.

    Args:
        code: Raw country code string (e.g. " us ", "all").

    Returns:
        Cleaned uppercase country code (e.g. "US", "ALL").
    """
    return code.strip().upper()


def parse_proxy_line(raw_line: str) -> Optional[str]:
    """Clean and validate a raw proxy line, extracting host:port.

    Args:
        raw_line: A single line from ProxyScrape output.

    Returns:
        Validated 'host:port' string, or None if invalid.
    """
    line = raw_line.strip()
    if not line or line.startswith("#"):
        return None

    # Strip any protocol prefix if present (e.g. socks5:// or http://)
    if "://" in line:
        line = line.split("://", 1)[1]

    # Strip any trailing credentials or path
    line = line.split("@")[-1].split("/")[0].strip()

    match = HOST_PORT_PATTERN.match(line)
    if not match:
        return None

    port = int(match.group(1))
    if 1 <= port <= 65535:
        return line
    return None


def build_proxyscrape_url(country: str, token: Optional[str] = None) -> str:
    """Build the ProxyScrape API request URL.

    Args:
        country: Country code (e.g. 'US' or 'ALL').
        token: Optional ProxyScrape API token.

    Returns:
        Full API request URL with query parameters.
    """
    country_param = country.lower()
    params = {
        "request": "display_proxies",
        "protocol": "socks5",
        "country": country_param,
        "format": "text",
    }
    if token:
        # Include serialkey parameter for token support in query
        params["serialkey"] = token

    query_string = urllib.parse.urlencode(params)
    return f"{DEFAULT_BASE_URL}?{query_string}"


def fetch_proxies_for_country(
    country: str,
    token: Optional[str] = None,
    max_retries: int = MAX_RETRIES,
    timeout: int = DEFAULT_TIMEOUT,
) -> List[str]:
    """Fetch raw proxy list for a given country with automatic retry.

    Args:
        country: Target country code (e.g. 'US').
        token: Optional API token.
        max_retries: Number of retry attempts on failure.
        timeout: Network request timeout in seconds.

    Returns:
        List of validated host:port strings.
    """
    url = build_proxyscrape_url(country, token)
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; ProxyScrapeFetcher/1.0)",
        "Accept": "text/plain,*/*",
    }
    if token:
        headers["api-token"] = token

    logger.info("Fetching SOCKS5 proxies for country [%s] from ProxyScrape...", country)

    for attempt in range(1, max_retries + 1):
        try:
            req = urllib.request.Request(url, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=timeout) as response:
                if response.status != 200:
                    logger.warning(
                        "Attempt %d/%d: Received HTTP %d for country [%s]",
                        attempt,
                        max_retries,
                        response.status,
                        country,
                    )
                    time.sleep(RETRY_DELAY)
                    continue

                raw_data: str = response.read().decode("utf-8", errors="replace")
                lines: List[str] = raw_data.splitlines()

                proxies: List[str] = []
                seen: set[str] = set()
                for line in lines:
                    parsed = parse_proxy_line(line)
                    if parsed and parsed not in seen:
                        seen.add(parsed)
                        proxies.append(parsed)

                logger.info(
                    "Successfully fetched %d valid proxies for country [%s]",
                    len(proxies),
                    country,
                )
                return proxies

        except urllib.error.URLError as err:
            logger.warning(
                "Attempt %d/%d failed for country [%s]: %s",
                attempt,
                max_retries,
                country,
                err,
            )
            if attempt < max_retries:
                time.sleep(RETRY_DELAY)
        except Exception as err:
            logger.error(
                "Unexpected error fetching proxies for [%s]: %s", country, err
            )
            break

    logger.error("Failed to fetch proxies for country [%s] after %d attempts", country, max_retries)
    return []


def format_proxy_lines(country: str, proxies: List[str]) -> List[str]:
    """Format proxy entries to the target format:
    `socks5://xxx:yyy #COUNTRY_CODE-SOCKS5-Number`

    Args:
        country: Normalized uppercase country code.
        proxies: List of host:port strings.

    Returns:
        Formatted proxy lines.
    """
    formatted: List[str] = []
    for idx, proxy in enumerate(proxies, start=1):
        line = f"socks5://{proxy} #{country}-SOCKS5-{idx}"
        formatted.append(line)
    return formatted


def save_proxy_file(country: str, lines: List[str], output_dir: Path) -> Path:
    """Save formatted proxy lines to {COUNTRY_CODE}-SOCKS5.txt.

    Args:
        country: Normalized uppercase country code.
        lines: Formatted proxy lines.
        output_dir: Directory where the file should be saved.

    Returns:
        Path to the saved file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{country}-SOCKS5.txt"
    filepath = output_dir / filename

    content = "\n".join(lines) + ("\n" if lines else "")
    filepath.write_text(content, encoding="utf-8")
    logger.info("Saved %d proxies to %s", len(lines), filepath)
    return filepath


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Fetch SOCKS5 proxies from ProxyScrape by country."
    )
    parser.add_argument(
        "--countries",
        type=str,
        default=os.getenv("COUNTRIES", "US,DE,GB,FR,JP,HK,SG"),
        help="Comma-separated country codes (e.g. 'US,DE,JP' or 'ALL')",
    )
    parser.add_argument(
        "--token",
        type=str,
        # TODO: [HUMAN] Configure PROXYSCRAPE_TOKEN in GitHub Repository Secrets if available
        default=os.getenv("PROXYSCRAPE_TOKEN", ""),
        help="ProxyScrape API Token (optional)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=os.getenv("OUTPUT_DIR", "proxies"),
        help="Directory to save generated proxy files",
    )
    return parser.parse_args()


def main() -> int:
    """Main CLI entrypoint."""
    args = parse_args()
    raw_countries: str = args.countries
    token: Optional[str] = args.token.strip() if args.token else None
    output_dir = Path(args.output_dir)

    country_list = [
        normalize_country_code(c)
        for c in raw_countries.split(",")
        if c.strip()
    ]

    if not country_list:
        logger.error("No valid country codes specified.")
        return 1

    logger.info("Processing countries: %s", ", ".join(country_list))
    if token:
        logger.info("ProxyScrape token detected (length: %d).", len(token))
    else:
        logger.info("No ProxyScrape token provided; using public endpoint.")

    total_proxies = 0
    success_count = 0

    for country in country_list:
        proxies = fetch_proxies_for_country(country, token=token)
        if proxies:
            formatted_lines = format_proxy_lines(country, proxies)
            save_proxy_file(country, formatted_lines, output_dir)
            total_proxies += len(proxies)
            success_count += 1
        else:
            logger.warning("No proxies found for [%s], skipping file write.", country)

    logger.info(
        "Finished: %d/%d countries succeeded, %d total proxies collected.",
        success_count,
        len(country_list),
        total_proxies,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
