import os
import sys
import re
import time
import argparse
import urllib.parse
from datetime import datetime
from seleniumwire import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException
from yt_dlp import YoutubeDL
from tqdm import tqdm
import json
import requests

# === Command Line Arguments ===
parser = argparse.ArgumentParser(description="Scrape Instagram post and reel media URLs")
parser.add_argument("--post-id", help="Instagram post shortcode (e.g., C0EVTGHSQUF)")
parser.add_argument("--username", default="heed_heejin", help="Target username (default: heed_heejin)")
parser.add_argument("--max-scraped-posts", type=int, help="Max posts to scrape from profile")
parser.add_argument("--max-grabbed-posts", type=int, help="Max posts to download (after scraping)")
parser.add_argument("--resume-log", help="Log file for storing scanned post URLs (now stores scraped order)")
parser.add_argument("--resume-file", help="File to track last successfully downloaded post URL")
parser.add_argument("--no-resume", dest="no_resume", action="store_true", help="Ignore resume file and start fresh")
# Added an argument for the file that stores ALL processed URLs for robust deduplication
parser.add_argument("--processed-urls-file", help="File to track all unique URLs already processed")
parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
args = parser.parse_args()

# === Constants ===
BASE_URL = "https://www.instagram.com"
PROFILE_URL = f"{BASE_URL}/{args.username}/"
POST_URL = f"{BASE_URL}/p/{args.post_id}/" if args.post_id else None
SESSION_NAME = args.post_id if args.post_id else args.username
DOWNLOAD_ROOT = os.path.abspath("downloads")
PROFILE_DIR = os.path.abspath("./firefox_profile")
MAX_GRABBED_POSTS = args.max_grabbed_posts if args.max_grabbed_posts else None
os.makedirs(DOWNLOAD_ROOT, exist_ok=True)
os.makedirs(PROFILE_DIR, exist_ok=True)
timestamp_now = datetime.now().strftime("%Y%m%d_%H%M%S")

# Paths for persistence files
RESUME_FILE = args.resume_file or os.path.join(DOWNLOAD_ROOT, SESSION_NAME, "last-post-url.txt")
RESUME_LOG = args.resume_log or os.path.join(DOWNLOAD_ROOT, SESSION_NAME, f"{SESSION_NAME}-posts_{timestamp_now}.log")
ERROR_LOG = RESUME_LOG.replace("posts_", "errors_")
# New file to store the set of all unique processed URLs
PROCESSED_URLS_FILE = os.path.join(DOWNLOAD_ROOT, SESSION_NAME, "processed-urls.json")
# If --processed-urls-file is explicitly provided, use it
if args.processed_urls_file:
    PROCESSED_URLS_FILE = os.path.abspath(args.processed_urls_file)


# Ensure session directory exists for persistence files
session_dir = os.path.join(DOWNLOAD_ROOT, SESSION_NAME)
os.makedirs(session_dir, exist_ok=True)

# === Selenium Setup ===
options = Options()
if args.headless:
    options.add_argument("--headless")
options.add_argument("--width=1920")
options.add_argument("--height=1080")
profile = FirefoxProfile(PROFILE_DIR)
options.profile = profile
service = Service()
driver = webdriver.Firefox(service=service, options=options)
driver.implicitly_wait(10)


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
                if href and ("/p/" in href or "/reel/" in href):
                    full_url = urllib.parse.urljoin(BASE_URL, href.split("?")[0])
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

            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

            waited_seconds = 0
            max_total_wait = 10 # seconds
            height_increased = False

            while waited_seconds < max_total_wait:
                time.sleep(1) # Wait for 1 second before checking
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

def update_line(msg):
    sys.stdout.write("\r" + msg)
    sys.stdout.flush()

