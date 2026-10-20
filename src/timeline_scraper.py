import os
import time
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright
from src.config import (
    DEFAULT_OUTPUT_FILE,
    TIMEZONE,
    TIMELINE_MAX_TWEETS
)
from src.utils import (
    save_tweets,
    extract_tweet_data,
    check_session_validity,
    launch_browser_context,
    close_browser_context
)
from src.thread_scraper import scrape_thread

def run_timeline_scraper(output_file=None, max_tweets=None, lookback_days=1, include_replies=False, include_threads=False, headless=True):
    """
    Main runner to scrape the logged-in user's Home timeline feed.
    Stops when it collects max_tweets (defaults to TIMELINE_MAX_TWEETS in config).
    """
    output_path = output_file or DEFAULT_OUTPUT_FILE
    limit = max_tweets or TIMELINE_MAX_TWEETS
    
    # We still compute cutoff_date solely for scraping thread continuations if requested
    now_ist = datetime.now(TIMEZONE)
    cutoff_date = (now_ist - timedelta(days=lookback_days)).date()
    
    print(f"\n--- Scraping Home Timeline Feed ---")
    print(f"Limit: {limit} tweets (headless={headless})")

    tweets_data = []
    seen_urls = set()

    with sync_playwright() as p:
        # Load standard browser context (must have session file)
        browser, context = launch_browser_context(p, headless=headless)
        page = context.new_page()
        page.set_default_timeout(60000)
        
        thread_page = None
        if include_threads:
            thread_page = context.new_page()
            thread_page.set_default_timeout(60000)

        session_expired = False
        try:
            page.goto("https://x.com/home", wait_until="domcontentloaded")
            time.sleep(6)
            
            # Check login state
            if not check_session_validity(page, "https://x.com/home"):
                session_expired = True
            else:
                # Wait for main feed content
                page.wait_for_selector("article", timeout=15000)
                time.sleep(3)
        except Exception as e:
            print(f"Error loading home feed: {e}")
            session_expired = True

        if not session_expired:
            reached_limit = False
            scroll_count = 0
            stale_scrolls = 0
            timeline_tweets = []

            while not reached_limit and scroll_count < 40:
                if not check_session_validity(page, "https://x.com/home"):
                    session_expired = True
                    break

                tweets = page.locator("article")
                count = tweets.count()

                if count == 0:
                    page.evaluate("window.scrollBy(0, 1000)")
                    time.sleep(2)
                    scroll_count += 1
                    stale_scrolls += 1
                    if stale_scrolls >= 6:
                        break
                    continue

                new_tweets_this_scroll = 0
                for i in range(count):
                    tweet_block = tweets.nth(i)
                    
                    # 1. Skip Promoted Tweets (Ads)
                    try:
                        promoted_locator = tweet_block.locator('span:text-is("Promoted"), span:has-text("Promoted")')
                        if promoted_locator.count() > 0:
                            continue
                    except:
                        pass

                    tweet_data = extract_tweet_data(tweet_block, "home_feed", TIMEZONE)
                    if not tweet_data:
                        continue

                    tweet_url = tweet_data[5]
                    if tweet_url in seen_urls:
                        continue
                    seen_urls.add(tweet_url)
                    new_tweets_this_scroll += 1

                    # 2. Check Type Filter
                    tweet_type = tweet_data[3]
                    if tweet_type == "Reply" and not include_replies:
                        # Skip replies if not requested
                        continue

                    timeline_tweets.append(tweet_data)
                    print(f"Saved home feed tweet: {tweet_url} by @{tweet_data[0]} ({tweet_data[1]} {tweet_data[2]}) [{tweet_type}]")

                    # 3. Check Tweet Count Limit
                    if len(timeline_tweets) >= limit:
                        print(f"Reached home timeline limit of {limit} tweets.")
                        reached_limit = True
                        break

                if reached_limit:
                    break

                if new_tweets_this_scroll == 0:
                    stale_scrolls += 1
                else:
                    stale_scrolls = 0

                if stale_scrolls >= 4:
                    print("Stale scroll detected (no new home feed tweets). Stopping.")
                    break

                page.evaluate("window.scrollBy(0, 3000)")
                time.sleep(3)
                scroll_count += 1

            # 4. Scrape Threads if requested
            if include_threads and thread_page and timeline_tweets and not session_expired:
                print(f"\nScraping thread replies for timeline feed...")
                thread_tweets = []
                for tweet_row in timeline_tweets:
                    author = tweet_row[0]
                    url = tweet_row[5]
                    type_str = tweet_row[3]
                    
                    if type_str in ("Tweet", "Reply"):
                        # Check session validity
                        if not check_session_validity(page, "https://x.com/home"):
                            session_expired = True
                            break
                        
                        thread_rows = scrape_thread(thread_page, author, url, cutoff_date)
                        thread_tweets.extend(thread_rows)
                
                timeline_tweets.extend(thread_tweets)

            tweets_data.extend(timeline_tweets)
            print(f"\nScraped {len(timeline_tweets)} total tweets from Home timeline feed.")

        close_browser_context(browser, context)

    # Save outputs
    if tweets_data:
        save_tweets(tweets_data, output_path, mode="merge")
    else:
        print("No new tweets scraped.")

    if session_expired:
        print("\n[ALERT] Scraping was aborted because the session expired.")
        print("Please log in again using: uv run main.py login")
