# yt-dlp_instagram_carousel_test.py
import sys
from yt_dlp import YoutubeDL

if len(sys.argv) < 3:
    print("Usage: python yt-dlp_instagram_carousel_test.py <instagram_post_url> <firefox_profile_path>")
    sys.exit(1)

post_url = sys.argv[1]
firefox_profile = sys.argv[2]

ydl_opts = {
    'cookiesfrombrowser': ('firefox', firefox_profile),
    'noplaylist': False,  # Treat as playlist (carousel)
    'quiet': False,       # Show yt-dlp output
    'verbose': True,
    'no_warnings': False,
    'progress': True,
    'ignoreerrors': True,  # <-- Add this line!
    'outtmpl': '%(title)s-[%(id)s].%(ext)s',  # Uncomment to customize output filename
    'format': 'bestvideo+bestaudio/best',  # Download best quality video and audio
    'postprocessors': [{
        'key': 'FFmpegVideoConvertor',
        'preferedformat': 'mp4',  # Convert to mp4 format
    }],
}

with YoutubeDL(ydl_opts) as ydl:
    ydl.download([post_url])