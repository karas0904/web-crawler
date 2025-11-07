from crawler import get_gazette_structure
from downloader import download_all_pdfs
from utils import print_info


if __name__ == "__main__":
    BASE_DIR = "/Users/karmesh/Desktop/shoura,web scrapping itern/"
    BASE_URL = "https://dlp.dubai.gov.ae/ar/Pages/OfficialGazette.aspx?lang=en"

    print_info("Starting Gazette Scraper...")
    structure = get_gazette_structure(BASE_URL)
    print_info("Crawled structure:")
    print(structure)

    download_all_pdfs(structure, BASE_DIR)
    print_info("Done.")
