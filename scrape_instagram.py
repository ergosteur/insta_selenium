# =============================================================================
# scrape_instagram.py
# Version: 0.1.1
# Description: Scrape and download Instagram post and reel media using Selenium.
# Author: ergosteur
# License: GPL-3.0
# =============================================================================

import os
import sys
import re
import time
import argparse
import urllib.parse
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException
from tqdm import tqdm
import json
import requests
import glob

# === Command Line Arguments ===
parser = argparse.ArgumentParser(description="Scrape Instagram post and reel media URLs")
parser.add_argument("--post-id", help="Instagram post shortcode (e.g., C0EVTGHSQUF)")
parser.add_argument("--username", help="Target username (required unless using --login)")
parser.add_argument("--max-scraped-posts", type=int, help="Max posts to scrape from profile")
parser.add_argument("--max-grabbed-posts", type=int, help="Max posts to download (after scraping)")
parser.add_argument("--resume-log", help="Log file for storing scanned post URLs (now stores scraped order)")
parser.add_argument("--resume-file", help="File to track last successfully downloaded post URL")
parser.add_argument("--no-resume", dest="no_resume", action="store_true", help="Ignore resume file and start fresh")
parser.add_argument("--processed-urls-file", help="File to track all unique URLs already processed")
parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
parser.add_argument("--login", action="store_true", help="Open browser for Instagram login and save session to Firefox profile")
parser.add_argument("--download-path", help="Directory to save downloaded media (default: ./downloads)")
parser.add_argument("--firefox-profile-dir", help="Path to Firefox profile directory (default: ./firefox_profile)")
parser.add_argument("--overwrite", action="store_true", help="Overwrite existing downloaded files")
parser.add_argument("--no-retry-errors", action="store_true", help="Do not retry failed posts from error logs")
parser.add_argument("--retry-errors-only", action="store_true", help="Only retry failed posts from error logs and exit")
parser.add_argument("--cleanup-and-retry", action="store_true", help="Delete post directories with no images or videos, remove their URLs from processed log, and retry them.")
args = parser.parse_args()

# === Constants ===
BASE_URL = "https://www.instagram.com"
PROFILE_URL = f"{BASE_URL}/{args.username}/"
POST_URL = f"{BASE_URL}/p/{args.post_id}/" if args.post_id else None
SESSION_NAME = args.post_id if args.post_id else args.username
DOWNLOAD_ROOT = os.path.abspath(args.download_path) if args.download_path else os.path.abspath("downloads")
PROFILE_DIR = os.path.abspath(args.firefox_profile_dir) if args.firefox_profile_dir else os.path.abspath("./firefox_profile")
MAX_GRABBED_POSTS = args.max_grabbed_posts if args.max_grabbed_posts else None
os.makedirs(DOWNLOAD_ROOT, exist_ok=True)
timestamp_now = datetime.now().strftime("%Y%m%d_%H%M%S")

# === Argument Validations ===
# Require --username unless --login is used
if not args.login and not args.username:
    parser.error("--username is required unless using --login")

# === Mutually exclusive check for --login and --headless ===
if args.login and args.headless:
    print("[!] Error: --login and --headless cannot be used together.")
    print("    --login requires a visible browser window for manual login.")
    sys.exit(1)

# Warn if PROFILE_DIR does not exist and not in login mode
if not os.path.exists(PROFILE_DIR):
    if args.login:
        print(f"[!] Firefox profile directory '{PROFILE_DIR}' does not exist.")
        print(f"[!] --login specified, creating new profile.")
        os.makedirs(PROFILE_DIR, exist_ok=True)
    else:
        print(f"[!] Firefox profile directory '{PROFILE_DIR}' does not exist.")
        print("    You must login first to create a profile with Instagram cookies.")
        print("    Run this script with the --login flag to do so.")
        sys.exit(1)

# Paths for persistence files if not in login mode
if not args.login:
    RESUME_FILE = args.resume_file or os.path.join(DOWNLOAD_ROOT, SESSION_NAME, "last-post-url.txt")
    RESUME_LOG = args.resume_log or os.path.join(DOWNLOAD_ROOT, SESSION_NAME, f"{SESSION_NAME}-posts_{timestamp_now}.log")
    ERROR_LOG = RESUME_LOG.replace("posts_", "errors_")
    PROCESSED_URLS_FILE = os.path.join(DOWNLOAD_ROOT, SESSION_NAME, "processed-urls.json")
    if args.processed_urls_file:
        PROCESSED_URLS_FILE = os.path.abspath(args.processed_urls_file)
    session_dir = os.path.join(DOWNLOAD_ROOT, SESSION_NAME)
    os.makedirs(session_dir, exist_ok=True)

