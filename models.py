from dataclasses import dataclass, field
from typing import Optional


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
