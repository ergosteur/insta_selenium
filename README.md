# insta_selenium

A Python tool for scraping and downloading Instagram post and reel media using Selenium WebDriver.

## Features

- Scrape post and reel URLs from public Instagram profiles
- Download images and videos from posts and reels
- Save post metadata (caption, timestamp, etc.)
- Resume interrupted downloads and avoid duplicates
- Supports headless mode for automated/scripted use

## Requirements

- Python 3.8+
- [Selenium](https://pypi.org/project/selenium/)
- Firefox WebDriver (geckodriver)
- Mozilla Firefox browser

## Installation

### From Source

1. Clone this repository:
   ```bash
   git clone https://github.com/ergosteur/insta_selenium.git
   cd insta_selenium
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Download [geckodriver](https://github.com/mozilla/geckodriver/releases) and ensure it's in your PATH.

### Via pip

You can also install directly from the repository:
```bash
pip install git+https://github.com/ergosteur/insta_selenium.git
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
- `--no-resume`: Ignore resume file and start fresh.

For a full list of options, run:

```bash
insta_selenium --help
```

## Notes

- Use responsibly and in accordance with Instagram's terms of service.
- Excessive automation may result in account restrictions or bans.

## AI-Assisted Development

This project was developed with the assistance of AI tools.

## License

GPL-3.0 License
