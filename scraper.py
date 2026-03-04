import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Optional

import requests
from bs4 import BeautifulSoup

TAG_PAGE = "https://www.gematsu.com/tag/famitsu-sales"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; gematsu-scraper/1.0)"}
TIMEOUT = 15

SOFTWARE_RE = re.compile(
    r"^\[(?P<platform>[^\]]+)\]\s+"
    r"(?P<title>.+?)"
    r"\s+\((?P<publisher>[^,]+),\s*"
    r"(?P<release_date>\d{2}/\d{2}/\d{2,4})\)"
    r"\s*[\u2013\-]\s*"
    r"(?P<weekly>[0-9,]+)"
    r"(?:\s*\((?P<lifetime>[0-9,]+)\))?"
    r"(?P<remainder>.*)",
    re.UNICODE | re.DOTALL,
)

HARDWARE_RE = re.compile(
    r"^(?P<platform>.+?)\s*[\u2013\-]\s*"
    r"(?P<weekly>[0-9,]+)"
    r"(?:\s*\((?P<lifetime>[0-9,]+)\))?",
    re.UNICODE,
)


@dataclass
class SoftwareEntry:
    rank: int
    platform: str
    title: str
    publisher: str
    release_date: str
    weekly_sales: int
    lifetime_sales: Optional[int]
    is_new: bool


@dataclass
class HardwareEntry:
    rank: int
    platform: str
    weekly_sales: int
    lifetime_sales: Optional[int]


@dataclass
class SalesReport:
    report_url: str
    period_start: str
    period_end: str
    week_of_year: int
    scraped_at: str
    software: list = field(default_factory=list)
    hardware: list = field(default_factory=list)


def fetch(url: str) -> str:
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    return r.content.decode("utf-8")


def find_latest_report_url(tag_html: str) -> str:
    soup = BeautifulSoup(tag_html, "lxml")
    pattern = re.compile(r"/\d{4}/\d{2}/famitsu-sales-")
    links = soup.find_all("a", href=pattern)
    if not links:
        raise ValueError("No Famitsu sales report links found on tag page.")
    return links[0]["href"]


def parse_period(soup: BeautifulSoup) -> tuple[str, str, int]:
    period_str = None

    date_range_re = re.compile(
        r"(\d{1,2}/\d{1,2}/\d{2,4}\s*[\u2013\u2014\-]\s*\d{1,2}/\d{1,2}/\d{2,4})"
    )

    title_tag = soup.find("title")
    if title_tag:
        m = date_range_re.search(title_tag.get_text())
        if m:
            period_str = m.group(1).strip()

    if not period_str:
        h1 = soup.find("h1")
        if h1:
            m = date_range_re.search(h1.get_text())
            if m:
                period_str = m.group(1).strip()

    if not period_str:
        raise ValueError("Could not extract period string from page title or h1.")

    parts = re.split(r"\u2013|\u2014|–|—|\s-\s", period_str)
    if len(parts) < 2:
        raise ValueError(f"Could not split period string: {period_str!r}")

    start_str = parts[0].strip()
    end_str = parts[1].strip()

    start_dt = datetime.strptime(start_str, "%m/%d/%y")
    end_dt = datetime.strptime(end_str, "%m/%d/%y")

    week_of_year = start_dt.isocalendar().week

    return start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d"), week_of_year


def find_section_ols(soup: BeautifulSoup):
    content = soup.find("div", class_="entry-content")
    if not content:
        content = soup.body

    software_ol = None
    hardware_ol = None
    mode = None

    for tag in content.descendants:
        if tag.name in ("p", "strong", "h2", "h3"):
            text = tag.get_text().lower()
            if "software" in text:
                mode = "software"
            elif "hardware" in text:
                mode = "hardware"
        elif tag.name == "ol":
            if mode == "software" and software_ol is None:
                software_ol = tag
            elif mode == "hardware" and hardware_ol is None:
                hardware_ol = tag

    if software_ol is None or hardware_ol is None:
        ols = content.find_all("ol")
        if len(ols) >= 1 and software_ol is None:
            software_ol = ols[0]
        if len(ols) >= 2 and hardware_ol is None:
            hardware_ol = ols[1]

    return software_ol, hardware_ol


