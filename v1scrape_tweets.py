from playwright.sync_api import sync_playwright
import pandas as pd
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

users = pd.read_csv("users.csv")
tweets_data = []

IST = ZoneInfo("Asia/Kolkata")
now_ist = datetime.now(IST)
yesterday_ist = now_ist - timedelta(days=1)
cutoff_date = yesterday_ist.date()

brave_exe = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
brave_profile = r"C:\Users\Shubham Kadam\AppData\Local\BraveSoftware\Brave-Browser\User Data"


def parse_tweet_datetime(dt_str):
    return datetime.fromisoformat(dt_str.replace("Z", "+00:00")).astimezone(IST)


def scrape_thread(thread_page, user, main_url, cutoff_date):
    """
    Opens a tweet URL and collects all tweets authored by the same user
    from that thread page. Main timeline logic stays untouched.
    """
    rows = []
    seen = set()
    stable_rounds = 0

    try:
        thread_page.goto(main_url, wait_until="domcontentloaded")
        thread_page.wait_for_selector("article")
        time.sleep(4)
    except Exception as e:
        print("Thread open error:", e)
        return rows

    while stable_rounds < 2:
        added_this_round = 0
        articles = thread_page.locator("article")
        count = articles.count()

        for i in range(count):
            try:
                tweet_block = articles.nth(i)

                full_text_lower = tweet_block.inner_text().lower()

                # Keep only tweets from the same author.
                # This avoids replies from other users on the thread page.
                if f"@{user.lower()}" not in full_text_lower:
                    continue

                link_element = tweet_block.locator("a[href*='/status/']").first
                tweet_url = link_element.get_attribute("href")
                if not tweet_url:
                    continue

                tweet_url = "https://x.com" + tweet_url.split("?")[0].split("#")[0]

                if tweet_url == main_url:
                    continue

                if tweet_url in seen:
                    continue
                seen.add(tweet_url)

                time_element = tweet_block.locator("time").first
                tweet_date_str = time_element.get_attribute("datetime")
                if not tweet_date_str:
                    continue

                tweet_ist = parse_tweet_datetime(tweet_date_str)

                if tweet_ist.date() < cutoff_date:
                    continue

                text_element = tweet_block.locator('div[data-testid="tweetText"]').first
                tweet_text = text_element.inner_text() if text_element.count() > 0 else ""

                if "reposted" in full_text_lower:
                    tweet_type = "Retweet"
                elif "quote" in full_text_lower:
                    tweet_type = "Quote"
                else:
                    tweet_type = "Tweet"

                rows.append([
                    user,
                    tweet_ist.strftime("%d-%m-%Y"),
                    tweet_ist.strftime("%H:%M"),
                    tweet_type,
                    tweet_text,
                    tweet_url
                ])
                added_this_round += 1

            except Exception as e:
                print("Thread row error:", e)

        if added_this_round == 0:
            stable_rounds += 1
        else:
            stable_rounds = 0

        try:
            thread_page.evaluate("window.scrollBy(0, 2500)")
        except:
            pass

        time.sleep(2)

    return rows


with sync_playwright() as p:
    browser = p.chromium.launch_persistent_context(
        user_data_dir=brave_profile,
        executable_path=brave_exe,
        headless=False
    )

    page = browser.new_page()
    thread_page = browser.new_page()

    for user in users["username"]:
        print("Scraping", user)

        page.goto(f"https://x.com/{user}", wait_until="domcontentloaded")
        page.wait_for_selector("article")
        time.sleep(6)

        seen_urls = set()
        reached_old = False

        while not reached_old:
            tweets = page.locator("article")
            count = tweets.count()

            print("Articles found:", count)

            for i in range(count):
                tweet_block = tweets.nth(i)

                try:
                    # Tweet URL
                    link_element = tweet_block.locator("a[href*='/status/']").first
                    tweet_url = link_element.get_attribute("href")
                    if not tweet_url:
                        continue

                    tweet_url = "https://x.com" + tweet_url.split("?")[0].split("#")[0]

                    if tweet_url in seen_urls:
                        continue

                    seen_urls.add(tweet_url)

                    # Tweet time UTC → IST
                    time_element = tweet_block.locator("time").first
                    tweet_date_str = time_element.get_attribute("datetime")
                    if not tweet_date_str:
                        continue

                    tweet_utc = datetime.fromisoformat(tweet_date_str.replace("Z", "+00:00"))
                    tweet_ist = tweet_utc.astimezone(IST)

                    if tweet_ist.date() < cutoff_date:
                        reached_old = True
                        break

                    # Tweet text
                    text_element = tweet_block.locator('div[data-testid="tweetText"]').first
                    tweet_text = text_element.inner_text() if text_element.count() > 0 else ""

                    # Tweet type
                    full_text = tweet_block.inner_text().lower()
                    if "reposted" in full_text:
                        tweet_type = "Retweet"
                    elif "quote" in full_text:
                        tweet_type = "Quote"
                    else:
                        tweet_type = "Tweet"

                    # Save the original tweet exactly as your script does
                    tweets_data.append([
                        user,
                        tweet_ist.strftime("%d-%m-%Y"),
                        tweet_ist.strftime("%H:%M"),
                        tweet_type,
                        tweet_text,
                        tweet_url
                    ])

                    print("Saved main tweet:", tweet_url)

                    # Add thread tweets from the status page
                    thread_rows = scrape_thread(
                        thread_page=thread_page,
                        user=user,
                        main_url=tweet_url,
                        cutoff_date=cutoff_date
                    )
                    tweets_data.extend(thread_rows)

                except Exception as e:
                    print("Main loop error:", e)

            page.evaluate("window.scrollBy(0, 3000)")
            time.sleep(3)

        print(user, "done")

    browser.close()

df = pd.DataFrame(
    tweets_data,
    columns=["Username", "Date", "Time", "Type", "Tweet", "URL"]
)

df.drop_duplicates(subset=["URL"], inplace=True)
df.to_csv("tweets.csv", index=False)

print("Tweets scraped successfully.")
print("Total collected:", len(df))
