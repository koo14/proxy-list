"""Fetch proxy lists (SOCKS5, SOCKS4, HTTP, HTTPS, etc.) from ProxyScrape and format them.

File format: {protocol}://xxx:yyy#{COUNTRY_CODE}-{PROTOCOL}-{Number}
File naming: {COUNTRY_CODE}-{PROTOCOL}.txt (e.g. US-SOCKS5.txt, US-HTTP.txt)
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
from typing import Final, List, Optional, Pattern, Set

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

SUPPORTED_PROTOCOLS: Final[Set[str]] = {"socks5", "socks4", "http", "https"}


def normalize_country_code(code: str) -> str:
    """Normalize country code string to trimmed uppercase.

    Args:
        code: Raw country code string (e.g. " us ", "all").

    Returns:
        Cleaned uppercase country code (e.g. "US", "ALL").
    """
    return code.strip().upper()


def normalize_protocol(protocol: str) -> str:
    """Normalize and validate proxy protocol string.

    Args:
        protocol: Raw protocol string (e.g. "SOCKS5", " socks4 ", "http").

    Returns:
        Cleaned lowercase protocol string.
    """
    clean_proto = protocol.strip().lower()
    return clean_proto


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

    # Strip any credentials or URL path
    line = line.split("@")[-1].split("/")[0].strip()

    match = HOST_PORT_PATTERN.match(line)
    if not match:
        return None

    port = int(match.group(1))
    if 1 <= port <= 65535:
        return line
    return None


def build_proxyscrape_url(
    country: str,
    protocol: str = "socks5",
    token: Optional[str] = None,
) -> str:
    """Build the ProxyScrape API request URL.

    Args:
        country: Country code (e.g. 'US' or 'ALL').
        protocol: Proxy protocol (e.g. 'socks5', 'socks4', 'http', 'https').
        token: Optional ProxyScrape API token.

    Returns:
        Full API request URL with query parameters.
    """
    country_param = country.lower()
    proto_param = protocol.lower()

    params = {
        "request": "display_proxies",
        "protocol": proto_param,
        "country": country_param,
        "format": "text",
    }
    if token:
        params["serialkey"] = token

    query_string = urllib.parse.urlencode(params)
    return f"{DEFAULT_BASE_URL}?{query_string}"


def fetch_proxies_for_target(
    country: str,
    protocol: str = "socks5",
    token: Optional[str] = None,
    max_retries: int = MAX_RETRIES,
    timeout: int = DEFAULT_TIMEOUT,
) -> List[str]:
    """Fetch raw proxy list for a given country and protocol with automatic retry.

    Args:
        country: Target country code (e.g. 'US').
        protocol: Proxy protocol ('socks5', 'socks4', 'http', 'https').
        token: Optional API token.
        max_retries: Number of retry attempts on failure.
        timeout: Network request timeout in seconds.

    Returns:
        List of validated host:port strings.
    """
    url = build_proxyscrape_url(country, protocol=protocol, token=token)
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; ProxyScrapeFetcher/2.0)",
        "Accept": "text/plain,*/*",
    }
    if token:
        headers["api-token"] = token

    logger.info(
        "Fetching [%s] proxies for country [%s] from ProxyScrape...",
        protocol.upper(),
        country,
    )

    for attempt in range(1, max_retries + 1):
        try:
            req = urllib.request.Request(url, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=timeout) as response:
                if response.status != 200:
                    logger.warning(
                        "Attempt %d/%d: Received HTTP %d for [%s / %s]",
                        attempt,
                        max_retries,
                        response.status,
                        protocol.upper(),
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
                    "Successfully fetched %d valid [%s] proxies for country [%s]",
                    len(proxies),
                    protocol.upper(),
                    country,
                )
                return proxies

        except urllib.error.URLError as err:
            logger.warning(
                "Attempt %d/%d failed for [%s / %s]: %s",
                attempt,
                max_retries,
                protocol.upper(),
                country,
                err,
            )
            if attempt < max_retries:
                time.sleep(RETRY_DELAY)
        except Exception as err:
            logger.error(
                "Unexpected error fetching proxies for [%s / %s]: %s",
                protocol.upper(),
                country,
                err,
            )
            break

    logger.error(
        "Failed to fetch proxies for [%s / %s] after %d attempts",
        protocol.upper(),
        country,
        max_retries,
    )
    return []


def format_proxy_lines(country: str, protocol: str, proxies: List[str]) -> List[str]:
    """Format proxy entries to the target format:
    `{protocol}://xxx:yyy#{COUNTRY_CODE}-{PROTOCOL}-{Number}`

    Args:
        country: Normalized uppercase country code.
        protocol: Proxy protocol name (e.g. 'socks5', 'http').
        proxies: List of host:port strings.

    Returns:
        Formatted proxy lines.
    """
    proto_lower = protocol.lower()
    proto_upper = protocol.upper()
    formatted: List[str] = []
    for idx, proxy in enumerate(proxies, start=1):
        line = f"{proto_lower}://{proxy}#{country}-{proto_upper}-{idx}"
        formatted.append(line)
    return formatted


def save_proxy_file(
    country: str,
    protocol: str,
    lines: List[str],
    output_dir: Path,
) -> Path:
    """Save formatted proxy lines to {COUNTRY_CODE}-{PROTOCOL}.txt.

    Args:
        country: Normalized uppercase country code.
        protocol: Proxy protocol name.
        lines: Formatted proxy lines.
        output_dir: Directory where the file should be saved.

    Returns:
        Path to the saved file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{country}-{protocol.upper()}.txt"
    filepath = output_dir / filename

    content = "\n".join(lines) + ("\n" if lines else "")
    filepath.write_text(content, encoding="utf-8")
    logger.info("Saved %d proxies to %s", len(lines), filepath)
    return filepath


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Fetch proxy lists (SOCKS5, SOCKS4, HTTP, HTTPS) from ProxyScrape."
    )
    parser.add_argument(
        "--countries",
        type=str,
        default=os.getenv("COUNTRIES", "US,DE,GB,FR,JP,HK,SG"),
        help="Comma-separated country codes (e.g. 'US,DE,JP' or 'ALL')",
    )
    parser.add_argument(
        "--protocols",
        type=str,
        default=os.getenv("PROTOCOLS", "socks5"),
        help="Comma-separated protocols (e.g. 'socks5', 'socks5,socks4,http,https')",
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
    raw_protocols: str = args.protocols
    token: Optional[str] = args.token.strip() if args.token else None
    output_dir = Path(args.output_dir)

    country_list = [
        normalize_country_code(c)
        for c in raw_countries.split(",")
        if c.strip()
    ]
    protocol_list = [
        normalize_protocol(p)
        for p in raw_protocols.split(",")
        if p.strip()
    ]

    if not country_list:
        logger.error("No valid country codes specified.")
        return 1

    if not protocol_list:
        logger.error("No valid protocols specified.")
        return 1

    logger.info("Processing countries: %s", ", ".join(country_list))
    logger.info("Processing protocols: %s", ", ".join(protocol_list))
    if token:
        logger.info("ProxyScrape token detected (length: %d).", len(token))
    else:
        logger.info("No ProxyScrape token provided; using public endpoint.")

    total_proxies = 0
    total_files = 0

    for protocol in protocol_list:
        for country in country_list:
            proxies = fetch_proxies_for_target(country, protocol=protocol, token=token)
            if proxies:
                formatted_lines = format_proxy_lines(country, protocol, proxies)
                save_proxy_file(country, protocol, formatted_lines, output_dir)
                total_proxies += len(proxies)
                total_files += 1
            else:
                logger.warning(
                    "No proxies found for [%s / %s], skipping file write.",
                    protocol.upper(),
                    country,
                )

    logger.info(
        "Finished: generated %d proxy files with %d total proxies.",
        total_files,
        total_proxies,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
