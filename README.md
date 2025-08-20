# insta_selenium

A Python tool for scraping and downloading Instagram post and reel media using Selenium WebDriver.

## Features

- Scrape post and reel URLs from public Instagram profiles
- Download images and videos from posts and reels
- Save post metadata (caption, timestamp, etc.)
- Resume interrupted downloads and avoid duplicates
- Supports headless mode for automated/scripted use

## Prerequisites

- [**Python 3.8+**](https://www.python.org/downloads/)
- [**Mozilla Firefox browser**](https://www.mozilla.org/firefox/)
- **GeckoDriver** (Firefox WebDriver)  
  [Download geckodriver](https://github.com/mozilla/geckodriver/releases) and ensure it's in your PATH.  
  *On Windows 11, geckodriver is available via WinGet:*  
  ```bash
  winget install --id Mozilla.GeckoDriver
  ```
- For installation, one of:
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

After installation (or building the Docker image), you can run the tool from the command line:

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
- `--cleanup-and-retry`: Delete post directories with no images or videos, remove their URLs from processed log, and retry them.

For a full list of options, run:

```bash
insta_selenium --help
```
## Docker

You can run `insta_selenium` in a containerized environment with full support for both **headless scraping** and **interactive login via a web browser (VNC/noVNC)**.

1. Pull the Docker image

```bash
docker pull ergosteur/insta_selenium:latest
```

2. Data Persistence

Create a local `data` directory to `/data` that will be mounted as a volume in the container to persist your Firefox profile and downloads:

```bash
mkdir -p $PWD/data/firefox_profile $PWD/data/downloads
```

3. Interactive Login via Web UI (VNC/noVNC)

To perform an interactive login (for the first time or when cookies expire), use the special login entrypoint.  
This will start a virtual desktop and expose a web-based VNC client on port 6080.

```bash
docker run --rm -it -p 6080:6080 -v "$PWD/data:/data" ergosteur/insta_selenium insta_selenium_login
```

- Then open [http://localhost:6080/vnc.html](http://localhost:6080/vnc.html) in your browser.
- Log in to Instagram in the Firefox window.
- After login, close the browser window and stop the container.
- Your session/cookies will be saved in `./data/firefox_profile` for future headless runs.

**Note:**  
- For convenience, the demo VNC setup does not use a password. For production, consider securing your VNC/noVNC setup.
- After logging in once, you can use the headless mode for all further scraping.

4. Headless Scraping

Once logged in, you can run the script with:

```bash
docker run --rm -it -v "$PWD/data:/data" ergosteur/insta_selenium insta_selenium --headless --firefox-profile-dir /data/firefox_profile --download-path /data/downloads --username <username>
```

- Downloads and Firefox profile will be stored in your local `./data` directory.
- Replace <username> with target username


## Notes

- Use responsibly and in accordance with Instagram's terms of service.
- Excessive automation may result in account restrictions or bans.
- Use with a secondary account is recommended.

## AI-Assisted Development

This project was developed with the assistance of AI tools.

## License

GPL-3.0 License
