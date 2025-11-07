import os
import time
from typing import Dict, List, Tuple

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from utils import sanitize_filename, print_info


def _build_driver(headless: bool = True) -> webdriver.Chrome:
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)


# NOTE: We no longer use Selenium to resolve viewer pages here due to network/driver fetch issues.
# All URLs provided to the downloader should already be direct .pdf links from the crawler.

def _download_to_path(pdf_url: str, pdf_path: str) -> bool:
    # Simple retry with backoff (handles transient DNS/connection issues)
    attempts = 5
    for attempt in range(1, attempts + 1):
        try:
            resp = requests.get(pdf_url, timeout=60)
            resp.raise_for_status()
            with open(pdf_path, "wb") as f:
                f.write(resp.content)
            print_info(f"Saved: {pdf_path}")
            return True
        except Exception as e:
            print_info(f"Attempt {attempt}/{attempts} failed for {pdf_url}: {e}")
            time.sleep(min(2 * attempt, 10))
    return False


def _desired_filename(i: int, display_num: str) -> str:
    file_base = (display_num or "").strip() or str(i + 1)
    return f"{file_base}.pdf"


def download_all_pdfs(structure: Dict[str, Dict[str, List[Tuple[str, str]]]], base_dir: str) -> None:
    for decade, years in structure.items():
        for year, pdf_tuples in years.items():
            year_dir = os.path.join(base_dir, sanitize_filename(decade), sanitize_filename(year))
            os.makedirs(year_dir, exist_ok=True)

            # First pass: attempt all
            total = len(pdf_tuples)
            for i, (display_num, url) in enumerate(pdf_tuples):
                pdf_filename = _desired_filename(i, display_num)
                pdf_path = os.path.join(year_dir, pdf_filename)

                if os.path.exists(pdf_path):
                    print_info(f"Exists, skip: {pdf_path}")
                    continue

                if not url or not url.lower().endswith(".pdf"):
                    print_info(f"Skip, not a direct PDF URL (expected .pdf): {url}")
                    continue

                print_info(f"Downloading PDF from: {url}")
                _download_to_path(url, pdf_path)

            # Verify and retry missing once
            existing = {name for name in os.listdir(year_dir) if name.lower().endswith(".pdf")}
            expected = { _desired_filename(i, dn) for i, (dn, _) in enumerate(pdf_tuples) if _ and str(_) }
            # The expected set above includes only entries that had tuples; but we only can download those with .pdf URLs
            # Build expected only from tuples that have .pdf URLs
            expected = { _desired_filename(i, dn) for i, (dn, u) in enumerate(pdf_tuples) if u and u.lower().endswith('.pdf') }
            missing = sorted(expected - existing)
            if missing:
                print_info(f"VERIFY: {len(existing)}/{len(expected)} downloaded for {decade}/{year}. Retrying {len(missing)} missing...")
                for i, (display_num, url) in enumerate(pdf_tuples):
                    pdf_filename = _desired_filename(i, display_num)
                    if pdf_filename not in missing:
                        continue
                    if not url or not url.lower().endswith(".pdf"):
                        print_info(f"Retry skip, not a direct PDF URL: {url}")
                        continue
                    pdf_path = os.path.join(year_dir, pdf_filename)
                    print_info(f"Retry downloading PDF from: {url}")
                    _download_to_path(url, pdf_path)

            # Final report per year
            final_existing = [name for name in os.listdir(year_dir) if name.lower().endswith(".pdf")]
            print_info(f"DONE {decade}/{year}: {len(final_existing)}/{len(expected)} files present")
