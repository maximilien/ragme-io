# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import re
from datetime import datetime, timedelta
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


def crawl_webpage(start_url: str, max_pages: int = 10) -> list[str]:
    """
    Crawl a webpage and extract all URLs that match the search term.

    Args:
        start_url (str): The starting URL to crawl
        max_pages (int): Maximum number of pages to crawl

    Returns:
        list[str]: List of URLs found
    """
    urls = []
    visited = set()

    def crawl(url: str, depth: int = 0):
        if depth >= max_pages or url in visited:
            return

        visited.add(url)

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

            # Extract all links
            for link in soup.find_all("a", href=True):
                href = link["href"]
                absolute_url = urljoin(url, href)

                # Only include HTTP/HTTPS URLs
                if absolute_url.startswith(("http://", "https://")):
                    urls.append(absolute_url)

                    # Recursively crawl if we haven't reached max_pages
                    if len(urls) < max_pages:
                        crawl(absolute_url, depth + 1)

        except Exception as e:
            print(f"Error crawling {url}: {e}")

    crawl(start_url)
    return urls[:max_pages]


def parse_date_query(query: str) -> tuple[datetime, datetime] | None:
    """
    Parse natural language date queries into datetime ranges.

    Args:
        query (str): Natural language date query (e.g., "yesterday", "today", "last week")

    Returns:
        Optional[Tuple[datetime, datetime]]: Start and end datetime, or None if not recognized
    """
    query_lower = query.lower().strip()
    now = datetime.now()

    # Today
    if "today" in query_lower:
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        return start_date, end_date

    # Yesterday
    if "yesterday" in query_lower:
        yesterday = now - timedelta(days=1)
        start_date = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
        return start_date, end_date

    # This week
    if "this week" in query_lower or "current week" in query_lower:
        start_date = now - timedelta(days=now.weekday())
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        return start_date, end_date

    # Last week
    if "last week" in query_lower or "previous week" in query_lower:
        start_date = now - timedelta(days=now.weekday() + 7)
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(
            days=6, hours=23, minutes=59, seconds=59, microseconds=999999
        )
        return start_date, end_date

    # This month
    if "this month" in query_lower or "current month" in query_lower:
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        return start_date, end_date

    # Last month
    if "last month" in query_lower or "previous month" in query_lower:
        if now.month == 1:
            start_date = now.replace(
                year=now.year - 1,
                month=12,
                day=1,
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
            )
        else:
            start_date = now.replace(
                month=now.month - 1, day=1, hour=0, minute=0, second=0, microsecond=0
            )
        end_date = start_date.replace(day=28) + timedelta(days=4)
        end_date = end_date.replace(day=1) - timedelta(microseconds=1)
        return start_date, end_date

    # This year
    if "this year" in query_lower or "current year" in query_lower:
        start_date = now.replace(
            month=1, day=1, hour=0, minute=0, second=0, microsecond=0
        )
        end_date = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        return start_date, end_date

    # Last year
    if "last year" in query_lower or "previous year" in query_lower:
        start_date = now.replace(
            year=now.year - 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0
        )
        end_date = start_date.replace(
            month=12, day=31, hour=23, minute=59, second=59, microsecond=999999
        )
        return start_date, end_date

    # Specific number of days ago
    days_match = re.search(r"(\d+)\s+days?\s+ago", query_lower)
    if days_match:
        days = int(days_match.group(1))
        target_date = now - timedelta(days=days)
        start_date = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = target_date.replace(
            hour=23, minute=59, second=59, microsecond=999999
        )
        return start_date, end_date

    # Specific number of weeks ago
    weeks_match = re.search(r"(\d+)\s+weeks?\s+ago", query_lower)
    if weeks_match:
        weeks = int(weeks_match.group(1))
        target_date = now - timedelta(weeks=weeks)
        start_date = target_date - timedelta(days=target_date.weekday())
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(
            days=6, hours=23, minutes=59, seconds=59, microseconds=999999
        )
        return start_date, end_date

    # Specific number of months ago
    months_match = re.search(r"(\d+)\s+months?\s+ago", query_lower)
    if months_match:
        months = int(months_match.group(1))
        target_date = now
        for _ in range(months):
            if target_date.month == 1:
                target_date = target_date.replace(year=target_date.year - 1, month=12)
            else:
                target_date = target_date.replace(month=target_date.month - 1)
        start_date = target_date.replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        # End of month
        if target_date.month == 12:
            end_date = target_date.replace(
                year=target_date.year + 1, month=1, day=1
            ) - timedelta(microseconds=1)
        else:
            end_date = target_date.replace(
                month=target_date.month + 1, day=1
            ) - timedelta(microseconds=1)
        return start_date, end_date

    return None


def filter_items_by_date_range(
    items: list, start_date: datetime, end_date: datetime
) -> list:
    """
    Filter items by date range based on their date_added metadata.

    Args:
        items (list): List of items (documents or images) to filter
        start_date (datetime): Start of date range
        end_date (datetime): End of date range

    Returns:
        list: Filtered items within the date range
    """
    filtered_items = []

    for item in items:
        metadata = item.get("metadata", {})
        if isinstance(metadata, str):
            try:
                import json

                metadata = json.loads(metadata)
            except (json.JSONDecodeError, TypeError):
                metadata = {}

        date_added_str = metadata.get("date_added")
        if not date_added_str:
            continue

        try:
            # Parse the date_added string
            if date_added_str.endswith("Z"):
                # Handle UTC time (with Z suffix)
                date_added = datetime.fromisoformat(
                    date_added_str.replace("Z", "+00:00")
                )
                # Convert to local time for consistent comparison with start_date and end_date
                date_added_local = date_added.astimezone()
            else:
                # Handle local time (no timezone suffix)
                date_added_local = datetime.fromisoformat(date_added_str)

            # Make date_added_local naive for comparison with start_date and end_date (which are also naive)
            date_added_naive = date_added_local.replace(tzinfo=None)
            if start_date <= date_added_naive <= end_date:
                filtered_items.append(item)
        except (ValueError, TypeError):
            # Skip items with invalid dates
            continue

    return filtered_items
