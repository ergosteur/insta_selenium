from setuptools import setup, find_packages

setup(
    name="insta_selenium",
    version="0.1.1",
    description="A command-line tool for scraping Instagram post and reel media using Selenium.",
    author="ergosteur",
    author_email="ergosteur@gmail.com",
    packages=find_packages(),
    py_modules=["scrape_instagram"],
    install_requires=[
        "selenium>=4.0.0",
        "webdriver-manager>=3.8.0",
        "yt-dlp",
        "tqdm",
        "requests>=2.25.0",
    ],
    entry_points={
        "console_scripts": [
            "insta_selenium=scrape_instagram:main"
        ]
    },
    python_requires=">=3.8",
)
