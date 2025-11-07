import time
from typing import Dict, List, Tuple

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException

from utils import print_info


def _build_driver(headless: bool = True) -> webdriver.Chrome:
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)


def _extract_direct_pdf(driver: webdriver.Chrome, viewer_url: str) -> str | None:
    wait = WebDriverWait(driver, 20)
    original = driver.current_window_handle
    try:
        driver.execute_script("window.open(arguments[0], '_blank');", viewer_url)
        wait.until(EC.number_of_windows_to_be(2))
        handles = driver.window_handles
        driver.switch_to.window(handles[-1])
        try:
            a_tag = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".df-ui-download")))
            pdf_url = a_tag.get_attribute("href")
            if pdf_url and pdf_url.startswith("/"):
                pdf_url = "https://dlp.dubai.gov.ae" + pdf_url
            return pdf_url
        except TimeoutException:
            return None
        finally:
            driver.close()
            driver.switch_to.window(original)
    except Exception:
        # Best-effort: if anything fails, return None
        try:
            # Ensure we are back to original window
            driver.switch_to.window(original)
        except Exception:
            pass
        return None


def get_gazette_structure(base_url: str) -> Dict[str, Dict[str, List[Tuple[str, str]]]]:
    """
    Navigate the Gazette landing page, click the 1960s decade, then iterate years 1962-1969
    (skip 1961), collecting tuples of (display_number, PDFViewer URL) for each year.
    Returns: { '1960s': { '1962': [(num, viewer_url), ...], ... } }
    """
    driver = _build_driver(headless=True)
    wait = WebDriverWait(driver, 20)

    structure: Dict[str, Dict[str, List[Tuple[str, str]]]] = {"2000s": {}, "2020s": {}}

    try:
        driver.get(base_url)
        time.sleep(2)

        decades_to_process = [
            ("2000s", "2000", range(2000, 2010)),
            ("2020s", "2020", range(2020, 2026)),
        ]

        for decade_label, decade_code, year_range in decades_to_process:
            # Move carousel until the target decade div is visible, then click it
            try:
                clicked_decade = False
                for _ in range(30):
                    decade_divs = driver.find_elements(
                        By.CSS_SELECTOR,
                        f"div.years_col[onclick*='decade_{decade_code}']"
                    )
                    if decade_divs:
                        decade_el = decade_divs[0]
                        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", decade_el)
                        time.sleep(0.3)
                        driver.execute_script("arguments[0].click();", decade_el)
                        clicked_decade = True
                        break
                    next_btn = driver.find_elements(By.CSS_SELECTOR, "div.owl-next")
                    if next_btn:
                        driver.execute_script("arguments[0].click();", next_btn[0])
                        time.sleep(0.4)
                if not clicked_decade:
                    # Fallback: click the decade image wrapper
                    img = None
                    try:
                        img = driver.find_element(By.CSS_SELECTOR, f"img[src*='{decade_label}']")
                    except Exception:
                        pass
                    if img:
                        parent = img.find_element(By.XPATH, "ancestor::div[contains(@class,'years_col')]")
                        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", parent)
                        time.sleep(0.2)
                        driver.execute_script("arguments[0].click();", parent)
                        clicked_decade = True
                if not clicked_decade:
                    # Fallback: text-based
                    nodes = driver.find_elements(By.XPATH, f"//div[contains(@class,'years_col')][.//text()[contains(.,'{decade_label}')]]")
                    if nodes:
                        node = nodes[0]
                        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", node)
                        time.sleep(0.2)
                        driver.execute_script("arguments[0].click();", node)
                        clicked_decade = True
                if clicked_decade:
                    print_info(f"Clicked {decade_label} decade div!")
                    # Best-effort wait for the first year of this decade to appear
                    try:
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, f"span[data-value='year_{year_range.start}']"))
                        )
                    except Exception:
                        pass
                else:
                    print_info(f"Could not find {decade_label} decade tile to click")
                time.sleep(1.0)
            except Exception as e:
                print_info(f"Could not find/click {decade_label} decade div: {e}")

            # Process years for this decade
            for yr in year_range:
                year_str = str(yr)
                print_info(f"--- Processing year: {year_str} ---")
                pdf_tuples: List[Tuple[str, str]] = []
                structure[decade_label][year_str] = pdf_tuples

                try:
                    year_span = wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, f"span[data-value='year_{year_str}']"))
                    )
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", year_span)
                    time.sleep(0.2)
                    driver.execute_script("arguments[0].click();", year_span)
                    print_info(f"Clicked year: {year_str}")

                    # Wait for either card covers or PDF viewer anchors to appear
                    try:
                        wait.until(
                            EC.presence_of_element_located(
                                (
                                    By.CSS_SELECTOR,
                                    "div._df_book-cover.thumb-div, div._df_book-cover, a[href*='PDFViewer.aspx?file=']",
                                )
                            )
                        )
                    except Exception:
                        print_info(f"WARN: No cards/anchors became present for {year_str} after click.")
                    time.sleep(0.5)

                    # Attempt to load lazy content by scrolling to bottom repeatedly until count stabilizes
                    try:
                        prev = -1
                        for _ in range(8):
                            current = len(driver.find_elements(By.CSS_SELECTOR, "div._df_book-cover.thumb-div, div._df_book-cover"))
                            if current <= prev:
                                break
                            prev = current
                            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                            time.sleep(0.5)
                        # Scroll back to top for consistent element positions
                        driver.execute_script("window.scrollTo(0, 0);")
                        time.sleep(0.3)
                    except Exception:
                        pass

                except Exception as e:
                    print_info(f"Could not find/click year {year_str}: {e}")
                    structure[decade_label][year_str] = []
                    continue

                seen_urls = set()

                # Prefer card elements to avoid duplicated overlay anchors; handle horizontal carousel pagination
                try:
                    # Find an ancestor container that likely holds the carousel
                    def collect_cards() -> List:
                        return driver.find_elements(By.CSS_SELECTOR, "div._df_book-cover.thumb-div, div._df_book-cover")

                    def page_cards_to_tuples(cards_now: List) -> None:
                        for idx, card in enumerate(cards_now):
                            try:
                                # Extract display number
                                display_num = None
                                try:
                                    num_span = card.find_element(By.CSS_SELECTOR, "span._df_book-No, span.num-in-card, span.badge")
                                    display_num = num_span.text.strip()
                                except Exception:
                                    display_num = None
                                if not display_num:
                                    display_num = str(idx + 1)

                                # Find ancestor anchor to viewer page
                                a_tag = card.find_element(By.XPATH, "./ancestor::a[contains(@href, 'PDFViewer.aspx?file=') or contains(@href, 'PDFViewer.aspx?file=')]")
                                href_val = a_tag.get_attribute("href")
                                if href_val and href_val.startswith("/"):
                                    href_val = "https://dlp.dubai.gov.ae" + href_val
                                direct_pdf = _extract_direct_pdf(driver, href_val) if href_val else None
                                final_url = direct_pdf or href_val
                                # Only include PDFs that clearly belong to this year (e.g., OGD_1962_*.pdf)
                                if final_url and final_url.lower().endswith('.pdf') and f"_{year_str}_" not in final_url:
                                    continue
                                if final_url and final_url not in seen_urls:
                                    pdf_tuples.append((display_num, final_url))
                                    seen_urls.add(final_url)
                            except Exception:
                                continue

                    # Iterate pages by clicking the local owl-next until exhausted
                    last_count = -1
                    for _ in range(30):
                        cards_now = collect_cards()
                        page_cards_to_tuples(cards_now)
                        if len(seen_urls) <= last_count:
                            break
                        last_count = len(seen_urls)
                        # Try click a local next button near cards
                        next_candidates = driver.find_elements(By.CSS_SELECTOR, "div.owl-next")
                        clicked = False
                        for btn in next_candidates:
                            try:
                                # Only click if button is displayed and in viewport
                                if btn.is_displayed():
                                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
                                    time.sleep(0.2)
                                    driver.execute_script("arguments[0].click();", btn)
                                    clicked = True
                                    time.sleep(0.5)
                                    break
                            except Exception:
                                continue
                        if not clicked:
                            break
                except Exception:
                    # Fallback to anchors if carousel handling fails
                    pdf_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='PDFViewer.aspx?file=']")
                    for idx in range(len(pdf_links)):
                        try:
                            links_now = driver.find_elements(By.CSS_SELECTOR, "a[href*='PDFViewer.aspx?file=']")
                            if idx >= len(links_now):
                                break
                            a_tag = links_now[idx]
                            viewer_url = a_tag.get_attribute("href")
                            # Heuristics to find a nearby numeric label
                            display_num = None
                            try:
                                candidates = a_tag.find_elements(
                                    By.XPATH,
                                    ".//span[contains(@class, 'book-No') or contains(@class, 'badge') or contains(@class, 'num') or contains(@class, '_df_book-No')] | .//div[contains(@class,'numbers')]",
                                )
                                for c in candidates:
                                    txt = c.text.strip()
                                    if txt.isdigit():
                                        display_num = txt
                                        break
                                if not display_num:
                                    parent = a_tag.find_element(By.XPATH, "..")
                                    siblings = parent.find_elements(
                                        By.XPATH,
                                        ".//span[contains(@class, 'book-No') or contains(@class, 'badge') or contains(@class, 'num') or contains(@class, '_df_book-No')] | .//div[contains(@class,'numbers')]",
                                    )
                                    for c in siblings:
                                        txt = c.text.strip()
                                        if txt.isdigit():
                                            display_num = txt
                                            break
                            except Exception:
                                pass
                            if not display_num:
                                display_num = str(idx + 1)
                            if viewer_url and viewer_url.startswith("/"):
                                viewer_url = "https://dlp.dubai.gov.ae" + viewer_url
                            direct_pdf = _extract_direct_pdf(driver, viewer_url) if viewer_url else None
                            final_url = direct_pdf or viewer_url
                            if final_url and final_url.lower().endswith('.pdf') and f"_{year_str}_" not in final_url:
                                continue
                            if final_url and final_url not in seen_urls:
                                pdf_tuples.append((display_num, final_url))
                                seen_urls.add(final_url)
                        except Exception:
                            continue

                # Anchor sweep to catch any offscreen/hidden DOM items for this year
                try:
                    pdf_links_all = driver.find_elements(By.CSS_SELECTOR, "a[href*='PDFViewer.aspx?file=']")
                    for idx2, a_tag in enumerate(pdf_links_all):
                        try:
                            viewer_url = a_tag.get_attribute("href")
                            # Attempt to read a numeric label near the anchor
                            display_num = None
                            try:
                                candidates = a_tag.find_elements(
                                    By.XPATH,
                                    ".//span[contains(@class, 'book-No') or contains(@class, 'badge') or contains(@class, 'num') or contains(@class, '_df_book-No')] | .//div[contains(@class,'numbers')]",
                                )
                                for c in candidates:
                                    txt = c.text.strip()
                                    if txt.isdigit():
                                        display_num = txt
                                        break
                                if not display_num:
                                    parent = a_tag.find_element(By.XPATH, "..")
                                    siblings = parent.find_elements(
                                        By.XPATH,
                                        ".//span[contains(@class, 'book-No') or contains(@class, 'badge') or contains(@class, 'num') or contains(@class, '_df_book-No')] | .//div[contains(@class,'numbers')]",
                                    )
                                    for c in siblings:
                                        txt = c.text.strip()
                                        if txt.isdigit():
                                            display_num = txt
                                            break
                            except Exception:
                                pass
                            if not display_num:
                                display_num = str(len(pdf_tuples) + 1)

                            if viewer_url and viewer_url.startswith("/"):
                                viewer_url = "https://dlp.dubai.gov.ae" + viewer_url
                            direct_pdf = _extract_direct_pdf(driver, viewer_url) if viewer_url else None
                            final_url = direct_pdf or viewer_url
                            if final_url and final_url.lower().endswith('.pdf') and f"_{year_str}_" not in final_url:
                                continue
                            if final_url and final_url not in seen_urls:
                                pdf_tuples.append((display_num, final_url))
                                seen_urls.add(final_url)
                        except Exception:
                            continue
                except Exception:
                    pass

                print_info(f"Found {len(pdf_tuples)} unique PDFs for {year_str}.")

    finally:
        driver.quit()

    return structure
