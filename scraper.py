import asyncio
import json
import os
import aiofiles
from datetime import datetime, timezone
import asyncpraw
from asyncpraw.models import MoreComments
from typing import Optional, Dict, Any

class SubredditScraper:
    def __init__(self, subreddit_name, target_date_str, job_id, logger, update_callback):
        self.subreddit_name = subreddit_name
        self.target_date = datetime.strptime(target_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        self.job_id = job_id
        self.logger = logger
        self.update_callback = update_callback
        self.is_running = True
        self.posts_scraped = 0
        self.comments_scraped = 0
        self.errors = 0
        self.scraped_data = {
            "scraped_at": datetime.now().isoformat(),
            "subreddit": subreddit_name,
            "date_range": {
                "start": target_date_str,
                "end": datetime.now().strftime("%Y-%m-%d")
            },
            "posts": []
        }
        
        # Initialize Reddit instance
        self.reddit = asyncpraw.Reddit(
            client_id=os.getenv("REDDIT_CLIENT_ID", "YOUR_CLIENT_ID"),
            client_secret=os.getenv("REDDIT_CLIENT_SECRET", "YOUR_CLIENT_SECRET"),
            user_agent="SubredditScraper/1.0 by /u/YourUsername"
        )
        
        # Cache for author info to reduce API calls
        self.author_cache = {}

    async def run(self):
        try:
            self.logger.info(f"Starting scrape for r/{self.subreddit_name} until {self.target_date.date()}")
            await self.update_callback("Starting scrape...", "info")
            
            subreddit = await self.reddit.subreddit(self.subreddit_name)
            
            # Reddit API has pagination limits. We'll iterate through as many posts as possible.
            # For 1M+ posts, this would require multiple strategies (time-based search, etc.)
            # This implementation handles the standard API approach efficiently.
            
            async for post in subreddit.new(limit=None):
                if not self.is_running:
                    self.logger.info("Scraping stopped by user")
                    break
                
                post_date = datetime.fromtimestamp(post.created_utc, tz=timezone.utc)
                
                if post_date < self.target_date:
                    self.logger.info(f"Reached target date: {post_date.date()}")
                    break
                
                await self.process_post(post)
                
                # Save progress every 10 posts
                if self.posts_scraped % 10 == 0:
                    await self.save_partial()
                    
        except Exception as e:
            self.logger.error(f"Scraping error: {str(e)}")
            await self.update_callback(f"Error: {str(e)}", "error")
            self.errors += 1
        finally:
            await self.save_final()
            await self.reddit.close()
            self.logger.info("Scraping finished.")

    async def process_post(self, post):
        try:
            # Fetch author info
            author_info = await self.get_author_info(post.author)
            
            post_data = {
                "post_id": post.id,
                "url": f"https://reddit.com{post.permalink}",
                "title": post.title,
                "body": post.selftext,
                "author": str(post.author) if post.author else "[deleted]",
                "created_utc": datetime.fromtimestamp(post.created_utc, tz=timezone.utc).isoformat(),
                "subreddit": post.subreddit.display_name,
                "flair": post.link_flair_text,
                "score": post.score,
                "upvote_ratio": post.upvote_ratio,
                "num_comments": post.num_comments,
                "awards": post.total_awards_received if hasattr(post, 'total_awards_received') else 0,
                "is_nsfw": post.over_18,
                "num_shares": 0,  # Not directly available via API
                "num_saves": 0,   # Not directly available via API
                "author_info": author_info,
                "comments": [],
                "comments_scraped_count": 0
            }
            
            # Fetch comments
            comments = await self.fetch_comments(post)
            post_data["comments"] = comments
            post_data["comments_scraped_count"] = len(comments)
            
            self.scraped_data["posts"].append(post_data)
            self.posts_scraped += 1
            self.comments_scraped += len(comments)
            
            await self.update_callback(f"Scraped: {post.title[:50]}...", "info")
            await self.update_callback({"posts": self.posts_scraped, "comments": self.comments_scraped, "errors": self.errors}, "stats")
            
        except Exception as e:
            self.logger.error(f"Error processing post {post.id}: {e}")
            self.errors += 1
            await self.update_callback({"posts": self.posts_scraped, "comments": self.comments_scraped, "errors": self.errors}, "stats")

    async def get_author_info(self, author) -> Dict[str, Any]:
        """Fetch author information with caching"""
        if author is None:
            return {
                "username": "[deleted]",
                "account_created_utc": None,
                "post_karma": 0,
                "comment_karma": 0,
                "total_karma": 0,
                "num_posts": 0,
                "num_comments": 0,
                "subreddits_participated_in": []
            }
        
        username = str(author)
        
        # Check cache
        if username in self.author_cache:
            return self.author_cache[username]
        
        try:
            # Fetch author details
            redditor = await self.reddit.redditor(username)
            
            author_data = {
                "username": username,
                "account_created_utc": datetime.fromtimestamp(redditor.created_utc, tz=timezone.utc).isoformat(),
                "post_karma": redditor.link_karma,
                "comment_karma": redditor.comment_karma,
                "total_karma": redditor.link_karma + redditor.comment_karma,
                "num_posts": 0,  # Would require iterating through submissions
                "num_comments": 0,  # Would require iterating through comments
                "subreddits_participated_in": []  # Would require complex analysis
            }
            
            # Cache the result
            self.author_cache[username] = author_data
            return author_data
            
        except Exception as e:
            self.logger.warning(f"Could not fetch author info for {username}: {e}")
            return {
                "username": username,
                "account_created_utc": None,
                "post_karma": 0,
                "comment_karma": 0,
                "total_karma": 0,
                "num_posts": 0,
                "num_comments": 0,
                "subreddits_participated_in": []
            }

    async def fetch_comments(self, post):
        """Fetch all comments from a post"""
        comments_data = []
        
        try:
            # Replace MoreComments objects (limit to avoid excessive API calls)
            # For production with 1M posts, you might want to limit this further
            await post.comments.replace_more(limit=5)
            
            # Recursively process all comments
            for comment in post.comments.list():
                if isinstance(comment, MoreComments):
                    continue
                
                comment_data = await self.process_comment(comment, post.id)
                if comment_data:
                    comments_data.append(comment_data)
                    
        except Exception as e:
            self.logger.error(f"Error fetching comments for post {post.id}: {e}")
        
        return comments_data

    async def process_comment(self, comment, post_id):
        """Process a single comment"""
        try:
            # Get author info
            author_info = await self.get_author_info(comment.author)
            
            # Determine depth (0 for top-level)
            depth = 0
            parent = comment.parent_id
            if not parent.startswith("t3_"):  # t3_ is post, t1_ is comment
                depth = 1  # Simplified depth calculation
            
            return {
                "comment_id": comment.id,
                "parent_id": comment.parent_id,
                "author": str(comment.author) if comment.author else "[deleted]",
                "body": comment.body,
                "created_utc": datetime.fromtimestamp(comment.created_utc, tz=timezone.utc).isoformat(),
                "score": comment.score,
                "depth": depth,
                "author_info": author_info
            }
        except Exception as e:
            self.logger.error(f"Error processing comment {comment.id}: {e}")
            return None

    async def save_partial(self):
        """Save partial progress to prevent data loss"""
        try:
            filename = f"data/{self.job_id}_partial.json"
            os.makedirs("data", exist_ok=True)
            async with aiofiles.open(filename, "w", encoding="utf-8") as f:
                await f.write(json.dumps(self.scraped_data, indent=2))
            self.logger.info(f"Saved partial progress: {self.posts_scraped} posts")
        except Exception as e:
            self.logger.error(f"Error saving partial data: {e}")

    async def save_final(self):
        """Save final scraped data"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            session_name = f"{self.subreddit_name}_{self.target_date.strftime('%Y%m%d')}"
            filename = f"data/{session_name}_{timestamp}.json"
            os.makedirs("data", exist_ok=True)
            
            async with aiofiles.open(filename, "w", encoding="utf-8") as f:
                await f.write(json.dumps(self.scraped_data, indent=2))
            
            self.logger.info(f"Saved final data to {filename}")
            await self.update_callback(f"Data saved to {filename}", "success")
            
            # Remove partial file if exists
            partial_file = f"data/{self.job_id}_partial.json"
            if os.path.exists(partial_file):
                os.remove(partial_file)
                
        except Exception as e:
            self.logger.error(f"Error saving final data: {e}")

    def stop(self):
        """Stop the scraping process"""
        self.is_running = False
        self.logger.info("Stop signal received")
