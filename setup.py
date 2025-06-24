from setuptools import setup, find_packages

setup(
    name="instagram-scraper",
    version="0.1.0",
    description="A command-line tool for scraping Instagram post and reel media using Selenium.",
    author="ergosteur",
    author_email="ergosteur@gmail.com",
    packages=find_packages(),
    py_modules=["scrape_instagram"],
    install_requires=[
        "selenium==4.33.0",
        "selenium-wire==5.1.0",
        "yt-dlp",
        "tqdm",
        "requests==2.32.4",
        "python-dotenv==1.1.0",
        "webdriver-manager==4.0.2"
    ],
    entry_points={
        "console_scripts": [
            "scrape-instagram=scrape_instagram:main"
        ]
    },
    python_requires=">=3.8",
)
