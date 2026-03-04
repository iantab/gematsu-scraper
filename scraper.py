import argparse
import json
import os
import sys
from dataclasses import asdict
from datetime import datetime, timezone

from bs4 import BeautifulSoup

import fetch as _fetch
import parser as _parser
from models import SalesReport


def scrape(url: str | None = None) -> SalesReport:
    if url:
        report_url = url if url.startswith("http") else "https://www.gematsu.com" + url
    else:
        tag_html = _fetch.fetch(_fetch.TAG_PAGE)
        report_url = _fetch.find_latest_report_url(tag_html)
        if not report_url.startswith("http"):
            report_url = "https://www.gematsu.com" + report_url

    report_html = _fetch.fetch(report_url)
    soup = BeautifulSoup(report_html, "lxml")

    period_start, period_end, week_of_year = _parser.parse_period(soup)
    software_ol, hardware_ol = _parser.find_section_ols(soup)

    software = _parser.parse_software(software_ol) if software_ol else []
    hardware = _parser.parse_hardware(hardware_ol) if hardware_ol else []

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
    ap = argparse.ArgumentParser(
        description="Scrape a Famitsu sales report from Gematsu."
    )
    ap.add_argument(
        "url",
        nargs="?",
        default=None,
        help="Specific report URL to scrape (default: latest).",
    )
    ap.add_argument(
        "-o",
        "--output",
        metavar="FILE",
        help="Write JSON to FILE (default: json/ subfolder).",
    )
    args = ap.parse_args()

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
