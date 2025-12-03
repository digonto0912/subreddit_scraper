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
        
        # HTTP client with custom headers
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        
        self.author_cache = {}
        self.last_request_time = 0
        self.min_request_interval = 1.0

    async def rate_limit(self):
        """Implement rate limiting"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < self.min_request_interval:
            await asyncio.sleep(self.min_request_interval - time_since_last_request)
        self.last_request_time = time.time()

    async def fetch_json(self, url: str, params: dict = None, retries: int = 5) -> Optional[dict]:
        """Fetch JSON with detailed logging and retry logic"""
        await self.rate_limit()
        backoff = 5.0
        
        for i in range(retries + 1):
            async with httpx.AsyncClient(headers=self.headers, timeout=30.0) as client:
                try:
                    self.logger.debug(f"Requesting: {url} | Params: {params} | Attempt: {i+1}/{retries+1}")
                    response = await client.get(url, params=params)
                    
                    # Log rate limit headers if present
                    remaining = response.headers.get('x-ratelimit-remaining')
                    reset = response.headers.get('x-ratelimit-reset')
                    if remaining:
                        self.logger.debug(f"Rate Limit: {remaining} remaining, reset in {reset}s")

                    if response.status_code == 200:
                        self.logger.info(f"Success: {url} | Status: 200 | Size: {len(response.content)} bytes")
                        return response.json()
                    
                    elif response.status_code == 429:
                        wait_time = backoff * (2 ** i)
                        self.logger.warning(f"Rate Limited (429): {url} | Waiting {wait_time}s")
                        await self.update_callback(f"Rate limited (429). Waiting {wait_time}s...", "warning")
                        if i < retries:
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            self.logger.error(f"Max retries exhausted for {url}")
                            return None
                    
                    else:
                        self.logger.error(f"HTTP Error: {url} | Status: {response.status_code} | Body: {response.text[:200]}")
                        if i < retries:
                            await asyncio.sleep(2)
                            continue
                        return None

                except Exception as e:
                    self.logger.error(f"Exception fetching {url}: {str(e)}")
                    if i < retries:
                        await asyncio.sleep(2)
                        continue
                    return None
        return None

    async def run(self):
        try:
            self.logger.info(f"Starting scrape for r/{self.subreddit_name}")
            await self.update_callback("Starting scraper...", "info")
            
            base_url = f"https://www.reddit.com/r/{self.subreddit_name}/new.json"
            after = None
            reached_target = False
            
            while self.is_running and not reached_target:
                params = {'limit': 100}
                if after:
                    params['after'] = after
                
                self.logger.info(f"Fetching batch. After: {after}")
                data = await self.fetch_json(base_url, params)
                
                if not data or 'data' not in data:
                    self.logger.warning("Invalid data received or no data")
                    break
                
                posts = data['data']['children']
                after = data['data'].get('after')
                
                if not posts:
                    self.logger.info("No posts in response")
                    break
                
                self.logger.info(f"Processing {len(posts)} posts in batch")
                
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
                    
                    if self.posts_scraped % 10 == 0:
                        await self.save_partial()
                
                if not after:
                    self.logger.info("No 'after' token - reached end of feed")
                    break
                    
        except Exception as e:
            self.logger.critical(f"Critical Scraper Error: {str(e)}")
            await self.update_callback(f"Critical Error: {str(e)}", "error")
        finally:
            await self.save_final()

    async def process_post(self, post: dict):
        try:
            post_id = post.get('id')
            permalink = post.get('permalink')
            self.logger.info(f"Processing Post: {post_id} | {post.get('title')[:30]}...")
            
            author_info = await self.get_author_info(post.get('author'))
            
            post_data = {
                "post_id": post_id,
                "url": f"https://reddit.com{permalink}",
                "title": post.get('title'),
                "body": post.get('selftext'),
                "author": post.get('author'),
                "created_utc": datetime.fromtimestamp(post.get('created_utc', 0), tz=timezone.utc).isoformat(),
                "subreddit": post.get('subreddit'),
                "score": post.get('score'),
                "num_comments": post.get('num_comments'),
                "author_info": author_info,
                "comments": []
            }
            
            if post.get('num_comments', 0) > 0:
                comments = await self.fetch_comments(post_id, permalink)
                post_data["comments"] = comments
            
            self.scraped_data["posts"].append(post_data)
            self.posts_scraped += 1
            self.comments_scraped += len(post_data["comments"])
            
            await self.update_callback({
                "posts": self.posts_scraped, 
                "comments": self.comments_scraped, 
                "errors": self.errors
            }, "stats")
            
        except Exception as e:
            self.logger.error(f"Error processing post {post.get('id')}: {e}")
            self.errors += 1

    async def get_author_info(self, author_name: str) -> Dict[str, Any]:
        if not author_name or author_name == '[deleted]':
            return {"username": "[deleted]"}
        
        if author_name in self.author_cache:
            return self.author_cache[author_name]
            
        url = f"https://www.reddit.com/user/{author_name}/about.json"
        data = await self.fetch_json(url)
        
        if data and 'data' in data:
            self.author_cache[author_name] = data['data']
            return data['data']
        return {"username": author_name}

    async def fetch_comments(self, post_id: str, permalink: str) -> List[Dict]:
        url = f"https://www.reddit.com{permalink}.json"
        data = await self.fetch_json(url, params={'limit': 500})
        if not data or len(data) < 2:
            return []
        return self.extract_comments(data[1]['data']['children'])

    def extract_comments(self, children: List) -> List[Dict]:
        comments = []
        for child in children:
            if child['kind'] == 't1':
                data = child['data']
                comment = {
                    "id": data.get('id'),
                    "author": data.get('author'),
                    "body": data.get('body'),
                    "score": data.get('score'),
                    "created_utc": datetime.fromtimestamp(data.get('created_utc', 0), tz=timezone.utc).isoformat(),
                    "replies": []
                }
                if data.get('replies'):
                    comment['replies'] = self.extract_comments(data['replies']['data']['children'])
                comments.append(comment)
        return comments

    async def save_partial(self):
        filename = f"data/{self.job_id}_partial.json"
        os.makedirs("data", exist_ok=True)
        async with aiofiles.open(filename, "w", encoding="utf-8") as f:
            await f.write(json.dumps(self.scraped_data, indent=2))

    async def save_final(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"data/{self.subreddit_name}_{timestamp}.json"
        os.makedirs("data", exist_ok=True)
        async with aiofiles.open(filename, "w", encoding="utf-8") as f:
            await f.write(json.dumps(self.scraped_data, indent=2))
        self.logger.info(f"Saved final data to {filename}")
        await self.update_callback(f"Saved to {filename}", "success")

    def stop(self):
        self.is_running = False
