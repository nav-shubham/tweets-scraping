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

brave_exe = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
brave_profile = r"C:\Users\Shubham Kadam\AppData\Local\BraveSoftware\Brave-Browser\User Data"

with sync_playwright() as p:
    browser = p.chromium.launch_persistent_context(
        user_data_dir=brave_profile,
        executable_path=brave_exe,
        headless=False
    )

    page = browser.new_page()

    for user in users['username']:
        print("Scraping", user)

        page.goto(f"https://x.com/{user}", wait_until="domcontentloaded")
        page.wait_for_selector("article")
        time.sleep(6)

        seen_urls = set()
        reached_old = False

        while not reached_old:
            tweets = page.locator("article")
            count = tweets.count()

            for i in range(count):
                tweet_block = tweets.nth(i)

                try:
                    # Tweet URL
                    link_element = tweet_block.locator("a[href*='/status/']").first
                    tweet_url = link_element.get_attribute("href")
                    tweet_url = "https://x.com" + tweet_url

                    if tweet_url in seen_urls:
                        continue

                    seen_urls.add(tweet_url)

                    # Tweet time UTC → IST
                    time_element = tweet_block.locator("time").first
                    tweet_date_str = time_element.get_attribute("datetime")

                    tweet_utc = datetime.fromisoformat(tweet_date_str.replace("Z", "+00:00"))
                    tweet_ist = tweet_utc.astimezone(IST)

                    if tweet_ist.date() < yesterday_ist.date():
                        reached_old = True
                        break

                    # Tweet text
                    text_element = tweet_block.locator('div[data-testid="tweetText"]').first
                    tweet_text = text_element.inner_text()

                    # Tweet type
                    full_text = tweet_block.inner_text().lower()
                    if "reposted" in full_text:
                        tweet_type = "Retweet"
                    elif "quote" in full_text:
                        tweet_type = "Quote"
                    else:
                        tweet_type = "Tweet"

                    tweets_data.append([
                        user,
                        tweet_ist.strftime("%d-%m-%Y"),
                        tweet_ist.strftime("%H:%M"),
                        tweet_type,
                        tweet_text,
                        tweet_url
                    ])

                except:
                    pass

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