# === Selenium Setup ===
options = Options()
if args.headless:
    options.add_argument("--headless")
options.add_argument("--width=1920")
options.add_argument("--height=1080")
if args.login:
    # Use -profile argument to ensure persistence for manual login
    options.add_argument("-profile")
    options.add_argument(PROFILE_DIR)
    # Do NOT use FirefoxProfile here
else:
    # Use FirefoxProfile for normal runs (optional, or just omit for default)
    profile = FirefoxProfile(PROFILE_DIR)
    options.profile = profile
service = Service()
driver = webdriver.Firefox(service=service, options=options)
driver.implicitly_wait(10)
# Handle --login mode using Firefox profile and selenium
if args.login:
    print("[*] Opening Instagram login page in Firefox...")
    driver.get("https://www.instagram.com/")
    print("[*] Please log in to Instagram in the opened browser window.")
    print("[*] Do NOT close the browser after logging in.")
    input("[*] After you have logged in and see your feed, press Enter here to finish and save the session...")
    print("[*] Login session should now be saved in your Firefox profile directory.")
    driver.quit()
    sys.exit(0)

def sanitize_filename(url):
    name = urllib.parse.unquote(url.split("?")[0].split("/")[-1])
    return re.sub(r'[^\w.-]', '_', name)

def load_processed_urls(file_path):
    """Loads a set of processed URLs from a JSON file."""
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as f:
                return set(json.load(f))
        except json.JSONDecodeError:
            print(f"[*] Warning: Could not decode {file_path}. Starting with empty processed URLs.")
            return set()
    return set()

def save_processed_urls(file_path, processed_set):
    """Saves a set of processed URLs to a JSON file."""
    try:
        with open(file_path, 'w') as f:
            json.dump(list(processed_set), f) # Convert set to list for JSON serialization
    except Exception as e:
        print(f"[!] Error saving processed URLs to {file_path}: {e}")

def normalize_post_url(href, base_url, username):
    """
    Normalize Instagram post/reel URLs to absolute canonical form.
    Removes username from path if present, strips query/fragments,
    and ensures the URL starts with base_url + '/p/' or '/reel/'.
    Returns None if the URL is not a valid post/reel link.
    """
    if not href:
        return None
    parsed = urllib.parse.urlparse(href)
    if not parsed.netloc:
        # Relative URL, join with BASE_URL
        normalized_href = urllib.parse.urljoin(base_url, href)
    else:
        normalized_href = href
    # Remove query params/fragments
    normalized_href = normalized_href.split("?")[0].split("#")[0]
    # Remove /username/ from the URL if present (for both /p/ and /reel/)
    if normalized_href.startswith(base_url + f"/{username}/p/"):
        normalized_href = base_url + normalized_href[len(base_url + f"/{username}"):]
    elif normalized_href.startswith(base_url + f"/{username}/reel/"):
        normalized_href = base_url + normalized_href[len(base_url + f"/{username}"):]
    # Final check: must start with BASE_URL + '/p/' or '/reel/'
    if not (normalized_href.startswith(base_url + "/p/") or normalized_href.startswith(base_url + "/reel/")):
        return None
    return normalized_href

