# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

def crawl_webpage(start_url: str, max_pages: int = 10) -> list[str]:
    """
    Crawl a webpage and find all web pages under it.
    Args:
        start_url (str): The URL to start crawling from
        max_pages (int): The maximum number of pages to crawl
    Returns:
        list[str]: A list of URLs found
    """
    print(f"Crawling {start_url} with max {max_pages} pages")

    visited_urls = set()
    urls_to_visit = [start_url]
    found_urls = []

    while urls_to_visit and len(visited_urls) < max_pages:
        current_url = urls_to_visit.pop(0)
        if current_url in visited_urls:
            continue

        try:
            response = requests.get(current_url)
            soup = BeautifulSoup(response.text, 'html.parser')
            visited_urls.add(current_url)
            found_urls.append(current_url)

            for a in soup.find_all('a', href=True):
                href = a['href']
                full_url = urljoin(current_url, href)
                if urlparse(full_url).netloc == urlparse(start_url).netloc and full_url not in visited_urls:
                    urls_to_visit.append(full_url)
        except Exception as e:
            print(f"Error crawling {current_url}: {e}")

    return found_urls 