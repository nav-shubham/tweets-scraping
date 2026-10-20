import os
import time
import pandas as pd
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright
from src.config import (
    DEFAULT_INPUT_FILE,
    DEFAULT_OUTPUT_FILE,
    TIMEZONE
)
from src.utils import (
    load_users,
    save_tweets,
    extract_tweet_data,
    check_session_validity,
    launch_browser_context,
    close_browser_context
)
from src.thread_scraper import scrape_thread

def scrape_user_tab(page, user, url, cutoff_date, tweets_data, seen_urls):
    """
    Helper function to scrape a specific tab for a user (either main timeline or replies tab).
    """
    print(f"Scraping timeline: {url}")
    try:
        page.goto(url, wait_until="domcontentloaded")
        time.sleep(5)
        # Check if redirected to login
        if not check_session_validity(page, url):
            return False
        
        # Wait for either article or no-tweet indicators
        page.wait_for_selector("article", timeout=12000)
        time.sleep(3)
    except Exception as e:
        print(f"Warning: Failed to load timeline or wait for articles: {e}")
        return True # continue to next tab/user rather than crashing

    reached_old = False
    scroll_count = 0
    stale_scrolls = 0

    while not reached_old and scroll_count < 25:
        # Check login redirection on scroll
        if not check_session_validity(page, url):
            return False

        tweets = page.locator("article")
        count = tweets.count()

        if count == 0:
            page.evaluate("window.scrollBy(0, 1000)")
            time.sleep(2)
            scroll_count += 1
            stale_scrolls += 1
            if stale_scrolls >= 5:
                print("No tweets loaded. Skipping.")
                break
            continue

        new_tweets_this_scroll = 0
        for i in range(count):
            tweet_block = tweets.nth(i)
            tweet_data = extract_tweet_data(tweet_block, user, TIMEZONE)
            if not tweet_data:
                continue

            tweet_url = tweet_data[5]
            if tweet_url in seen_urls:
                continue
            seen_urls.add(tweet_url)
            new_tweets_this_scroll += 1

            # Parse date
            tweet_date = datetime.strptime(tweet_data[1], "%d-%m-%Y").date()
            if tweet_date < cutoff_date:
                # Pinned tweets appear at top but can be older
                if tweet_data[3] == "Pinned":
                    continue
                print(f"Reached tweet older than cutoff date: {tweet_date}")
                reached_old = True
                break

            tweets_data.append(tweet_data)

        if reached_old:
            break

        if new_tweets_this_scroll == 0:
            stale_scrolls += 1
        else:
            stale_scrolls = 0

        if stale_scrolls >= 3:
            print("Stale scroll detected (no new tweets found). Stopping.")
            break

        page.evaluate("window.scrollBy(0, 3000)")
        time.sleep(3)
        scroll_count += 1

    return True

def run_profile_scraper(input_file=None, output_file=None, lookback_days=1, include_replies=False, include_threads=False, headless=True):
    """
    Main runner to scrape profile feeds.
    """
    input_path = input_file or DEFAULT_INPUT_FILE
    output_path = output_file or DEFAULT_OUTPUT_FILE

    # Load users
    try:
        users = load_users(input_path)
    except Exception as e:
        print(f"Error loading users from {input_path}: {e}")
        return

    # Cutoff date
    now_ist = datetime.now(TIMEZONE)
    cutoff_date = (now_ist - timedelta(days=lookback_days)).date()
    print(f"Target users: {users}")
    print(f"Date window: {cutoff_date} to {now_ist.date()} ({lookback_days} day lookback)")

    tweets_data = []

    with sync_playwright() as p:
        browser, context = launch_browser_context(p, headless=headless)
        page = context.new_page()
        page.set_default_timeout(60000)
        
        # Second page for scraping threads without losing scroll state on main page
        thread_page = None
        if include_threads:
            thread_page = context.new_page()
            thread_page.set_default_timeout(60000)

        session_expired = False
        for user in users:
            print(f"\n--- Scraping @{user} ---")
            seen_urls = set()
            user_tweets = []

            # 1. Scrape main posts timeline
            main_url = f"https://x.com/{user}"
            success = scrape_user_tab(page, user, main_url, cutoff_date, user_tweets, seen_urls)
            if not success:
                session_expired = True
                tweets_data.extend(user_tweets) # save what we have
                break

            # 2. Scrape replies tab if requested
            if include_replies:
                replies_url = f"https://x.com/{user}/with_replies"
                success = scrape_user_tab(page, user, replies_url, cutoff_date, user_tweets, seen_urls)
                if not success:
                    session_expired = True
                    tweets_data.extend(user_tweets)
                    break

            # 3. Follow status pages to scrape thread continuations if requested
            if include_threads and thread_page and user_tweets:
                print(f"Scraping thread continuations for @{user}...")
                main_tweet_urls = [t[5] for t in user_tweets if t[3] in ("Tweet", "Reply")]
                thread_tweets = []
                for url in main_tweet_urls:
                    # Check session validity
                    if not check_session_validity(page, main_url):
                        session_expired = True
                        break
                    
                    thread_rows = scrape_thread(thread_page, user, url, cutoff_date)
                    thread_tweets.extend(thread_rows)
                
                # Combine thread tweets
                user_tweets.extend(thread_tweets)

            tweets_data.extend(user_tweets)
            print(f"Collected {len(user_tweets)} tweets for @{user}")

            if session_expired:
                break

        close_browser_context(browser, context)

    # Save outputs
    if tweets_data:
        save_tweets(tweets_data, output_path, mode="merge")
    else:
        print("No new tweets scraped.")

    if session_expired:
        print("\n[ALERT] Scraping was aborted because the session expired.")
        print("Please log in again using: uv run main.py login")