# === Profile scraping links collection ===
# This function collects all post and reel links from the profile page.
def collect_post_links():
    print(f"[+] Scanning profile: {PROFILE_URL}")
    driver.get(PROFILE_URL)
    time.sleep(3)

    # CHANGE: Initialize post_links as a list to preserve discovery order
    post_links = []
    # Use a temporary set for deduplication *during collection* to avoid redundant DOM checks
    # But the main 'post_links' will retain the order of discovery.
    temp_seen_urls_during_collection = set()

    last_height = driver.execute_script("return document.body.scrollHeight")
    # FIX: Initialize tqdm bar *before* the loop, outside of any conditional check.
    # This ensures it's created once and properly managed.
    tqdm_bar_collection = tqdm(total=None, unit="links", desc="Collecting Links")

    try: # Added try-finally to ensure tqdm bar closure
        while True:
            anchors = driver.find_elements(By.XPATH, "//a[contains(@href, '/p/') or contains(@href, '/reel/')]")
            for a in anchors: # Iterate over anchors without wrapping a tqdm() directly around it
                href = a.get_attribute("href")
                # Use the normalization function
                full_url = normalize_post_url(href, BASE_URL, args.username)
                if full_url is None:
                    continue
                # Only add to our ordered list if it hasn't been seen during this collection run
                if full_url not in temp_seen_urls_during_collection:
                    post_links.append(full_url)
                    temp_seen_urls_during_collection.add(full_url)
                    tqdm_bar_collection.update(1) # Manually update progress for each new link
                    # tqdm.write(f"[{'REEL' if '/reel/' in full_url else 'POST'}]  {full_url}") # Optional: enable for verbose logging
                    if args.max_scraped_posts and len(post_links) >= args.max_scraped_posts:
                        break # Break from inner loop

            if args.max_scraped_posts and len(post_links) >= args.max_scraped_posts:
                break # Break from outer loop
            # Scroll down to load more content
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            waited_seconds = 0
            max_total_wait = 10 # seconds
            height_increased = False
            while waited_seconds < max_total_wait:
                time.sleep(1)
                waited_seconds += 1
                current_height = driver.execute_script("return document.body.scrollHeight")
                if current_height > last_height:
                    # Height has increased, new content loaded
                    height_increased = True
                    tqdm.write(f"[i] Scrolled and detected new content. New height: {current_height}")
                    last_height = current_height # Update last_height for the next iteration
                    break # Exit the inner wait loop, content loaded, continue outer loop

                tqdm.write(f"[i] No new content detected yet. Waiting... ({waited_seconds}/{max_total_wait}s)")
            if not height_increased:
                # If after max_total_wait, height still hasn't increased, assume end of content
                tqdm.write("[!] Reached end of scrollable content. Exiting scroll loop.")
                break # Exit the outer while True loop
    finally:
        # FIX: Remove the 'if tqdm_bar_collection:' condition.
        # Since it's initialized before the try block, it will always be a tqdm object here.
        tqdm_bar_collection.close()

    # CHANGE: Removed post_links = sorted(post_links)
    # The list 'post_links' now contains URLs in their scraped/discovery order.
    
    # Save the full list of collected links in their scraped order
    with open(RESUME_LOG, "w") as f:
        for url in post_links:
            f.write(url + "\n")

    print(f"[✓] Collected {len(post_links)} post+reel links → {RESUME_LOG}")
    return post_links

# === Media download functions ===
def download_video(post_url, post_dir, shortcode, label="video"):
    """Download video(s) from an Instagram post using yt-dlp, preserving original filename if possible."""
    from yt_dlp import YoutubeDL
    # Use yt-dlp's %(title)s or %(id)s as fallback, and prefix with label
    outtmpl = os.path.join(post_dir, f"{label}_%(id)s.%(ext)s")
    if not args.overwrite:
        existing = [f for f in os.listdir(post_dir) if f.startswith(label) and f.endswith(('.mp4', '.webm', '.mkv'))]
        if existing:
            tqdm.write(f"[⏩] Skipping video download for {post_url} (video file already exists)")
            return
    try:
        user_agent = driver.execute_script("return navigator.userAgent;")
        tqdm.write(f"[▶] Downloading video(s) via yt-dlp from post: {shortcode}")
        ytdl_opts = {
            'outtmpl': outtmpl,
            'quiet': True,
            'verbose': False,
            'no_warnings': True,
            'progress': False,
            # Use cookies from the Firefox profile directory
            'cookiesfrombrowser': ('firefox', PROFILE_DIR),
            'user_agent': user_agent,
            'noplaylist': False,  # <-- Ensure yt-dlp treats the post as a playlist
            'ignoreerrors': True,  # <-- Ignore errors for individual videos
            'format': 'bestvideo+bestaudio/best',  # Download best quality video
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',  # Convert to mp4 if not already
            }],
        }
        with YoutubeDL(ytdl_opts) as ytdl:
            ytdl.download([post_url])
    except Exception as e:
        tqdm.write(f"[!] yt-dlp error: {e}")
        with open(ERROR_LOG, "a") as elog:
            elog.write(f"{post_url} — yt-dlp error: {e}\n")

