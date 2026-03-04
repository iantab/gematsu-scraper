# gematsu-scraper

Scrapes Famitsu weekly sales reports from [Gematsu](https://www.gematsu.com/tag/famitsu-sales) and outputs structured JSON.

## Requirements

- Python 3.14+
- Dependencies: `requests`, `beautifulsoup4`, `lxml`

```bash
pip install -r requirements.txt
```

## Usage

```bash
# Scrape latest report → json/famitsu_YYYY-MM-DD_YYYY-MM-DD.json
python scraper.py

# Scrape a specific past report → json/famitsu_YYYY-MM-DD_YYYY-MM-DD.json
python scraper.py https://www.gematsu.com/2026/02/famitsu-sales-2-9-26-2-15-26

# Write to an explicit file
python scraper.py -o out.json
python scraper.py https://www.gematsu.com/2026/02/famitsu-sales-2-9-26-2-15-26 -o out.json
```

## Output format

```json
{
  "report_url": "https://www.gematsu.com/...",
  "period_start": "2026-02-16",
  "period_end": "2026-02-22",
  "week_of_year": 8,
  "scraped_at": "2026-02-23T10:00:00Z",
  "software": [
    {
      "rank": 1,
      "platform": "PS5",
      "title": "Example Game",
      "publisher": "Example Publisher",
      "release_date": "02/19/26",
      "weekly_sales": 123456,
      "lifetime_sales": 123456,
      "is_new": true
    }
  ],
  "hardware": [
    {
      "rank": 1,
      "platform": "Switch 2",
      "weekly_sales": 123456,
      "lifetime_sales": 1234567
    }
  ]
}
```
