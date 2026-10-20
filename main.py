import argparse
import sys
from src.config import ensure_dirs, SESSION_FILE, DEFAULT_INPUT_FILE, X_USERNAME, X_PASSWORD, LOOKBACK_DAYS, TIMELINE_MAX_TWEETS
from src.login import run_login_manual, run_login_auto
from src.scraper import run_profile_scraper
from src.timeline_scraper import run_timeline_scraper

def run_full_pipeline():
    """
    Runs the entire scraping process sequentially:
    1. Logs in (automated if credentials exist, otherwise manual browser window).
    2. Scrapes target profiles from users.csv (including replies and threads).
    3. Scrapes the home timeline feed (including replies and threads).
    """
    print("\n==================================================")
    print("RUNNING TWITTER/X SCRAPER PIPELINE")
    print("==================================================")

    # 1. Login check
    if not SESSION_FILE.exists():
        print("\n[Step 1/3] Session not found. Initiating login process...")
        if X_USERNAME and X_PASSWORD:
            run_login_auto()
        else:
            run_login_manual()
        
        # Verify if session was created
        if not SESSION_FILE.exists():
            print("Error: Login was not completed successfully. Aborting scraping pipeline.")
            sys.exit(1)
    else:
        print(f"\n[Step 1/3] Active session found at: {SESSION_FILE}")

    # 2. Scrape Profiles
    if DEFAULT_INPUT_FILE.exists():
        print("\n[Step 2/3] Scraping target profiles (including replies and threads)...")
        run_profile_scraper(
            include_replies=True,
            include_threads=True,
            headless=True,
            lookback_days=LOOKBACK_DAYS
        )
    else:
        print(f"\n[Step 2/3] Target profiles list not found at: {DEFAULT_INPUT_FILE}")
        print("Skipping profile scraping.")

    # 3. Scrape Home Timeline Feed
    print("\n[Step 3/3] Scraping Home timeline feed (including replies and threads)...")
    run_timeline_scraper(
        include_replies=True,
        include_threads=True,
        headless=True,
        max_tweets=TIMELINE_MAX_TWEETS,
        lookback_days=LOOKBACK_DAYS
    )

    print("\n==================================================")
    print("PIPELINE COMPLETED SUCCESSFULLY")
    print("All scraped tweets have been merged and saved.")
    print("==================================================")

def main():
    # Make sure workspace directories exist
    ensure_dirs()

    parser = argparse.ArgumentParser(
        description="Twitter/X Playwright-based Scraper CLI",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Login command
    login_parser = subparsers.add_parser("login", help="Log in to X/Twitter and save authentication state")
    login_group = login_parser.add_mutually_exclusive_group(required=True)
    login_group.add_argument("--manual", action="store_true", help="Log in manually via visible browser window")
    login_group.add_argument("--auto", action="store_true", help="Log in automatically using credentials from .env")

    # Scrape command
    scrape_parser = subparsers.add_parser("scrape", help="Scrape profiles and/or timeline feed")
    
    # Sources
    scrape_parser.add_argument("--profiles", action="store_true", help="Scrape target profiles list")
    scrape_parser.add_argument("--timeline", action="store_true", help="Scrape your logged-in home timeline feed")
    
    # Content Filters / Options
    scrape_parser.add_argument("--input", "-i", type=str, help="Path to input CSV containing usernames (profile scrape only)")
    scrape_parser.add_argument("--output", "-o", type=str, help="Path to output CSV")
    scrape_parser.add_argument("--lookback", "-l", type=int, default=LOOKBACK_DAYS, help="Number of lookback days (profiles/threads only)")
    scrape_parser.add_argument("--limit", type=int, default=TIMELINE_MAX_TWEETS, help="Max tweets to scrape (home timeline only)")
    scrape_parser.add_argument("--include-replies", action="store_true", help="Include reply tweets and replies tab")
    scrape_parser.add_argument("--include-threads", action="store_true", help="Follow tweets and extract user's thread continuations")
    
    # Browser Config
    scrape_parser.add_argument("--show-browser", action="store_true", help="Run browser in visible mode (default is headless)")

    args = parser.parse_args()

    # If no subcommand is specified, default to running the full sequential pipeline
    if not args.command:
        run_full_pipeline()
        return

    if args.command == "login":
        if args.auto:
            run_login_auto()
        else:
            run_login_manual()

    elif args.command == "scrape":
        headless = not args.show_browser
        scrape_profiles = args.profiles
        scrape_timeline = args.timeline
        if not scrape_profiles and not scrape_timeline:
            scrape_profiles = True

        if scrape_profiles:
            print("\n=== Running Profile Scraper ===")
            run_profile_scraper(
                input_file=args.input,
                output_file=args.output,
                lookback_days=args.lookback,
                include_replies=args.include_replies,
                include_threads=args.include_threads,
                headless=headless
            )

        if scrape_timeline:
            print("\n=== Running Home Timeline Scraper ===")
            run_timeline_scraper(
                output_file=args.output,
                max_tweets=args.limit,
                lookback_days=args.lookback,
                include_replies=args.include_replies,
                include_threads=args.include_threads,
                headless=headless
            )

if __name__ == "__main__":
    main()