def download_images(media_items, target_dir):
    for url, label in tqdm(media_items, desc=f"Downloading media to {os.path.basename(target_dir)}", leave=False):
        if url.startswith("blob:"):
            tqdm.write(f"[⏩] Skipping blob URL: {url}")
            continue
        # Extract the original filename from the URL path
        parsed_url = urllib.parse.urlparse(url)
        original_filename = os.path.basename(parsed_url.path)
        # Fallback if original filename is empty
        if not original_filename:
            ext = os.path.splitext(parsed_url.path)[-1]
            original_filename = f"media{ext if ext else '.jpg'}"
        # Prefix with our sequence label
        filename = f"{label}_{original_filename}"
        filepath = os.path.join(target_dir, sanitize_filename(filename))
        if not os.path.exists(filepath) or args.overwrite:
            tqdm.write(f"[↓] Downloading {url} → {filepath}")
            try:
                with requests.get(url, stream=True, timeout=20) as r:
                    r.raise_for_status()
                    with open(filepath, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            f.write(chunk)
            except Exception as e:
                tqdm.write(f"[!] Failed to download {url}: {e}")
        else:
            tqdm.write(f"[⏩] Skipping {url} (already exists)")

# === Post scraping and downloading logic ===
def extract_media_urls(post_url):
    print(f"[→] {post_url}")
    driver.get(post_url)
    media_items = []
    seen_urls = set()
    actions = ActionChains(driver)

    shortcode = post_url.rstrip('/').split('/')[-1]

    tqdm.write(f"[i] Extracting media from post: {shortcode}")
    try:
        # Wait for a large <img> or <video> tag to appear
        tqdm.write(f"[i] Waiting for main media element (<img> or <video>)...")
        WebDriverWait(driver, 20).until(
            lambda d: any(
                (img.size['width'] > 300 and img.size['height'] > 300)
                for img in d.find_elements(By.TAG_NAME, "img")
            ) or any(
                (vid.size['width'] > 300 and vid.size['height'] > 300)
                for vid in d.find_elements(By.TAG_NAME, "video")
            )
        )
    except Exception as e:
        tqdm.write(f"[!] Warning: Could not find main media element on {post_url}. Error: {e}")

    # Try to find the time element, but fallback if not found
    tqdm.write(f"[i] Looking for <time> tag...")
    try:
        time_elem = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.TAG_NAME, "time"))
        )
        timestamp_raw = time_elem.get_attribute("datetime")
        timestamp_prefix = datetime.fromisoformat(timestamp_raw.replace("Z", "+00:00")).strftime("%Y%m%d")
    except Exception as e:
        tqdm.write(f"[!] Warning: Could not find time element on {post_url} after wait. Using current time. Error: {e}")
        timestamp_raw = datetime.now().isoformat()
        timestamp_prefix = datetime.now().strftime("%Y%m%d")
    tqdm.write(f"[i] Timestamp found: {timestamp_raw}")
    post_dir_name = f"{timestamp_prefix}_{shortcode}"
    post_dir = os.path.join(DOWNLOAD_ROOT, SESSION_NAME, post_dir_name)
    os.makedirs(post_dir, exist_ok=True)

    caption = ""
    try:
        # Try to extract the caption from the h1 tag with known class pattern
        caption_elem = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, '//article//h1[contains(@class, "_ap3a")]'))
        )
        caption = caption_elem.text.strip()
    except TimeoutException:
        caption = ""
    except Exception as e:
        print(f"[*] An unexpected error occurred while getting caption: {e}")
        caption = ""
        
    metadata = {
        "url": post_url,
        "shortcode": shortcode,
        "caption": caption,
        "timestamp": timestamp_raw
    }
    with open(os.path.join(post_dir, "metadata.json"), "w") as meta_file:
        json.dump(metadata, meta_file, indent=2)

    index = 1
    video_detected = False

    # Only collect images for manual download
    def collect_images():
        nonlocal index, video_detected
        img_tags = driver.find_elements(By.TAG_NAME, "img")
        for img in img_tags:
            url = img.get_attribute("src")
            if not url or url in seen_urls or url.startswith("blob:"):
                continue
            box = driver.execute_script("""
                const rect = arguments[0].getBoundingClientRect();
                return {width: rect.width, height: rect.height, top: rect.top, left: rect.left};
            """, img)
            if box["width"] < 320 or box["height"] < 300:
                continue
            if box["top"] < 0 or box["left"] < 0:
                continue
            seen_urls.add(url)
            label = f"image_{index:02d}"
            media_items.append((url, label))
            index += 1

        # Detect if any <video> is present in the post (for yt-dlp)
        videos = driver.find_elements(By.TAG_NAME, "video")
        if videos:
            video_detected = True

    # Carousel navigation loop (as before)
    next_button_xpath = '//button[contains(@class, "_afxw") or @aria-label="Next"]'
    slide_count = 1
    while True:
        tqdm.write(f"[→] Processing slide {slide_count}")
        collect_images()
        try:
            next_button = WebDriverWait(driver, 2).until(
                EC.element_to_be_clickable((By.XPATH, next_button_xpath))
            )
            next_button.click()
            slide_count += 1
            time.sleep(1.5)
        except:
            tqdm.write("[✓] Reached end of carousel or no next button")
            break

    with open(os.path.join(post_dir, "media_urls.txt"), "w") as f:
        for url, label in media_items:
            f.write(f"{label}: {url}\n")

    call_ytdlp = video_detected or not media_items
    return media_items, post_dir, call_ytdlp