def parse_software(ol) -> list[SoftwareEntry]:
    entries = []
    for rank, li in enumerate(ol.find_all("li"), start=1):
        text = li.get_text(" ", strip=True)
        m = SOFTWARE_RE.match(text)
        if not m:
            print(f"WARNING: could not parse software li #{rank}: {text!r}", file=sys.stderr)
            continue
        weekly = int(m.group("weekly").replace(",", ""))
        lifetime_raw = m.group("lifetime")
        lifetime = int(lifetime_raw.replace(",", "")) if lifetime_raw else None
        is_new = "new" in m.group("remainder").lower()
        entries.append(SoftwareEntry(
            rank=rank,
            platform=m.group("platform"),
            title=m.group("title"),
            publisher=m.group("publisher"),
            release_date=m.group("release_date"),
            weekly_sales=weekly,
            lifetime_sales=lifetime,
            is_new=is_new,
        ))
    return entries


def parse_hardware(ol) -> list[HardwareEntry]:
    entries = []
    for rank, li in enumerate(ol.find_all("li"), start=1):
        text = li.get_text(" ", strip=True)
        m = HARDWARE_RE.match(text)
        if not m:
            print(f"WARNING: could not parse hardware li #{rank}: {text!r}", file=sys.stderr)
            continue
        weekly = int(m.group("weekly").replace(",", ""))
        lifetime_raw = m.group("lifetime")
        lifetime = int(lifetime_raw.replace(",", "")) if lifetime_raw else None
        entries.append(HardwareEntry(
            rank=rank,
            platform=m.group("platform").strip(),
            weekly_sales=weekly,
            lifetime_sales=lifetime,
        ))
    return entries


def scrape(url: str | None = None) -> SalesReport:
    if url:
        report_url = url if url.startswith("http") else "https://www.gematsu.com" + url
    else:
        tag_html = fetch(TAG_PAGE)
        report_url = find_latest_report_url(tag_html)
        if not report_url.startswith("http"):
            report_url = "https://www.gematsu.com" + report_url

    report_html = fetch(report_url)
    soup = BeautifulSoup(report_html, "lxml")

    period_start, period_end, week_of_year = parse_period(soup)
    software_ol, hardware_ol = find_section_ols(soup)

    software = parse_software(software_ol) if software_ol else []
    hardware = parse_hardware(hardware_ol) if hardware_ol else []

    if not software:
        print("WARNING: no software entries parsed.", file=sys.stderr)
    if not hardware:
        print("WARNING: no hardware entries parsed.", file=sys.stderr)

    scraped_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    return SalesReport(
        report_url=report_url,
        period_start=period_start,
        period_end=period_end,
        week_of_year=week_of_year,
        scraped_at=scraped_at,
        software=[asdict(e) for e in software],
        hardware=[asdict(e) for e in hardware],
    )


def main():
    parser = argparse.ArgumentParser(description="Scrape a Famitsu sales report from Gematsu.")
    parser.add_argument("url", nargs="?", default=None,
                        help="Specific report URL to scrape (default: latest).")
    parser.add_argument("-o", "--output", metavar="FILE", help="Write JSON to FILE (default: json/ subfolder).")
    args = parser.parse_args()

    report = scrape(args.url)
    output = json.dumps(asdict(report), ensure_ascii=False, indent=2)

    if args.output:
        out_path = args.output
    else:
        os.makedirs("json", exist_ok=True)
        filename = f"famitsu_{report.period_start}_{report.period_end}.json"
        out_path = os.path.join("json", filename)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(output)
    print(f"Written to {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
