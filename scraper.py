import asyncio
import json
import os
import aiofiles
from datetime import datetime, timezone
import httpx
from typing import Optional, Dict, Any, List
import time

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
        
        # HTTP client with custom headers to avoid rate limiting
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        
        # Cache for author info to reduce requests
        self.author_cache = {}
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 1.0  # 1 second between requests

    async def rate_limit(self):
        """Implement rate limiting to avoid being blocked"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < self.min_request_interval:
            await asyncio.sleep(self.min_request_interval - time_since_last_request)
        self.last_request_time = time.time()

    async def fetch_json(self, url: str, params: dict = None) -> Optional[dict]:
        """Fetch JSON data from Reddit"""
        await self.rate_limit()
        
        async with httpx.AsyncClient(headers=self.headers, timeout=30.0) as client:
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                self.logger.error(f"Error fetching {url}: {e}")
                return None

    async def run(self):
        try:
            self.logger.info(f"Starting scrape for r/{self.subreddit_name} until {self.target_date.date()}")
            await self.update_callback("Starting custom scraper (no API required)...", "info")
            
            # Reddit's JSON endpoint for new posts
            base_url = f"https://www.reddit.com/r/{self.subreddit_name}/new.json"
            after = None
            reached_target = False
            
            while self.is_running and not reached_target:
                # Fetch posts
                params = {'limit': 100}
                if after:
                    params['after'] = after
                
                data = await self.fetch_json(base_url, params)
                
                if not data or 'data' not in data:
                    self.logger.warning("No more data available")
                    break
                
                posts = data['data']['children']
                after = data['data'].get('after')
                
                if not posts:
                    self.logger.info("No more posts found")
                    break
                
                for post_data in posts:
                    if not self.is_running:
                        break
                    
                    post = post_data['data']
                    post_date = datetime.fromtimestamp(post['created_utc'], tz=timezone.utc)
                    
                    if post_date < self.target_date:
                        self.logger.info(f"Reached target date: {post_date.date()}")
                        reached_target = True
                        break
                    
                    await self.process_post(post)
                    
                    # Save progress every 10 posts
                    if self.posts_scraped % 10 == 0:
                        await self.save_partial()
                
                if not after:
                    self.logger.info("Reached end of available posts")
                    break
                
                await self.update_callback(f"Fetching more posts... (after: {after[:20]}...)", "info")
                    
        except Exception as e:
            self.logger.error(f"Scraping error: {str(e)}")
            await self.update_callback(f"Error: {str(e)}", "error")
            self.errors += 1
        finally:
            await self.save_final()
            self.logger.info("Scraping finished.")

    async def process_post(self, post: dict):
        try:
            # Extract post data
            post_id = post.get('id', '')
            permalink = post.get('permalink', '')
            
            # Get author info
            author_name = post.get('author', '[deleted]')
            author_info = await self.get_author_info(author_name)
            
            post_data = {
                "post_id": post_id,
                "url": f"https://reddit.com{permalink}",
                "title": post.get('title', ''),
                "body": post.get('selftext', ''),
                "author": author_name,
                "created_utc": datetime.fromtimestamp(post.get('created_utc', 0), tz=timezone.utc).isoformat(),
                "subreddit": post.get('subreddit', self.subreddit_name),
                "flair": post.get('link_flair_text'),
                "score": post.get('score', 0),
                "upvote_ratio": post.get('upvote_ratio', 0.0),
                "num_comments": post.get('num_comments', 0),
                "awards": post.get('total_awards_received', 0),
                "is_nsfw": post.get('over_18', False),
                "num_shares": 0,  # Not available in JSON
                "num_saves": 0,   # Not available in JSON
                "author_info": author_info,
                "comments": [],
                "comments_scraped_count": 0
            }
            
            # Fetch comments
            if post.get('num_comments', 0) > 0:
                comments = await self.fetch_comments(post_id, permalink)
                post_data["comments"] = comments
                post_data["comments_scraped_count"] = len(comments)
            
            self.scraped_data["posts"].append(post_data)
            self.posts_scraped += 1
            self.comments_scraped += post_data["comments_scraped_count"]
            
            await self.update_callback(f"Scraped: {post_data['title'][:50]}...", "info")
            await self.update_callback({
                "posts": self.posts_scraped, 
                "comments": self.comments_scraped, 
                "errors": self.errors
            }, "stats")
            
        except Exception as e:
            self.logger.error(f"Error processing post: {e}")
            self.errors += 1
            await self.update_callback({
                "posts": self.posts_scraped, 
                "comments": self.comments_scraped, 
                "errors": self.errors
            }, "stats")

    async def get_author_info(self, author_name: str) -> Dict[str, Any]:
        """Fetch author information from Reddit's JSON endpoint"""
        if author_name == '[deleted]' or not author_name:
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
        
        # Check cache
        if author_name in self.author_cache:
            return self.author_cache[author_name]
        
        try:
            url = f"https://www.reddit.com/user/{author_name}/about.json"
            data = await self.fetch_json(url)
            
            if data and 'data' in data:
                user = data['data']
                author_data = {
                    "username": author_name,
                    "account_created_utc": datetime.fromtimestamp(user.get('created_utc', 0), tz=timezone.utc).isoformat(),
                    "post_karma": user.get('link_karma', 0),
                    "comment_karma": user.get('comment_karma', 0),
                    "total_karma": user.get('total_karma', user.get('link_karma', 0) + user.get('comment_karma', 0)),
                    "num_posts": 0,  # Would require additional requests
                    "num_comments": 0,  # Would require additional requests
                    "subreddits_participated_in": []  # Would require additional requests
                }
                
                # Cache the result
                self.author_cache[author_name] = author_data
                return author_data
            
        except Exception as e:
            self.logger.warning(f"Could not fetch author info for {author_name}: {e}")
        
        # Return default if fetch failed
        default_data = {
            "username": author_name,
            "account_created_utc": None,
            "post_karma": 0,
            "comment_karma": 0,
            "total_karma": 0,
            "num_posts": 0,
            "num_comments": 0,
            "subreddits_participated_in": []
        }
        self.author_cache[author_name] = default_data
        return default_data

    async def fetch_comments(self, post_id: str, permalink: str) -> List[Dict]:
        """Fetch all comments for a post"""
        comments_data = []
        
        try:
            url = f"https://www.reddit.com{permalink}.json"
            data = await self.fetch_json(url, params={'limit': 500})
            
            if not data or len(data) < 2:
                return comments_data
            
            # Comments are in the second element
            comments_listing = data[1]['data']['children']
            
            for comment_item in comments_listing:
                if comment_item['kind'] == 'more':
                    continue  # Skip "load more comments" items
                
                comment = comment_item['data']
                comment_data = await self.process_comment(comment)
                if comment_data:
                    comments_data.append(comment_data)
                    
                    # Process replies recursively
                    if 'replies' in comment and comment['replies']:
                        replies = await self.process_replies(comment['replies'])
                        comments_data.extend(replies)
                        
        except Exception as e:
            self.logger.error(f"Error fetching comments for post {post_id}: {e}")
        
        return comments_data

    async def process_replies(self, replies_data) -> List[Dict]:
        """Process nested comment replies"""
        replies = []
        
        if isinstance(replies_data, dict) and 'data' in replies_data:
            children = replies_data['data'].get('children', [])
            
            for reply_item in children:
                if reply_item['kind'] == 'more':
                    continue
                
                reply = reply_item['data']
                reply_data = await self.process_comment(reply)
                if reply_data:
                    replies.append(reply_data)
                    
                    # Process nested replies
                    if 'replies' in reply and reply['replies']:
                        nested_replies = await self.process_replies(reply['replies'])
                        replies.extend(nested_replies)
        
        return replies

    async def process_comment(self, comment: dict) -> Optional[Dict]:
        """Process a single comment"""
        try:
            author_name = comment.get('author', '[deleted]')
            author_info = await self.get_author_info(author_name)
            
            # Calculate depth based on parent
            parent_id = comment.get('parent_id', '')
            depth = 0
            if parent_id and not parent_id.startswith('t3_'):  # t3_ is post, t1_ is comment
                depth = comment.get('depth', 0)
            
            return {
                "comment_id": comment.get('id', ''),
                "parent_id": parent_id,
                "author": author_name,
                "body": comment.get('body', ''),
                "created_utc": datetime.fromtimestamp(comment.get('created_utc', 0), tz=timezone.utc).isoformat(),
                "score": comment.get('score', 0),
                "depth": depth,
                "author_info": author_info
            }
        except Exception as e:
            self.logger.error(f"Error processing comment: {e}")
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
