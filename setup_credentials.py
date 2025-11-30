"""
Reddit API Credentials Setup Helper
Run this script to set your credentials and test them.
"""

import os
import sys

def set_credentials():
    print("=" * 60)
    print("Reddit API Credentials Setup")
    print("=" * 60)
    print("\nFirst, get your credentials from: https://www.reddit.com/prefs/apps")
    print("Create a 'script' type app if you haven't already.\n")
    
    client_id = input("Enter your Reddit CLIENT_ID: ").strip()
    client_secret = input("Enter your Reddit CLIENT_SECRET: ").strip()
    
    if not client_id or not client_secret:
        print("\n❌ Error: Both CLIENT_ID and CLIENT_SECRET are required!")
        return False
    
    # Set environment variables for current session
    os.environ['REDDIT_CLIENT_ID'] = client_id
    os.environ['REDDIT_CLIENT_SECRET'] = client_secret
    
    print("\n✅ Credentials set for current session!")
    print("\nTo make these permanent, run these commands in PowerShell:")
    print(f'$env:REDDIT_CLIENT_ID="{client_id}"')
    print(f'$env:REDDIT_CLIENT_SECRET="{client_secret}"')
    
    return True

def test_credentials():
    print("\n" + "=" * 60)
    print("Testing Reddit API Connection")
    print("=" * 60)
    
    try:
        import asyncpraw
        import asyncio
        
        async def test():
            reddit = asyncpraw.Reddit(
                client_id=os.getenv("REDDIT_CLIENT_ID", "YOUR_CLIENT_ID"),
                client_secret=os.getenv("REDDIT_CLIENT_SECRET", "YOUR_CLIENT_SECRET"),
                user_agent="SubredditScraper/1.0 Test"
            )
            
            try:
                # Try to access a subreddit
                subreddit = await reddit.subreddit("python")
                print(f"\n✅ Successfully connected to Reddit API!")
                print(f"✅ Test subreddit: r/{subreddit.display_name}")
                
                # Get one post to verify
                async for post in subreddit.new(limit=1):
                    print(f"✅ Successfully fetched post: {post.title[:50]}...")
                    break
                
                await reddit.close()
                return True
                
            except Exception as e:
                print(f"\n❌ Error connecting to Reddit API: {e}")
                await reddit.close()
                return False
        
        result = asyncio.run(test())
        return result
        
    except ImportError:
        print("\n❌ asyncpraw not installed. Run: pip install asyncpraw")
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("\n🔧 Reddit API Setup Helper\n")
    
    # Check if credentials are already set
    existing_id = os.getenv("REDDIT_CLIENT_ID")
    existing_secret = os.getenv("REDDIT_CLIENT_SECRET")
    
    if existing_id and existing_secret and existing_id != "YOUR_CLIENT_ID":
        print(f"Found existing credentials:")
        print(f"  CLIENT_ID: {existing_id[:10]}...")
        print(f"  CLIENT_SECRET: {existing_secret[:10]}...")
        
        choice = input("\nDo you want to test these credentials? (y/n): ").strip().lower()
        if choice == 'y':
            if test_credentials():
                print("\n✅ Your credentials are working! You can now run the scraper.")
                sys.exit(0)
            else:
                print("\n❌ Credentials test failed. Let's set new ones.")
    
    # Set new credentials
    if set_credentials():
        print("\n" + "=" * 60)
        choice = input("\nDo you want to test the credentials now? (y/n): ").strip().lower()
        if choice == 'y':
            if test_credentials():
                print("\n✅ Setup complete! You can now run the scraper.")
                print("\nNext steps:")
                print("1. Restart the server: python main.py")
                print("2. Open http://localhost:8000")
                print("3. Start scraping!")
            else:
                print("\n❌ Credentials test failed. Please check your CLIENT_ID and CLIENT_SECRET.")
        else:
            print("\n⚠️  Remember to restart the server after setting credentials!")
    else:
        print("\n❌ Setup failed. Please try again.")
