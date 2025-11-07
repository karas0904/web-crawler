# Dubai Official Gazette PDF Scraper

A Python web scraper that automatically downloads PDF files from the Dubai Official Gazette website (https://dlp.dubai.gov.ae/ar/Pages/OfficialGazette.aspx). The scraper organizes downloaded PDFs into a structured folder hierarchy by decade and year.

## Features

- **Automated Web Scraping**: Uses Selenium to navigate dynamic JavaScript-driven pages
- **Structured Organization**: Downloads PDFs into `decade_name/year_name/downloaded_file_name.pdf` structure
- **Multi-Decade Support**: Currently configured to scrape:
  - **2000s**: Years 2000-2009
  - **2020s**: Years 2020-2025
- **Robust Error Handling**: Includes retry logic and verification to ensure complete downloads
- **Duplicate Prevention**: Skips already downloaded files
- **Year Verification**: Verifies downloaded file counts match crawled counts per year

## Requirements

- Python 3.7 or higher
- Google Chrome browser installed
- Internet connection

## Installation

1. **Clone or download this repository**

2. **Create a virtual environment** (recommended):

   ```bash
   python3 -m venv gazette-venv
   source gazette-venv/bin/activate  # On Windows: gazette-venv\Scripts\activate
   ```

3. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

   This will install:

   - `requests` - For downloading PDF files
   - `beautifulsoup4` - HTML parsing (legacy, currently using Selenium)
   - `selenium` - Web browser automation
   - `webdriver_manager` - Automatic ChromeDriver management

## Configuration

Before running, you may want to adjust settings in `main.py`:

- **BASE_DIR**: Change the download directory path (default: `/Users/karmesh/Desktop/shoura,web scrapping itern/`)
- **BASE_URL**: The target website URL (default: `https://dlp.dubai.gov.ae/ar/Pages/OfficialGazette.aspx?lang=en`)

To change which decades/years to scrape, edit `crawler.py`:

- Modify the `decades_to_process` list in the `get_gazette_structure()` function

## How to Run

1. **Activate your virtual environment** (if using one):

   ```bash
   source gazette-venv/bin/activate  # On Windows: gazette-venv\Scripts\activate
   ```

2. **Run the main script**:

   ```bash
   python main.py
   ```

   Or with full path:

   ```bash
   python "main.py"
   ```

3. **Monitor progress**: The script will print progress messages showing:
   - Which decade/year is being processed
   - How many PDFs were found for each year
   - Download status for each file
   - Verification results after each year completes

## Project Structure

```
.
├── main.py              # Entry point - orchestrates crawling and downloading
├── crawler.py           # Web scraping logic - navigates site and extracts PDF links
├── downloader.py        # PDF download logic - handles file downloads and organization
├── utils.py             # Utility functions (filename sanitization, logging)
├── requirements.txt     # Python package dependencies
└── README.md           # This file
```

## How It Works

1. **Crawling Phase** (`crawler.py`):

   - Opens the Dubai Official Gazette website
   - Navigates through decade carousel to find target decades (2000s, 2020s)
   - Clicks each year tab within the selected decade
   - Extracts PDF card elements from horizontal carousels
   - Resolves viewer page URLs to direct PDF download links
   - Returns a nested dictionary structure: `{decade: {year: [(display_num, pdf_url), ...]}}`

2. **Downloading Phase** (`downloader.py`):
   - Creates directory structure: `decade_name/year_name/`
   - Downloads each PDF using the direct URL
   - Names files using the display number from the website
   - Skips files that already exist
   - Verifies download completeness and retries missing files

## Output Structure

Downloaded files are organized as:

```
BASE_DIR/
├── 2000s/
│   ├── 2000/
│   │   ├── 1.pdf
│   │   ├── 2.pdf
│   │   └── ...
│   ├── 2001/
│   │   └── ...
│   └── ...
└── 2020s/
    ├── 2020/
    │   └── ...
    └── ...
```