def extract_media_urls(post_url):
    print(f"[→] {post_url}")
    driver.get(post_url)
    media_items = []
    seen_urls = set()
    actions = ActionChains(driver)

    shortcode = post_url.rstrip('/').split('/')[-1]

    # Use an explicit wait to ensure the main content (e.g., the <article> tag)
    # or the <time> tag is present before proceeding.
    # This will be more precise than relying only on implicit_wait.
    try:
        # Wait up to 20 seconds for the main <article> tag (which contains the post) to be present
        # This is generally a good indicator that the post content has rendered.
        tqdm.write(f"[i] Waiting for <article> arrival...")
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "article"))
        )
        
        # Now that the article is present, safely try to find the time element.
        # It's good to keep a short explicit wait here too, in case time_elem appears slightly later
        # or if the article contains multiple elements.
        tqdm.write(f"[i] Looking for <time> tag...")
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

    def check_for_video():
        nonlocal video_detected
        tqdm.write(f"[i] Searching for <video> tags...")
        videos = driver.find_elements(By.TAG_NAME, "video")
        if videos:
            tqdm.write(f"[▶] Detected {len(videos)} <video> tag(s) — using yt-dlp later")
            video_detected = True
        else:
            tqdm.write(f"[i] No <video> tag(s) detected")

    def collect_images():
        nonlocal index
        tqdm.write(f"[i] Searching for <img> tags...")
        img_tags = driver.find_elements(By.TAG_NAME, "img")

        processed_imgtag_count = 0  # Counter for all <img> tags processed on the current slide
        collected_count_on_slide = 0 # Counter for images that actually meet criteria and are collected

        # Single pass to process, filter, and collect images
        total = len(img_tags)
        for i, img in tqdm(enumerate(img_tags), leave=False):
            processed_imgtag_count += 1
            #update_line(f"[→] Processing <img> tags {processed_imgtag_count}/{total} on current slide.")
            #print()

            url = img.get_attribute("src")
            
            # Skip if URL is empty or already seen
            if not url or url in seen_urls:
                continue

            # Get bounding box dimensions - this is the main operation
            box = driver.execute_script("""
                const rect = arguments[0].getBoundingClientRect();
                return {width: rect.width, height: rect.height, top: rect.top, left: rect.left};
            """, img)

            # Apply filtering criteria
            if box["width"] < 320 or box["height"] < 300:
                continue
            if box["top"] < 0 or box["left"] < 0:
                continue

            # If all checks pass, collect the image
            seen_urls.add(url)
            label = f"video_still_{index:02d}" if video_detected else f"image_{index:02d}"
            media_items.append((url, label))
            
            collected_count_on_slide += 1
            # [+] Message: Show how many media items have been collected so far.
            # We can indicate it's out of the total img tags scanned for context.
            tqdm.write(f"  [+] Collected media {collected_count_on_slide}/{len(img_tags)} (total scanned): {label}")
            
            index += 1 # Increment global index for the next item

    next_button_xpath = '//button[contains(@class, "_afxw") or @aria-label="Next"]'
    slide_count = 1

    while True:
        tqdm.write(f"[→] Processing slide {slide_count}")
        check_for_video()
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

    try:
        if video_detected or not media_items: # If videos were detected, or no images found, try yt-dlp
            tqdm.write(f"[▶] Downloading video(s) via yt-dlp from post: {shortcode}")
            ydl_opts = {
                'outtmpl': os.path.join(post_dir, '%(title)s [%(id)s].%(ext)s'),
                'quiet': True, # Keep yt-dlp quiet to not mess with tqdm
                'verbose': False,
                'no_warnings': True,
                'progress': False # Disable yt-dlp's internal progress bar
            }
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([post_url])
    except Exception as e:
        tqdm.write(f"[!] yt-dlp error: {e}")
        with open(ERROR_LOG, "a") as elog:
            elog.write(f"{post_url} — yt-dlp error: {e}\n")

    if not media_items and not video_detected:
        tqdm.write(f"[!] WARNING: No media found for {post_url}")
        with open(ERROR_LOG, "a") as elog:
            elog.write(f"{post_url} — no media found\n")
    else:
        tqdm.write(f"[✓] {len(media_items)} image(s) saved → {post_dir}/media_urls.txt")
        # The RESUME_FILE still stores the last processed URL, which is a good quick start
        with open(RESUME_FILE, "w") as rfile:
            rfile.write(post_url)

    return media_items, post_dir


def download_media(media_items, target_dir):
    # Added tqdm around the media_items loop for progress on downloads
    for url, label in tqdm(media_items, desc=f"Downloading media to {os.path.basename(target_dir)}", leave=False):
        ext = os.path.splitext(urllib.parse.urlparse(url).path)[-1]
        filename = f"{label}{ext if ext else '.bin'}"
        filepath = os.path.join(target_dir, sanitize_filename(filename))
        if not os.path.exists(filepath):
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


# === Main Execution ===
def main():
    try:
        if POST_URL:
            # If a specific post ID is provided, just scrape that one
            items, dir_path = extract_media_urls(POST_URL)
            download_media(items, dir_path)
            # When processing a single post, add it to processed URLs if successful
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
                    items, dir_path = extract_media_urls(link_to_process)
                    download_media(items, dir_path)
                    # Mark this URL as successfully processed and save the updated set
                    processed_urls.add(link_to_process)
                    save_processed_urls(PROCESSED_URLS_FILE, processed_urls)
                except Exception as e:
                    tqdm.write(f"[!!!] Error processing {link_to_process}: {e}")
                    with open(ERROR_LOG, "a") as elog:
                        elog.write(f"{link_to_process} — main loop error: {e}\n")

    except KeyboardInterrupt:
        print("[!] Interrupted by user - please wait for clean exit...")
    finally:
        driver.quit()
        print("[✓] Browser closed.")

if __name__ == "__main__":
    main()

