# Tweets Scraping - Playwright Twitter Scraper

This is a Playwright-based Twitter/X scraper designed to automatically extract tweets, retweets, and quote tweets for a list of target usernames, and save them in a structured CSV format.

## 🚀 Features

- **Automated & Manual Login modes**: Authenticate manually or automate X logins using environment credentials. Session tokens are saved to `sessions/twitter_session.json` to bypass logins on subsequent runs.
- **Headless by Default**: Performs all scrapes in the background (headless) to save resources, with an optional visible browser mode for debugging.
- **Unified Scraping Interface**: Scrape target user profiles, Home timeline feed, reply tabs, and thread continuations through simple command-line flags.
- **Timezone Conversion**: Automatically converts tweet UTC timestamps into Indian Standard Time (IST).
- **Date Filtering**: Grabs tweets dynamically up to a lookback window and stops scrolling once older tweets are encountered.
- **Data Export**: Merges, deduplicates, and saves scraped tweets in a clean `tweets.csv` file.

---

## 📁 Project Structure

- `src/` - Core scraper modules:
  - [config.py](file:///D:/PythonTools/tweets_scraping/src/config.py) - Centralized configuration of files, directories, and browser settings (loads `.env`).
  - [login.py](file:///D:/PythonTools/tweets_scraping/src/login.py) - Manages manual and automated login workflows.
  - [scraper.py](file:///D:/PythonTools/tweets_scraping/src/scraper.py) - Scrapes target user profile timelines & reply tabs.
  - [thread_scraper.py](file:///D:/PythonTools/tweets_scraping/src/thread_scraper.py) - Follows tweet status links to scrape thread continuations.
  - [timeline_scraper.py](file:///D:/PythonTools/tweets_scraping/src/timeline_scraper.py) - Scrapes your logged-in Home timeline feed.
  - [utils.py](file:///D:/PythonTools/tweets_scraping/src/utils.py) - Shared helper functions for parsing, saving, and context setup.
- `data/` - Input and output directory:
  - `inputs/` - Target usernames lists (e.g., `users.csv`, `users1.csv`).
  - `outputs/` - Scraped outputs (e.g., `tweets.csv`).
- `sessions/` - Stores persistent authentication state (`twitter_session.json`).
- `main.py` - Root level CLI entry point.
- `pyproject.toml` / `uv.lock` - Project dependencies managed by `uv`.
- `.env.example` - Template for environment credentials.

---

## 🛠️ Setup & Execution

### 1. Setup Environment
This project uses `playwright` which requires browser binaries. In this directory, run:
```bash
uv venv
uv sync
uv run playwright install
```

### 2. Configure Credentials (Optional)
If you want to use the automated login script, copy `.env.example` to `.env` and fill in your Twitter/X credentials:
```bash
cp .env.example .env
```
Open `.env` and edit:
```env
X_USERNAME=your_username
X_PASSWORD=your_password
X_EMAIL=your_email@example.com
```

### 3. Save X (Twitter) Session
Before scraping, you need an authenticated session so Twitter displays full tweet histories.

- **Option A (Manual)**: Run and log in by hand in the opened browser window:
  ```bash
  uv run main.py login --manual
  ```
- **Option B (Automated)**: Run to automatically fill credentials from your `.env` file:
  ```bash
  uv run main.py login --auto
  ```

### 4. Run Scraper Pipeline (One-Click)
To scrape everything in sequence (checks login -> scrapes target profiles -> scrapes home timeline feed -> saves and merges all output with reply & thread continuations), simply run:
```bash
uv run main.py
```
This is the easiest way to run the entire scraper without needing to memorize any command flags.

### 🎛️ Advanced Command-line Options (Optional)
If you want to run specific sub-tasks or customize paths, the CLI supports additional commands:
```bash
# Scrape target profiles only
uv run main.py scrape

# Scrape target profiles and include replies
uv run main.py scrape --include-replies

# Scrape profiles and follow threads
uv run main.py scrape --include-threads

# Scrape your Home timeline feed instead of profiles
uv run main.py scrape --timeline

# Custom input/output paths, 3 days profile lookback, and 50 timeline tweet limit
uv run main.py scrape -i data/inputs/users1.csv -o data/outputs/custom.csv -l 3 --limit 50

# Run scraping visibly (for debugging)
uv run main.py scrape --show-browser
```




