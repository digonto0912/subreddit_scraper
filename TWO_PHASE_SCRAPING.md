# Two-Phase Distributed Scraping - Practical Implementation

## Overview

This approach solves the "repeated scrolling" problem by separating ID collection from detail fetching.

## Phase 1: Collect All Post IDs (Single Worker)

**File: `collect_post_ids.py`**

```python
import asyncio
import json
import httpx
from datetime import datetime, timezone

async def collect_all_post_ids(subreddit, target_date_str):
    """Quickly collect all post IDs without fetching details"""
    
    target_date = datetime.strptime(target_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    base_url = f"https://www.reddit.com/r/{subreddit}/new.json"
    after = None
    post_ids = []
    
    async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
        while True:
            params = {'limit': 100}
            if after:
                params['after'] = after
            
            response = await client.get(base_url, params=params)
            data = response.json()
            
            posts = data['data']['children']
            after = data['data'].get('after')
            
            for post_data in posts:
                post = post_data['data']
                post_date = datetime.fromtimestamp(post['created_utc'], tz=timezone.utc)
                
                if post_date < target_date:
                    print(f"Reached target date: {post_date.date()}")
                    # Save and exit
                    with open(f'post_ids_{subreddit}.json', 'w') as f:
                        json.dump(post_ids, f, indent=2)
                    return post_ids
                
                # Store minimal info
                post_ids.append({
                    'id': post['id'],
                    'permalink': post['permalink'],
                    'created_utc': post['created_utc'],
                    'num_comments': post.get('num_comments', 0)
                })
                
                if len(post_ids) % 100 == 0:
                    print(f"Collected {len(post_ids)} post IDs...")
            
            if not after:
                break
            
            await asyncio.sleep(1)  # Rate limiting
    
    # Save final list
    with open(f'post_ids_{subreddit}.json', 'w') as f:
        json.dump(post_ids, f, indent=2)
    
    return post_ids

# Usage
asyncio.run(collect_all_post_ids('python', '2024-01-01'))
```

**Time:** ~30 minutes for 1 year (only fetching post lists, not details)

---

## Phase 2: Fetch Details in Parallel (25 Workers)

**File: `fetch_post_details.py`**

```python
import asyncio
import json
import sys
from scraper import SubredditScraper
from logger import setup_logger

async def fetch_details_for_batch(worker_id, total_workers, post_ids_file, subreddit):
    """Fetch full details for assigned batch of posts"""
    
    # Load all post IDs
    with open(post_ids_file, 'r') as f:
        all_post_ids = json.load(f)
    
    # Calculate this worker's batch
    total_posts = len(all_post_ids)
    posts_per_worker = total_posts // total_workers
    
    start_idx = worker_id * posts_per_worker
    if worker_id == total_workers - 1:
        end_idx = total_posts
    else:
        end_idx = (worker_id + 1) * posts_per_worker
    
    my_posts = all_post_ids[start_idx:end_idx]
    
    print(f"Worker {worker_id}: Processing posts {start_idx} to {end_idx} ({len(my_posts)} posts)")
    
    # Setup logger
    logger, _ = setup_logger(f"worker_{worker_id}_{subreddit}")
    
    # Fetch details for each post
    scraped_data = {
        "scraped_at": datetime.now().isoformat(),
        "subreddit": subreddit,
        "worker_id": worker_id,
        "posts": []
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
        for idx, post_info in enumerate(my_posts):
            try:
                # Fetch full post details
                url = f"https://www.reddit.com{post_info['permalink']}.json"
                response = await client.get(url, params={'limit': 500})
                data = response.json()
                
                # Extract post data
                post = data[0]['data']['children'][0]['data']
                
                # Process post (similar to existing scraper)
                post_data = {
                    "post_id": post['id'],
                    "url": f"https://reddit.com{post['permalink']}",
                    "title": post.get('title', ''),
                    "body": post.get('selftext', ''),
                    "author": post.get('author', '[deleted]'),
                    "created_utc": datetime.fromtimestamp(post['created_utc'], tz=timezone.utc).isoformat(),
                    "score": post.get('score', 0),
                    "upvote_ratio": post.get('upvote_ratio', 0.0),
                    "num_comments": post.get('num_comments', 0),
                    # ... other fields
                }
                
                # Extract comments from data[1]
                if len(data) > 1:
                    comments = process_comments(data[1]['data']['children'])
                    post_data['comments'] = comments
                    post_data['comments_scraped_count'] = len(comments)
                
                scraped_data['posts'].append(post_data)
                
                if (idx + 1) % 10 == 0:
                    print(f"Worker {worker_id}: Processed {idx + 1}/{len(my_posts)} posts")
                
                await asyncio.sleep(1)  # Rate limiting
                
            except Exception as e:
                logger.error(f"Error processing post {post_info['id']}: {e}")
                continue
    
    # Save worker's results
    output_file = f"data/worker_{worker_id}_{subreddit}.json"
    with open(output_file, 'w') as f:
        json.dump(scraped_data, f, indent=2)
    
    print(f"Worker {worker_id}: Complete! Saved to {output_file}")

def process_comments(comments_data):
    """Process comment tree"""
    comments = []
    # ... implement comment processing
    return comments

# Usage
if __name__ == "__main__":
    worker_id = int(sys.argv[1])
    total_workers = int(sys.argv[2])
    post_ids_file = sys.argv[3]
    subreddit = sys.argv[4]
    
    asyncio.run(fetch_details_for_batch(worker_id, total_workers, post_ids_file, subreddit))
```

