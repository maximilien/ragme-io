# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import sys
import os
import pytest
import requests
import requests_mock

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ragme.common import crawl_webpage

def test_crawl_webpage():
    """Test the crawl_webpage function with mocked responses."""
    base_url = "https://example.com"
    page1_html = """
    <html>
        <body>
            <a href="/page2">Page 2</a>
            <a href="/page3">Page 3</a>
        </body>
    </html>
    """
    page2_html = """
    <html>
        <body>
            <a href="/page1">Page 1</a>
            <a href="/page4">Page 4</a>
        </body>
    </html>
    """
    page3_html = """
    <html>
        <body>
            <a href="/page1">Page 1</a>
        </body>
    </html>
    """

    with requests_mock.Mocker() as m:
        # Mock responses for each page
        m.get(f"{base_url}/", text=page1_html)
        m.get(f"{base_url}/page2", text=page2_html)
        m.get(f"{base_url}/page3", text=page3_html)
        m.get(f"{base_url}/page4", text="<html><body>Page 4</body></html>")

        # Test crawling with max_pages=3
        urls = crawl_webpage(base_url, max_pages=3)
        
        # Should find exactly 3 pages
        assert len(urls) == 3
        assert f"{base_url}" in urls
        assert f"{base_url}/page2" in urls
        assert f"{base_url}/page3" in urls

def test_crawl_webpage_with_error():
    """Test the crawl_webpage function handling errors."""
    base_url = "https://example.com"
    page1_html = """
    <html>
        <body>
            <a href="/page2">Page 2</a>
            <a href="/error">Error Page</a>
        </body>
    </html>
    """

    with requests_mock.Mocker() as m:
        # Mock successful response for main page
        m.get(f"{base_url}/", text=page1_html)
        # Mock error for error page
        m.get(f"{base_url}/error", exc=requests.exceptions.RequestException)

        # Test crawling with error handling
        urls = crawl_webpage(base_url, max_pages=2)
        
        # Should only find the main page
        assert len(urls) == 1
        assert f"{base_url}" in urls

def test_crawl_webpage_external_links():
    """Test that crawl_webpage only follows links within the same domain."""
    base_url = "https://example.com"
    page1_html = """
    <html>
        <body>
            <a href="https://other-domain.com">External Link</a>
            <a href="/page2">Internal Link</a>
        </body>
    </html>
    """
    page2_html = """
    <html>
        <body>
            <a href="/page1">Back to Page 1</a>
        </body>
    </html>
    """

    with requests_mock.Mocker() as m:
        # Mock responses
        m.get(f"{base_url}/", text=page1_html)
        m.get(f"{base_url}/page2", text=page2_html)

        # Test crawling
        urls = crawl_webpage(base_url, max_pages=2)
        
        # Should only find pages from example.com
        assert len(urls) == 2
        assert f"{base_url}" in urls
        assert f"{base_url}/page2" in urls
 