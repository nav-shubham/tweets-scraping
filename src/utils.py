import os
import time
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from src.config import (
    SESSION_FILE,
    TIMEZONE
)

def load_users(input_file_path):
    """
    Loads and validates the list of target usernames from the input CSV.
    """
    if not os.path.exists(input_file_path):
        raise FileNotFoundError(f"Input file not found at: {input_file_path}")
    
    try:
        df = pd.read_csv(input_file_path)
    except Exception as e:
        raise ValueError(f"Failed to read input CSV: {e}")
        
    if 'username' not in df.columns:
        raise ValueError("Input CSV must contain a 'username' column.")
        
    users = df['username'].dropna().astype(str).str.strip().tolist()
    # Filter out empty or header-like entries
    users = [u for u in users if u and u.lower() != 'username']
    return users

def save_tweets(tweets_data, output_file_path, mode="merge"):
    """
    Saves scraped tweets to the CSV file.
    Modes:
      - "merge": merges with existing CSV and removes duplicate URLs
      - "overwrite": writes a fresh CSV file
    """
    if not tweets_data:
        print("No tweets to save.")
        return

    df_new = pd.DataFrame(
        tweets_data,
        columns=["Username", "Date", "Time", "Type", "Tweet", "URL"]
    )
    
    # Ensure directory exists
    output_dir = Path(output_file_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if mode == "merge" and os.path.exists(output_file_path):
        try:
            df_existing = pd.read_csv(output_file_path)
            df_combined = pd.concat([df_existing, df_new], ignore_index=True)
            df_combined.drop_duplicates(subset=["URL"], inplace=True)
            df_combined.to_csv(output_file_path, index=False)
            print(f"Successfully saved. Total tweets in {output_file_path}: {len(df_combined)} (New/Updated: {len(df_new)})")
            return
        except Exception as e:
            print(f"Warning: Failed to merge with existing CSV ({e}). Writing fresh file.")
            
    df_new.drop_duplicates(subset=["URL"], inplace=True)
    df_new.to_csv(output_file_path, index=False)
    print(f"Successfully saved {len(df_new)} tweets to {output_file_path}.")

def check_session_validity(page, current_url):
    """
    Checks if the page is currently redirected to the login wall.
    Returns True if session is valid, False if redirect to login occurred.
    """
    try:
        url = page.url.lower()
        if "login" in url or "flow/login" in url or "i/flow" in url:
            print("Session Expiry Alert: Redirected to login wall!")
            return False
    except Exception as e:
        print(f"Warning: Failed to check page URL for session validity: {e}")
    return True

def detect_tweet_type(tweet_block):
    """
    Accurately detects type of tweet using DOM structures and content.
    Returns: "Retweet", "Quote", "Reply", "Tweet" (or "Pinned").
    """
    try:
        # 1. Pinned Tweet check (look for pin indicator in socialContext)
        social_context = tweet_block.locator('div[data-testid="socialContext"]')
        is_retweet = False
        is_pinned = False
        if social_context.count() > 0:
            ctx_text = social_context.first.inner_text().lower()
            if "pinned" in ctx_text:
                is_pinned = True
            elif "reposted" in ctx_text or "retweet" in ctx_text:
                is_retweet = True

        if is_pinned:
            return "Pinned"
        if is_retweet:
            return "Retweet"

        # 2. Quote Tweet check (nested quote tweet card)
        is_quote = tweet_block.locator('div[data-testid="quoteTweet"]').count() > 0
        if is_quote:
            return "Quote"

        # 3. Reply check (text contains Replying to at the top or reply context)
        full_text_lower = tweet_block.inner_text().lower()
        if "replying to" in full_text_lower:
            return "Reply"

    except Exception as e:
        pass

    return "Tweet"

def extract_tweet_data(tweet_block, target_user, timezone):
    """
    Parses a single tweet block (article) and returns list of data if successful.
    Returns: [username, date, time, tweet_type, tweet_text, tweet_url] or None
    """
    try:
        # 1. Extract Tweet URL
        link_element = tweet_block.locator("a[href*='/status/']").first
        tweet_url = link_element.get_attribute("href")
        if not tweet_url:
            return None
        
        # Clean URL and check for absolute vs relative path doubling bug
        raw_href = tweet_url.split("?")[0].split("#")[0]
        if raw_href.startswith("http"):
            tweet_url = raw_href
        else:
            tweet_url = "https://x.com" + ("" if raw_href.startswith("/") else "/") + raw_href
        
        # Extract username from URL path: /username/status/xxxx
        parts = tweet_url.split("/")
        extracted_user = target_user
        if len(parts) > 4 and parts[4] == 'status':
            extracted_user = parts[3]

        # 2. Extract and parse timestamp
        time_element = tweet_block.locator("time").first
        tweet_date_str = time_element.get_attribute("datetime")
        if not tweet_date_str:
            return None
        
        tweet_utc = datetime.fromisoformat(tweet_date_str.replace("Z", "+00:00"))
        tweet_ist = tweet_utc.astimezone(timezone)
        
        # 3. Extract Text
        text_element = tweet_block.locator('div[data-testid="tweetText"]').first
        tweet_text = text_element.inner_text() if text_element.count() > 0 else ""
        
        # 4. Type
        tweet_type = detect_tweet_type(tweet_block)
        
        return [
            extracted_user,
            tweet_ist.strftime("%d-%m-%Y"),
            tweet_ist.strftime("%H:%M"),
            tweet_type,
            tweet_text,
            tweet_url
        ]
    except Exception as e:
        return None

def launch_browser_context(p, headless=True):
    """
    Launches standard Chromium context using the saved session state file.
    Uses custom user-agent and arguments to avoid headless detection blocks by X.
    """
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    
    # Launch options to disguise automation
    launch_args = [
        "--disable-blink-features=AutomationControlled",
        "--no-sandbox",
        "--disable-setuid-sandbox",
    ]
    
    browser = p.chromium.launch(headless=headless, args=launch_args)
    
    context_options = {
        "user_agent": user_agent,
        "viewport": {"width": 1280, "height": 800},
        "locale": "en-US",
        "timezone_id": "Asia/Kolkata",
    }
    
    if os.path.exists(SESSION_FILE):
        print(f"Launching standard Chromium with saved session from: {SESSION_FILE}")
        context_options["storage_state"] = str(SESSION_FILE)
        context = browser.new_context(**context_options)
        return browser, context
    else:
        print(f"Warning: Saved session file ({SESSION_FILE}) not found. Launching clean browser.")
        context = browser.new_context(**context_options)
        return browser, context

def close_browser_context(browser, context):
    """Closes standard browser and context clean."""
    try:
        if browser:
            browser.close()
    except Exception as e:
        print(f"Warning: Error closing browser: {e}")