---

## Launch Script

**File: `launch_distributed.ps1`**

```powershell
# PowerShell script to launch all workers

param(
    [int]$TotalWorkers = 25,
    [string]$Subreddit = "python",
    [string]$TargetDate = "2024-01-01"
)

Write-Host "Phase 1: Collecting post IDs..." -ForegroundColor Green
python collect_post_ids.py $Subreddit $TargetDate

$PostIdsFile = "post_ids_$Subreddit.json"

if (-not (Test-Path $PostIdsFile)) {
    Write-Host "Error: Post IDs file not found!" -ForegroundColor Red
    exit 1
}

Write-Host "Phase 2: Launching $TotalWorkers workers..." -ForegroundColor Green

# Launch all workers in parallel
for ($i = 0; $i -lt $TotalWorkers; $i++) {
    Start-Process python -ArgumentList "fetch_post_details.py $i $TotalWorkers $PostIdsFile $Subreddit" -WindowStyle Minimized
    Write-Host "Launched worker $i" -ForegroundColor Cyan
}

Write-Host "All workers launched! Monitor progress in data/ folder" -ForegroundColor Green
```

**Usage:**
```powershell
.\launch_distributed.ps1 -TotalWorkers 25 -Subreddit "python" -TargetDate "2024-01-01"
```

---

## Merge Results

**File: `merge_results.py`**

```python
import json
from glob import glob

def merge_worker_results(subreddit):
    """Merge all worker results into single file"""
    
    worker_files = glob(f"data/worker_*_{subreddit}.json")
    
    merged_data = {
        "scraped_at": datetime.now().isoformat(),
        "subreddit": subreddit,
        "posts": []
    }
    
    for file in sorted(worker_files):
        with open(file, 'r') as f:
            data = json.load(f)
            merged_data['posts'].extend(data['posts'])
    
    output_file = f"data/{subreddit}_complete.json"
    with open(output_file, 'w') as f:
        json.dump(merged_data, f, indent=2)
    
    print(f"Merged {len(worker_files)} workers into {output_file}")
    print(f"Total posts: {len(merged_data['posts'])}")

merge_worker_results('python')
```

---

## Performance

### Phase 1: ID Collection
- **Time:** 30 minutes
- **Workers:** 1
- **Data:** Post IDs only (~1 MB)

### Phase 2: Detail Fetching
- **Time:** 1-2 hours
- **Workers:** 25 parallel
- **Data:** Full posts + comments (~500 MB)

### Total Time
- **1 year of data:** ~2 hours
- **vs Single worker:** 35 hours
- **Speedup:** 17.5x faster

---

## Advantages

✅ **No repeated scrolling** - Phase 1 scrolls once  
✅ **True parallelization** - Phase 2 workers are independent  
✅ **Fault tolerant** - Can restart individual workers  
✅ **Efficient** - Each worker does unique work  
✅ **Scalable** - Add more workers easily  

---

## Monitoring

```powershell
# Check progress
Get-ChildItem data\worker_*.json | Measure-Object | Select-Object Count

# View worker status
Get-Process python | Where-Object {$_.MainWindowTitle -like "*worker*"}
```
