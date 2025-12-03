"""
Streaming Coordinator - Continuously collect post lists and distribute to workers
"""
import asyncio
import httpx
import json
from datetime import datetime, timezone
from typing import List, Dict
import aiofiles

class StreamingCoordinator:
    def __init__(self, subreddit: str, target_date_str: str, num_workers: int = 25):
        self.subreddit = subreddit
        self.target_date = datetime.strptime(target_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        self.num_workers = num_workers
        
        # Queue for distributing posts to workers
        self.post_queue = asyncio.Queue(maxsize=1000)
        self.is_collecting = True
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
        }
        
        # Statistics
        self.posts_collected = 0
        self.posts_processed = 0
        
    async def collect_post_lists(self):
        """Continuously fetch post lists and add to queue"""
        print(f"[Collector] Starting to collect posts from r/{self.subreddit}")
        
        base_url = f"https://www.reddit.com/r/{self.subreddit}/new.json"
        after = None
        
        async with httpx.AsyncClient(headers=self.headers, timeout=30.0) as client:
            while self.is_collecting:
                try:
                    params = {'limit': 100}
                    if after:
                        params['after'] = after
                    
                    # Fetch 100 posts (~2 seconds)
                    response = await client.get(base_url, params=params)
                    data = response.json()
                    
                    posts = data['data']['children']
                    after = data['data'].get('after')
                    
                    if not posts:
                        print("[Collector] No more posts available")
                        break
                    
                    # Check if we've reached target date
                    for post_data in posts:
                        post = post_data['data']
                        post_date = datetime.fromtimestamp(post['created_utc'], tz=timezone.utc)
                        
                        if post_date < self.target_date:
                            print(f"[Collector] Reached target date: {post_date.date()}")
                            self.is_collecting = False
                            break
                        
                        # Add post info to queue for workers
                        post_info = {
                            'id': post['id'],
                            'permalink': post['permalink'],
                            'created_utc': post['created_utc'],
                            'num_comments': post.get('num_comments', 0)
                        }
                        
                        await self.post_queue.put(post_info)
                        self.posts_collected += 1
                    
                    if self.posts_collected % 100 == 0:
                        print(f"[Collector] Collected {self.posts_collected} posts, Queue size: {self.post_queue.qsize()}")
                    
                    if not after:
                        print("[Collector] Reached end of available posts")
                        break
                    
                    # Small delay for rate limiting
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    print(f"[Collector] Error: {e}")
                    await asyncio.sleep(2)
        
        # Signal workers that collection is done
        self.is_collecting = False
        print(f"[Collector] Finished! Total posts collected: {self.posts_collected}")
    
    async def worker_process_posts(self, worker_id: int):
        """Worker that processes posts from the queue"""
        print(f"[Worker {worker_id}] Started")
        
        worker_data = {
            "worker_id": worker_id,
            "scraped_at": datetime.now().isoformat(),
            "subreddit": self.subreddit,
            "posts": []
        }
        
        async with httpx.AsyncClient(headers=self.headers, timeout=30.0) as client:
            while True:
                try:
                    # Get post from queue (with timeout)
                    try:
                        post_info = await asyncio.wait_for(
                            self.post_queue.get(), 
                            timeout=5.0
                        )
                    except asyncio.TimeoutError:
                        # Check if collector is done
                        if not self.is_collecting and self.post_queue.empty():
                            print(f"[Worker {worker_id}] No more posts, finishing...")
                            break
                        continue
                    
                    # Fetch full post details
                    url = f"https://www.reddit.com{post_info['permalink']}.json"
                    response = await client.get(url, params={'limit': 500, 'depth': 10})
                    data = response.json()
                    
                    # Extract post data
                    post = data[0]['data']['children'][0]['data']
                    
                    post_data = {
                        "post_id": post['id'],
                        "url": f"https://reddit.com{post['permalink']}",
                        "title": post.get('title', ''),
                        "body": post.get('selftext', ''),
                        "author": post.get('author', '[deleted]'),
                        "created_utc": datetime.fromtimestamp(post['created_utc'], tz=timezone.utc).isoformat(),
                        "subreddit": post.get('subreddit', self.subreddit),
                        "flair": post.get('link_flair_text'),
                        "score": post.get('score', 0),
                        "upvote_ratio": post.get('upvote_ratio', 0.0),
                        "num_comments": post.get('num_comments', 0),
                        "awards": post.get('total_awards_received', 0),
                        "is_nsfw": post.get('over_18', False),
                        "comments": [],
                        "comments_scraped_count": 0
                    }
                    
                    # Extract comments if available
                    if len(data) > 1 and post.get('num_comments', 0) > 0:
                        comments = self.extract_comments(data[1]['data']['children'])
                        post_data['comments'] = comments
                        post_data['comments_scraped_count'] = len(comments)
                    
                    worker_data['posts'].append(post_data)
                    self.posts_processed += 1
                    
                    # Save progress every 10 posts
                    if len(worker_data['posts']) % 10 == 0:
                        await self.save_worker_data(worker_id, worker_data)
                        print(f"[Worker {worker_id}] Processed {len(worker_data['posts'])} posts")
                    
                    # Rate limiting
                    await asyncio.sleep(1.0)
                    
                except Exception as e:
                    print(f"[Worker {worker_id}] Error processing post: {e}")
                    continue
        
        # Final save
        await self.save_worker_data(worker_id, worker_data)
        print(f"[Worker {worker_id}] Finished! Processed {len(worker_data['posts'])} posts")
    
    def extract_comments(self, comments_data: List) -> List[Dict]:
        """Extract comments from Reddit data structure"""
        comments = []
        
        for comment_item in comments_data:
            if comment_item['kind'] == 'more':
                continue  # Skip "load more" for now
            
            if comment_item['kind'] != 't1':
                continue
            
            comment = comment_item['data']
            
            comment_data = {
                "comment_id": comment.get('id', ''),
                "parent_id": comment.get('parent_id', ''),
                "author": comment.get('author', '[deleted]'),
                "body": comment.get('body', ''),
                "created_utc": datetime.fromtimestamp(comment.get('created_utc', 0), tz=timezone.utc).isoformat(),
                "score": comment.get('score', 0),
                "depth": 0
            }
            
            comments.append(comment_data)
            
            # Process replies recursively
            if 'replies' in comment and comment['replies']:
                if isinstance(comment['replies'], dict):
                    replies = self.extract_comments(comment['replies']['data']['children'])
                    comments.extend(replies)
        
        return comments
    
    async def save_worker_data(self, worker_id: int, data: Dict):
        """Save worker data to file"""
        import os
        os.makedirs('data', exist_ok=True)
        
        filename = f"data/worker_{worker_id}_{self.subreddit}_partial.json"
        async with aiofiles.open(filename, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(data, indent=2))
    
    async def monitor_progress(self):
        """Monitor and display progress"""
        while self.is_collecting or not self.post_queue.empty():
            await asyncio.sleep(5)
            print(f"\n[Monitor] Collected: {self.posts_collected} | Processed: {self.posts_processed} | Queue: {self.post_queue.qsize()}")
    
    async def run(self):
        """Run the streaming coordinator"""
        print(f"Starting streaming scraper with {self.num_workers} workers")
        print(f"Subreddit: r/{self.subreddit}")
        print(f"Target date: {self.target_date.date()}\n")
        
        # Start collector task
        collector_task = asyncio.create_task(self.collect_post_lists())
        
        # Start worker tasks
        worker_tasks = [
            asyncio.create_task(self.worker_process_posts(i))
            for i in range(self.num_workers)
        ]
        
        # Start monitor task
        monitor_task = asyncio.create_task(self.monitor_progress())
        
        # Wait for collector to finish
        await collector_task
        
        # Wait for all workers to finish processing queue
        await asyncio.gather(*worker_tasks)
        
        # Stop monitor
        monitor_task.cancel()
        
        print(f"\n✅ All done! Total posts processed: {self.posts_processed}")
        print(f"Check data/worker_*_{self.subreddit}_partial.json for results")

async def main():
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python streaming_coordinator.py <subreddit> <target_date> [num_workers]")
        print("Example: python streaming_coordinator.py python 2024-01-01 25")
        sys.exit(1)
    
    subreddit = sys.argv[1]
    target_date = sys.argv[2]
    num_workers = int(sys.argv[3]) if len(sys.argv) > 3 else 25
    
    coordinator = StreamingCoordinator(subreddit, target_date, num_workers)
    await coordinator.run()

if __name__ == "__main__":
    asyncio.run(main())
