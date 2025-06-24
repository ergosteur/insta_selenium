# insta_selenium

A Python tool for scraping and downloading Instagram post and reel media using Selenium WebDriver.

## Features

- Scrape post and reel URLs from public Instagram profiles
- Download images and videos from posts and reels
- Save post metadata (caption, timestamp, etc.)
- Resume interrupted downloads and avoid duplicates
- Supports headless mode for automated/scripted use

## Prerequisites

- **Python 3.8+**  
  [Download Python](https://www.python.org/downloads/)
- **Mozilla Firefox browser**  
  [Download Firefox](https://www.mozilla.org/firefox/)
- **GeckoDriver** (Firefox WebDriver)  
  [Download geckodriver](https://github.com/mozilla/geckodriver/releases) and ensure it's in your PATH.  
  *On Windows 11, geckodriver is available via WinGet:*  
  ```bash
  winget install --id Mozilla.GeckoDriver
  ```
- **pip**, **pipx**, or **git**  
  - [pip](https://pip.pypa.io/en/stable/installation/)
  - [pipx](https://pypa.github.io/pipx/)
  - [git](https://git-scm.com/)

## Installation

### via pipx (recommended, easiest)

Install using pip directly from this git repo:
```bash
pipx install git+https://github.com/ergosteur/insta_selenium.git
```


### via pip

1. Create and activate a virtual environment (recommended):
   ```bash
   python -m venv .venv
   # On Windows:
   .venv\Scripts\activate
   # On macOS/Linux:
   source .venv/bin/activate
   ```
2. Install using pip directly from this git repo:
   ```
   pip install git+https://github.com/ergosteur/insta_selenium.git
   ```

### from source

1. Clone this repository:
   ```bash
   git clone https://github.com/ergosteur/insta_selenium.git
   cd insta_selenium
   ```
2. Create and activate a virtual environment (recommended):
   ```bash
   python -m venv .venv
   # On Windows:
   .venv\Scripts\activate
   # On macOS/Linux:
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

After installation, you can run the tool from the command line:

```bash
insta_selenium --username <instagram_username> [options]
```

Or, if running from source:

```bash
python scrape_instagram.py --username <instagram_username> [options]
```

### Common options

- `--post-id <shortcode>`: Download a specific post or reel by shortcode.
- `--max-scraped-posts <N>`: Limit the number of posts scraped from a profile.
- `--max-grabbed-posts <N>`: Limit the number of posts to download after scraping.
- `--headless`: Run the browser in headless mode (no GUI).
- `--resume-log <file>`: Specify a log file for storing scanned post URLs.
- `--resume-file <file>`: File to track last successfully downloaded post URL.
- `--no-resume`: Ignore resume file and start fresh.
- `--processed-urls-file <file>`: File to track all unique URLs already processed.
- `--download-path <dir>`: Directory to save downloaded media (default: ./downloads).
- `--firefox-profile-dir <dir>`: Path to Firefox profile directory (default: ./firefox_profile).
- `--overwrite`: Overwrite existing downloaded files.
- `--login`: Open browser for Instagram login and save session to Firefox profile.
- `--no-retry-errors`: Do not retry failed posts from error logs.
- `--retry-errors-only`: Only retry failed posts from error logs and exit.

For a full list of options, run:

```bash
insta_selenium --help
```

## Notes

- Use responsibly and in accordance with Instagram's terms of service.
- Excessive automation may result in account restrictions or bans.
- Use with a secondary account is recommended.

## AI-Assisted Development

This project was developed with the assistance of AI tools.

## License

GPL-3.0 License