# === Main Execution ===
def main():
    try:
        if getattr(args, "cleanup_and_retry", False):
            cleanup_and_retry_empty_dirs()
            return

        if args.retry_errors_only:
            # Only retry failed posts from error logs, then exit
            error_log_pattern = os.path.join(DOWNLOAD_ROOT, SESSION_NAME, "*-errors_*.log")
            error_logs = glob.glob(error_log_pattern)
            error_logs = list(set(error_logs + [ERROR_LOG]))
            retry_failed_posts(error_logs)
            return  # Exit after retrying errors

        if POST_URL:
            # If a specific post ID is provided, just scrape that one
            items, dir_path, call_ytdlp = extract_media_urls(POST_URL)
            download_images(items, dir_path)
            if call_ytdlp:
                shortcode = POST_URL.rstrip('/').split('/')[-1]
                download_video(POST_URL, dir_path, shortcode)
            processed_urls = load_processed_urls(PROCESSED_URLS_FILE)
            processed_urls.add(POST_URL)
            save_processed_urls(PROCESSED_URLS_FILE, processed_urls)
        else:
            # Init total_urls_grabbed counter
            total_urls_grabbed = 0
            # Scrape all post links from the profile (most recent to oldest)
            post_links = collect_post_links()
            
            # Load previously processed URLs for robust deduplication
            processed_urls = load_processed_urls(PROCESSED_URLS_FILE)

            # Reverse the list so it goes from oldest to most recent
            # This modification is applied before calculating the resume index
            # to ensure the index is correct for the desired processing order.
            post_links.reverse() # In-place reverse of the list

            resume_index = 0
            last_url_from_file = None

            # Try to find the last processed URL from the resume file
            if os.path.exists(RESUME_FILE) and not args.no_resume:
                with open(RESUME_FILE) as f:
                    last_url_from_file = f.read().strip()
                    # Normalize the last_url_from_file for robust matching
                    last_url_from_file = normalize_post_url(last_url_from_file, BASE_URL, args.username)
                    if last_url_from_file:
                        try:
                            # Find the index of the last processed URL in our *now reversed* list
                            # This index will correctly point to the item just before where we want to resume
                            resume_index = post_links.index(last_url_from_file) + 1
                            tqdm.write(f"[⏩] Resuming from after: {last_url_from_file} (index {resume_index} in reversed list)")
                        except ValueError:
                            tqdm.write(f"[!] Warning: Last processed URL '{last_url_from_file}' not found in current list of posts. Starting from the oldest available.")
                            resume_index = 0
                    else:
                        tqdm.write("[*] No last URL found in resume file. Starting from the oldest available.")
            else:
                tqdm.write("[*] Resume file not found. Starting from the oldest available.")


            # Iterate through the collected links starting from the resume point
            # The list is already reversed, so this will process from oldest to newest
            for link_to_process in tqdm(post_links[resume_index:], desc="Processing Posts (Oldest to Newest)"):
                if link_to_process in processed_urls:
                    tqdm.write(f"[⏩] Skipping already processed: {link_to_process}")
                    continue # Skip this URL if it's already in our processed set
                total_urls_grabbed += 1
                
                # Stop at --max-grabbed-posts if specified
                if MAX_GRABBED_POSTS:
                    if total_urls_grabbed > MAX_GRABBED_POSTS :
                        tqdm.write(f"[!] Reached maximum number of grabbed posts ({MAX_GRABBED_POSTS}), exiting.")
                        break

                try:
                    items, dir_path, call_ytdlp = extract_media_urls(link_to_process)
                    download_images(items, dir_path)
                    if call_ytdlp:
                        shortcode = link_to_process.rstrip('/').split('/')[-1]
                        download_video(link_to_process, dir_path, shortcode)
                    processed_urls.add(link_to_process)
                    save_processed_urls(PROCESSED_URLS_FILE, processed_urls)
                except Exception as e:
                    tqdm.write(f"[!!!] Error processing {link_to_process}: {e}")
                    with open(ERROR_LOG, "a") as elog:
                        elog.write(f"{link_to_process} — main loop error: {e}\n")
        if not args.no_retry_errors:
            # Find all error logs for this session/user
            error_log_pattern = os.path.join(DOWNLOAD_ROOT, SESSION_NAME, "*-errors_*.log")
            error_logs = glob.glob(error_log_pattern)
            # Always include the current ERROR_LOG in case it's not matched (avoid duplicates with set)
            error_logs = list(set(error_logs + [ERROR_LOG]))
            retry_failed_posts(error_logs)
    except KeyboardInterrupt:
        print("[!] Interrupted by user - please wait for clean exit...")
    finally:
        driver.quit()
        print("[✓] Browser closed.")

