# Tweets Scraping - Playwright Twitter Scraper

This is a Playwright-based Twitter/X scraper designed to automatically extract tweets, retweets, and quote tweets for a list of target usernames, and save them in a structured CSV format.

## 🚀 Features

- **Automated Login & Session Saving**: Manually log in once to X, and save your authentication tokens to `twitter_session.json` to bypass logins on subsequent runs.
- **Persistent Profile Support**: Optionally hooks directly into your local Brave browser profile to leverage pre-existing X sessions.
- **Timezone Conversion**: Automatically converts tweet UTC timestamps into Indian Standard Time (IST).
- **Date Filtering**: Grabs tweets dynamically up to a lookback window (e.g., from yesterday to today) and stops scrolling once older tweets are encountered.
- **Data Export**: Exports all scraped tweets with columns: `Username`, `Date`, `Time`, `Type`, `Tweet`, and `URL` to a clean `tweets.csv` file.

---

## 📁 Project Structure

- `login.py` - Script to open a browser, perform manual login, and save cookies to `twitter_session.json`.
- `scrape_tweets.py` - Core scraper script that loads profiles/sessions, visits usernames, scrolls, extracts, and parses tweets.
- `users.csv` - Target usernames list containing a `username` column.
- `tweets.csv` - Output CSV file with scraped tweet details.
- `pyproject.toml` / `requirements.txt` - Project dependencies.

---

## 🛠️ Setup & Execution

### 1. Setup Environment
This project uses `playwright` which requires browser binaries. In this directory, run:
```bash
uv venv
uv sync
uv run playwright install
```

### 2. Save X (Twitter) Session
Before scraping, you need an authenticated session so Twitter displays full tweet histories.
1. Run `login.py`:
   ```bash
   uv run login.py
   ```
2. A Chromium window will open. Log in manually.
3. Once logged in, go back to the terminal and press `ENTER`. The session will be saved in `twitter_session.json`.

### 3. Add Targets
Add the Twitter usernames you want to track into `users.csv`. Example:
```csv
username
elonmusk
naval
```

### 4. Run Scraper
Launch the scraper:
```bash
uv run scrape_tweets.py
```
This will parse the feeds, download tweets from the lookback range, and save the output in `tweets.csv`.
