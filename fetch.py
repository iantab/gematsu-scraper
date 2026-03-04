import re

import requests
from bs4 import BeautifulSoup

TAG_PAGE = "https://www.gematsu.com/tag/famitsu-sales"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; gematsu-scraper/1.0)"}
TIMEOUT = 15


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