def extract_urls_from_error_log(error_log_path):
    """Extracts Instagram post URLs from an error log file."""
    urls = set()
    if not os.path.exists(error_log_path):
        return urls
    with open(error_log_path, "r") as f:
        for line in f:
            # Look for a URL at the start of the line
            match = re.match(r"(https://www\.instagram\.com/(?:p|reel)/[A-Za-z0-9_\-]+)/?", line)
            if match:
                urls.add(match.group(1))
    return urls

def retry_failed_posts(error_log_paths):
    """Retry posts that failed in previous runs, based only on error logs.
    If a post is successfully processed (all media skipped or downloaded), it is not included in the new error log.
    """
    all_failed_urls = set()
    for log_path in error_log_paths:
        all_failed_urls.update(extract_urls_from_error_log(log_path))
    if not all_failed_urls:
        tqdm.write("[✓] No failed posts to retry.")
        return

    tqdm.write(f"[!] Retrying {len(all_failed_urls)} failed posts from error logs...")
    still_failed_urls = set()
    for url in tqdm(all_failed_urls, desc="Retrying Failed Posts"):
        try:
            items, dir_path, call_ytdlp = extract_media_urls(url)
            # Track if any image/video actually needed to be downloaded
            all_exist = True
            for media_url, label in items:
                parsed_url = urllib.parse.urlparse(media_url)
                original_filename = os.path.basename(parsed_url.path)
                if not original_filename:
                    ext = os.path.splitext(parsed_url.path)[-1]
                    original_filename = f"media{ext if ext else '.jpg'}"
                filename = f"{label}_{original_filename}"
                filepath = os.path.join(dir_path, sanitize_filename(filename))
                if not os.path.exists(filepath):
                    all_exist = False
                    break
            # For video, check if any video file exists
            video_exists = False
            if call_ytdlp:
                video_files = [f for f in os.listdir(dir_path) if f.endswith(('.mp4', '.webm', '.mkv'))]
                if video_files:
                    video_exists = True
            # If all images and (if needed) video exist, consider this post as successfully processed
            if (items and all_exist) and (not call_ytdlp or video_exists):
                tqdm.write(f"[✓] All media already present for {url}, removing from error log.")
                continue
            # Otherwise, try to download missing media
            try:
                download_images(items, dir_path)
                if call_ytdlp:
                    shortcode = url.rstrip('/').split('/')[-1]
                    download_video(url, dir_path, shortcode)
            except Exception as e:
                tqdm.write(f"[!!!] Error retrying {url}: {e}")
                still_failed_urls.add(url)
                continue
            # After download attempt, check again if all media exist
            all_exist = True
            for media_url, label in items:
                parsed_url = urllib.parse.urlparse(media_url)
                original_filename = os.path.basename(parsed_url.path)
                if not original_filename:
                    ext = os.path.splitext(parsed_url.path)[-1]
                    original_filename = f"media{ext if ext else '.jpg'}"
                filename = f"{label}_{original_filename}"
                filepath = os.path.join(dir_path, sanitize_filename(filename))
                if not os.path.exists(filepath):
                    all_exist = False
                    break
            video_exists = False
            if call_ytdlp:
                video_files = [f for f in os.listdir(dir_path) if f.endswith(('.mp4', '.webm', '.mkv'))]
                if video_files:
                    video_exists = True
            if (items and all_exist) and (not call_ytdlp or video_exists):
                tqdm.write(f"[✓] Successfully retried {url}")
            else:
                still_failed_urls.add(url)
        except Exception as e:
            tqdm.write(f"[!!!] Error retrying {url}: {e}")
            still_failed_urls.add(url)

    # Remove all old error logs
    for log_path in error_log_paths:
        try:
            os.remove(log_path)
        except Exception:
            pass

    # Write new error log with only remaining failed URLs
    if still_failed_urls:
        new_error_log = os.path.join(DOWNLOAD_ROOT, SESSION_NAME, f"{SESSION_NAME}-errors_remaining_{timestamp_now}.log")
        
        with open(new_error_log, "w") as elog:
            for url in still_failed_urls:
                elog.write(f"{url} — still failed after retry\n")
        tqdm.write(f"[!] Wrote new error log: {new_error_log}")
    else:
        tqdm.write("[✓] All previously errored posts processed successfully!")

