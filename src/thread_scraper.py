import time
from datetime import datetime
from src.config import TIMEZONE
from src.utils import extract_tweet_data

def scrape_thread(thread_page, user, main_url, cutoff_date):
    """
    Opens a tweet URL and collects all tweets authored by the same user
    from that thread page. Avoids replies from other users.
    """
    rows = []
    seen = set()
    stable_rounds = 0
    max_rounds = 10 # Safety scroll limit on thread page

    print(f"  Scraping thread replies for: {main_url}")
    try:
        thread_page.goto(main_url, wait_until="domcontentloaded")
        thread_page.wait_for_selector("article", timeout=12000)
        time.sleep(4)
    except Exception as e:
        print(f"  Warning: Thread open error for {main_url}: {e}")
        return rows

    round_count = 0
    while stable_rounds < 2 and round_count < max_rounds:
        added_this_round = 0
        articles = thread_page.locator("article")
        count = articles.count()

        for i in range(count):
            try:
                tweet_block = articles.nth(i)
                # Verify author using the URL (cleaner and more robust)
                link_element = tweet_block.locator("a[href*='/status/']").first
                tweet_url = link_element.get_attribute("href")
                if not tweet_url:
                    continue

                raw_href = tweet_url.split("?")[0].split("#")[0]
                if raw_href.startswith("http"):
                    tweet_url = raw_href
                else:
                    tweet_url = "https://x.com" + ("" if raw_href.startswith("/") else "/") + raw_href
                
                # Check URL parts to verify author
                parts = tweet_url.split("/")
                if len(parts) > 3 and parts[3].lower() != user.lower():
                    continue

                if tweet_url == main_url:
                    continue

                if tweet_url in seen:
                    continue
                seen.add(tweet_url)

                tweet_data = extract_tweet_data(tweet_block, user, TIMEZONE)
                if not tweet_data:
                    continue

                # Parse date
                tweet_date = datetime.strptime(tweet_data[1], "%d-%m-%Y").date()
                if tweet_date < cutoff_date:
                    continue

                rows.append(tweet_data)
                added_this_round += 1
                print(f"  [Thread Reply] Saved: {tweet_url} ({tweet_data[1]})")

            except Exception as e:
                pass

        if added_this_round == 0:
            stable_rounds += 1
        else:
            stable_rounds = 0

        try:
            thread_page.evaluate("window.scrollBy(0, 2500)")
        except:
            pass

        time.sleep(2)
        round_count += 1

    return rows
