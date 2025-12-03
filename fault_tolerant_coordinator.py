"""
Fault-Tolerant Streaming Coordinator with Auto-Recovery
Tracks worker progress, detects failures, and automatically restarts failed workers
"""
import asyncio
import httpx
import json
from datetime import datetime, timezone
from typing import List, Dict, Optional, Callable, Any
import aiofiles
import os
from dataclasses import dataclass, asdict
from enum import Enum

class WorkerStatus(Enum):
    IDLE = "idle"
    WORKING = "working"
    FAILED = "failed"
    COMPLETED = "completed"

@dataclass
class WorkItem:
    """Represents a single post to be processed"""
    post_id: str
    permalink: str
    created_utc: float
    num_comments: int
    batch_id: int
    item_index: int  # Position within batch

@dataclass
class WorkerState:
    """Tracks worker state and progress"""
    worker_id: int
    status: WorkerStatus
    current_item: Optional[WorkItem] = None
    items_processed: int = 0
    items_failed: int = 0
    last_heartbeat: float = 0
    reserved_batch: Optional[int] = None  # Next batch reserved for this worker
    
class FaultTolerantCoordinator:
    def __init__(self, subreddit: str, target_date_str: str, job_id: str, logger, update_callback: Callable[[Any, str], Any], num_workers: int = 25):
        self.subreddit = subreddit
        self.target_date = datetime.strptime(target_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        self.job_id = job_id
        self.logger = logger
        self.update_callback = update_callback
        self.num_workers = num_workers
        
        # Work distribution
        self.work_queue = asyncio.Queue(maxsize=2000)
        self.is_collecting = True
        self.current_batch_id = 0
        self.is_running = True
        
        # Worker management
        self.workers: Dict[int, WorkerState] = {}
        self.worker_tasks: Dict[int, asyncio.Task] = {}
        
        # Progress tracking
        self.checkpoint_dir = "checkpoints"
        os.makedirs(self.checkpoint_dir, exist_ok=True)
        os.makedirs("data", exist_ok=True)
        
        # Statistics
        self.total_items_collected = 0
        self.total_items_processed = 0
        self.total_items_failed = 0
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
        }
        
        # Heartbeat monitoring
        self.heartbeat_timeout = 30.0  # 30 seconds
        
    async def save_checkpoint(self, worker_id: int, item: WorkItem):
        """Save worker checkpoint for recovery"""
        checkpoint = {
            'worker_id': worker_id,
            'timestamp': datetime.now().isoformat(),
            'current_item': asdict(item),
            'items_processed': self.workers[worker_id].items_processed,
        }
        
        checkpoint_file = f"{self.checkpoint_dir}/worker_{worker_id}_checkpoint.json"
        async with aiofiles.open(checkpoint_file, 'w') as f:
            await f.write(json.dumps(checkpoint, indent=2))
    
    async def load_checkpoint(self, worker_id: int) -> Optional[WorkItem]:
        """Load worker checkpoint if exists"""
        checkpoint_file = f"{self.checkpoint_dir}/worker_{worker_id}_checkpoint.json"
        
        if not os.path.exists(checkpoint_file):
            return None
        
        try:
            async with aiofiles.open(checkpoint_file, 'r') as f:
                content = await f.read()
                checkpoint = json.loads(content)
                
                item_data = checkpoint['current_item']
                return WorkItem(**item_data)
        except Exception as e:
            self.logger.error(f"[Recovery] Error loading checkpoint for worker {worker_id}: {e}")
            return None
    
    async def fetch_json_with_retry(self, client: httpx.AsyncClient, url: str, params: dict = None, retries: int = 3) -> Optional[dict]:
        """Fetch JSON data with exponential backoff for 429 errors"""
        backoff = 2.0
        
        for i in range(retries + 1):
            try:
                response = await client.get(url, params=params)
                
                if response.status_code == 429:
                    if i < retries:
                        wait_time = backoff * (2 ** i)
                        self.logger.warning(f"Rate limited (429). Waiting {wait_time}s before retry {i+1}/{retries}...")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        self.logger.error(f"Max retries reached for {url}")
                        return None
                        
                response.raise_for_status()
                return response.json()
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    if i < retries:
                        wait_time = backoff * (2 ** i)
                        self.logger.warning(f"Rate limited (429). Waiting {wait_time}s before retry {i+1}/{retries}...")
                        await asyncio.sleep(wait_time)
                        continue
                self.logger.error(f"HTTP error fetching {url}: {e}")
                return None
            except Exception as e:
                self.logger.error(f"Error fetching {url}: {e}")
                if i < retries:
                    await asyncio.sleep(1)
                    continue
                return None
        return None

    async def collect_post_lists(self):
        """Continuously fetch post lists and create work items"""
        self.logger.info(f"[Collector] Starting to collect posts from r/{self.subreddit}")
        await self.update_callback(f"Collector started for r/{self.subreddit}", "info")
        
        base_url = f"https://www.reddit.com/r/{self.subreddit}/new.json"
        after = None
        item_index = 0
        
        async with httpx.AsyncClient(headers=self.headers, timeout=30.0) as client:
            while self.is_collecting and self.is_running:
                try:
                    params = {'limit': 100}
                    if after:
                        params['after'] = after
                    
                    data = await self.fetch_json_with_retry(client, base_url, params)
                    
                    if not data:
                        self.logger.warning("[Collector] Failed to fetch data after retries")
                        await asyncio.sleep(5) # Wait a bit longer before trying again loop
                        continue

                    if 'data' not in data or 'children' not in data['data']:
                        self.logger.warning(f"[Collector] Unexpected response format: {data.keys()}")
                        break

                    posts = data['data']['children']
                    after = data['data'].get('after')
                    
                    if not posts:
                        break
                    
                    # Create work items for this batch
                    batch_items = []
                    for post_data in posts:
                        post = post_data['data']
                        post_date = datetime.fromtimestamp(post['created_utc'], tz=timezone.utc)
                        
                        if post_date < self.target_date:
                            self.is_collecting = False
                            break
                        
                        work_item = WorkItem(
                            post_id=post['id'],
                            permalink=post['permalink'],
                            created_utc=post['created_utc'],
                            num_comments=post.get('num_comments', 0),
                            batch_id=self.current_batch_id,
                            item_index=item_index
                        )
                        
                        batch_items.append(work_item)
                        item_index += 1
                    
                    # Add items to queue
                    for item in batch_items:
                        await self.work_queue.put(item)
                        self.total_items_collected += 1
                    
                    self.current_batch_id += 1
                    
                    if self.total_items_collected % 100 == 0:
                        msg = f"Collected {self.total_items_collected} items, Queue: {self.work_queue.qsize()}"
                        self.logger.info(msg)
                        await self.update_callback(msg, "info")
                    
                    if not after or not self.is_collecting:
                        break
                    
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    self.logger.error(f"[Collector] Error: {e}")
                    await asyncio.sleep(2)
        
        self.is_collecting = False
        self.logger.info(f"[Collector] Finished! Total items: {self.total_items_collected}")
        await self.update_callback(f"Collection finished. Total items: {self.total_items_collected}", "success")
    
    async def worker_process(self, worker_id: int):
        """Worker that processes items with fault tolerance"""
        # Initialize worker state
        self.workers[worker_id] = WorkerState(
            worker_id=worker_id,
            status=WorkerStatus.IDLE,
            last_heartbeat=asyncio.get_event_loop().time()
        )
        
        # Check for checkpoint (recovery)
        recovery_item = await self.load_checkpoint(worker_id)
        if recovery_item:
            self.logger.info(f"[Worker {worker_id}] Recovering from checkpoint: item {recovery_item.item_index}")
            await self.work_queue.put(recovery_item)  # Re-queue the failed item
        
        worker_data = {
            "worker_id": worker_id,
            "scraped_at": datetime.now().isoformat(),
            "subreddit": self.subreddit,
            "posts": []
        }
        
        async with httpx.AsyncClient(headers=self.headers, timeout=30.0) as client:
            while self.is_running:
                try:
                    # Update heartbeat
                    self.workers[worker_id].last_heartbeat = asyncio.get_event_loop().time()
                    
                    # Get work item
                    try:
                        work_item = await asyncio.wait_for(
                            self.work_queue.get(),
                            timeout=5.0
                        )
                    except asyncio.TimeoutError:
                        if not self.is_collecting and self.work_queue.empty():
                            break
                        continue
                    
                    # Update worker state
                    self.workers[worker_id].status = WorkerStatus.WORKING
                    self.workers[worker_id].current_item = work_item
                    
                    # Save checkpoint before processing
                    await self.save_checkpoint(worker_id, work_item)
                    
                    # Process the item
                    try:
                        post_data = await self.fetch_post_details(client, work_item)
                        
                        if post_data:
                            worker_data['posts'].append(post_data)
                            self.workers[worker_id].items_processed += 1
                            self.total_items_processed += 1
                            
                            # Save progress every 5 posts
                            if len(worker_data['posts']) % 5 == 0:
                                await self.save_worker_data(worker_id, worker_data)
                        
                    except Exception as e:
                        self.logger.error(f"[Worker {worker_id}] Error processing item {work_item.item_index}: {e}")
                        self.workers[worker_id].items_failed += 1
                        self.total_items_failed += 1
                        
                        # Re-queue failed item for retry
                        await self.work_queue.put(work_item)
                        await asyncio.sleep(2)
                        continue
                    
                    # Clear checkpoint after successful processing
                    self.workers[worker_id].current_item = None
                    self.workers[worker_id].status = WorkerStatus.IDLE
                    
                    # Rate limiting
                    await asyncio.sleep(1.0)
                    
                except asyncio.CancelledError:
                    self.logger.info(f"[Worker {worker_id}] Cancelled")
                    raise
                except Exception as e:
                    self.logger.error(f"[Worker {worker_id}] Unexpected error: {e}")
                    self.workers[worker_id].status = WorkerStatus.FAILED
                    await asyncio.sleep(5)
        
        # Final save
        await self.save_worker_data(worker_id, worker_data)
        self.workers[worker_id].status = WorkerStatus.COMPLETED
    
    async def fetch_post_details(self, client: httpx.AsyncClient, work_item: WorkItem) -> Optional[Dict]:
        """Fetch full post details"""
        url = f"https://www.reddit.com{work_item.permalink}.json"
        
        data = await self.fetch_json_with_retry(client, url, params={'limit': 500, 'depth': 10})
        
        if not data or len(data) < 1:
            return None
        
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
            "batch_id": work_item.batch_id,
            "item_index": work_item.item_index,
            "comments": [],
            "comments_scraped_count": 0
        }
        
        # Extract comments
        if len(data) > 1 and post.get('num_comments', 0) > 0:
            comments = self.extract_comments(data[1]['data']['children'])
            post_data['comments'] = comments
            post_data['comments_scraped_count'] = len(comments)
        
        return post_data
    
    def extract_comments(self, comments_data: List) -> List[Dict]:
        """Extract comments recursively"""
        comments = []
        
        for comment_item in comments_data:
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
            
            if 'replies' in comment and comment['replies']:
                if isinstance(comment['replies'], dict):
                    replies = self.extract_comments(comment['replies']['data']['children'])
                    comments.extend(replies)
        
        return comments
    
    async def save_worker_data(self, worker_id: int, data: Dict):
        """Save worker data"""
        filename = f"data/worker_{worker_id}_{self.subreddit}_partial.json"
        async with aiofiles.open(filename, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(data, indent=2))
    
    async def monitor_workers(self):
        """Monitor worker health and restart failed workers"""
        while self.is_running and (self.is_collecting or not self.work_queue.empty() or any(
            w.status == WorkerStatus.WORKING for w in self.workers.values()
        )):
            await asyncio.sleep(2)  # Update more frequently for UI
            
            current_time = asyncio.get_event_loop().time()
            
            # Check for failures
            for worker_id, state in self.workers.items():
                if state.status == WorkerStatus.WORKING:
                    time_since_heartbeat = current_time - state.last_heartbeat
                    
                    if time_since_heartbeat > self.heartbeat_timeout:
                        self.logger.warning(f"[Monitor] Worker {worker_id} timeout detected! Restarting...")
                        
                        # Cancel the worker task
                        if worker_id in self.worker_tasks:
                            self.worker_tasks[worker_id].cancel()
                        
                        # Re-queue current item if exists
                        if state.current_item:
                            await self.work_queue.put(state.current_item)
                            self.logger.info(f"[Monitor] Re-queued item {state.current_item.item_index} from worker {worker_id}")
                        
                        # Restart worker
                        state.status = WorkerStatus.IDLE
                        state.current_item = None
                        self.worker_tasks[worker_id] = asyncio.create_task(
                            self.worker_process(worker_id)
                        )
            
            # Prepare stats for UI
            workers_stats = {}
            for wid, state in self.workers.items():
                workers_stats[str(wid)] = {
                    "status": state.status.value,
                    "items_processed": state.items_processed,
                    "items_failed": state.items_failed
                }
            
            # Send updates to UI
            await self.update_callback(workers_stats, "workers_stats")
            
            # Send global stats
            await self.update_callback({
                "posts": self.total_items_processed,
                "comments": 0, # We don't track total comments easily here yet
                "errors": self.total_items_failed
            }, "stats")
    
    async def run(self):
        """Run the fault-tolerant coordinator"""
        self.logger.info(f"Starting fault-tolerant scraper with {self.num_workers} workers")
        await self.update_callback(f"Starting {self.num_workers} workers...", "info")
        
        # Start collector
        collector_task = asyncio.create_task(self.collect_post_lists())
        
        # Start workers
        for i in range(self.num_workers):
            self.worker_tasks[i] = asyncio.create_task(self.worker_process(i))
        
        # Start monitor
        monitor_task = asyncio.create_task(self.monitor_workers())
        
        # Wait for collector
        await collector_task
        
        # Wait for all workers
        await asyncio.gather(*self.worker_tasks.values(), return_exceptions=True)
        
        # Stop monitor
        monitor_task.cancel()
        
        self.logger.info("All workers finished")
        await self.update_callback("All workers finished successfully", "success")

    def stop(self):
        """Stop the coordinator"""
        self.is_running = False
        for task in self.worker_tasks.values():
            task.cancel()