def cleanup_and_retry_empty_dirs():
    """
    Delete post directories with no images or videos, remove their URLs from processed log, and retry them.
    """
    session_dir = os.path.join(DOWNLOAD_ROOT, SESSION_NAME)
    if not os.path.exists(session_dir):
        tqdm.write(f"[!] Session directory not found: {session_dir}")
        return
    
    # Load processed URLs
    processed_urls = load_processed_urls(PROCESSED_URLS_FILE)
    # Map shortcode to URL for quick lookup
    shortcode_to_url = {url.rstrip('/').split('/')[-1]: url for url in processed_urls}
    
    empty_shortcodes = []
    for entry in os.listdir(session_dir):
        entry_path = os.path.join(session_dir, entry)
        if not os.path.isdir(entry_path):
            continue
        # Only consider directories with a valid shortcode (date_shortcode)
        if '_' not in entry:
            continue
        _, shortcode = entry.split('_', 1)
        # Check for media files
        has_media = False
        for ext in ('.jpg', '.jpeg', '.png', '.mp4', '.webm', '.mkv'):
            if any(f.endswith(ext) for f in os.listdir(entry_path)):
                has_media = True
                break
        if not has_media:
            tqdm.write(f"[!] Deleting empty post dir: {entry_path}")
            # Remove directory and contents
            try:
                for root, dirs, files in os.walk(entry_path, topdown=False):
                    for name in files:
                        os.remove(os.path.join(root, name))
                    for name in dirs:
                        os.rmdir(os.path.join(root, name))
                os.rmdir(entry_path)
            except Exception as e:
                tqdm.write(f"[!] Error deleting {entry_path}: {e}")
            empty_shortcodes.append(shortcode)
    
    # Remove URLs from processed_urls
    removed_urls = set()
    for shortcode in empty_shortcodes:
        url = shortcode_to_url.get(shortcode)
        if url and url in processed_urls:
            processed_urls.remove(url)
            removed_urls.add(url)
    if removed_urls:
        tqdm.write(f"[!] Removed {len(removed_urls)} URLs from processed log.")
        save_processed_urls(PROCESSED_URLS_FILE, processed_urls)
    else:
        tqdm.write("[✓] No processed URLs needed removal.")
    
    # Retry the removed URLs
    if removed_urls:
        tqdm.write(f"[!] Retrying {len(removed_urls)} cleaned-up posts...")
        for url in tqdm(removed_urls, desc="Retrying Cleaned Posts"):
            try:
                items, dir_path, call_ytdlp = extract_media_urls(url)
                download_images(items, dir_path)
                if call_ytdlp:
                    shortcode = url.rstrip('/').split('/')[-1]
                    download_video(url, dir_path, shortcode)
                processed_urls.add(url)
                save_processed_urls(PROCESSED_URLS_FILE, processed_urls)
            except Exception as e:
                tqdm.write(f"[!!!] Error retrying {url}: {e}")
    else:
        tqdm.write("[✓] No posts to retry after cleanup.")

if __name__ == "__main__":
    main()

