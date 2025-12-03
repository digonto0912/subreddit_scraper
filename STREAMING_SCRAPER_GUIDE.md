# Streaming Scraper - Real-Time Distribution

## Overview

This approach implements a **streaming pipeline** where:
1. **Collector** continuously fetches post lists (100 posts every ~2 seconds)
2. **Queue** distributes posts to workers in real-time
3. **25 Workers** process posts in parallel as they arrive

## How It Works

```
┌─────────────┐
│  Collector  │ ──> Fetches 100 posts every 2 sec
└──────┬──────┘
       │
       ▼
┌─────────────┐
│    Queue    │ ──> Holds ~1000 posts max
└──────┬──────┘
       │
       ├──> Worker 1  ──> Processes posts
       ├──> Worker 2  ──> Processes posts
       ├──> Worker 3  ──> Processes posts
       │    ...
       └──> Worker 25 ──> Processes posts
```

## Advantages

✅ **No waiting** - Workers start immediately  
✅ **Continuous flow** - Posts processed as they're collected  
✅ **Efficient** - No idle time for workers  
✅ **Scalable** - Add more workers easily  
✅ **Fault tolerant** - Workers save progress every 10 posts  

## Usage

### Step 1: Run the Streaming Scraper

```bash
python streaming_coordinator.py <subreddit> <target_date> [num_workers]
```

**Example:**
```bash
# Scrape r/python from 2024-01-01 with 25 workers
python streaming_coordinator.py python 2024-01-01 25
```

### Step 2: Monitor Progress

The scraper will show real-time updates:

```
[Collector] Collected 100 posts, Queue size: 95
[Worker 0] Processed 10 posts
[Worker 1] Processed 10 posts
[Monitor] Collected: 500 | Processed: 450 | Queue: 50
```

### Step 3: Merge Results

After scraping completes:

```bash
python merge_worker_results.py python
```

This creates: `data/python_complete_YYYYMMDD_HHMMSS.json`

## Performance

### Timeline for 1 Year of Data

**Assumptions:**
- 50 posts/day average
- 18,250 posts total
- 10 comments/post average

**Collector:**
- 18,250 posts ÷ 100 per batch = 183 batches
- 183 batches × 2 seconds = 366 seconds = **6 minutes**

**Workers (parallel):**
- 18,250 posts ÷ 25 workers = 730 posts per worker
- 730 posts × 7 seconds = 5,110 seconds = **85 minutes**

**Total Time:** ~**90 minutes** (1.5 hours)

### Comparison

| Method | Time | Speedup |
|--------|------|---------|
| Single worker | 35 hours | 1x |
| Two-phase | 2 hours | 17.5x |
| **Streaming** | **1.5 hours** | **23x** |

## Configuration

### Adjust Number of Workers

```bash
# Use 10 workers (safer, slower)
python streaming_coordinator.py python 2024-01-01 10

# Use 50 workers (faster, riskier)
python streaming_coordinator.py python 2024-01-01 50
```

### Adjust Rate Limiting

Edit `streaming_coordinator.py`:

```python
# Line ~120 - Collector rate limit
await asyncio.sleep(0.5)  # Change to 1.0 for slower, safer

# Line ~180 - Worker rate limit
await asyncio.sleep(1.0)  # Change to 0.5 for faster, riskier
```

### Adjust Queue Size

```python
# Line ~20
self.post_queue = asyncio.Queue(maxsize=1000)  # Increase for more buffering
```

## Monitoring

### Check Worker Progress

```bash
# Count worker files
dir data\worker_*_partial.json | measure

# View latest worker file
type data\worker_0_python_partial.json
```

### View Queue Status

The monitor task shows:
- **Collected:** Total posts collected by collector
- **Processed:** Total posts processed by workers
- **Queue:** Current queue size

## Error Handling

### If a Worker Crashes

Workers save progress every 10 posts. If a worker crashes:

1. Check the partial file: `data/worker_X_subreddit_partial.json`
2. The data is already saved
3. Restart the scraper - it will continue from where it left off

### If Collector Crashes

The collector will automatically retry on errors. If it fails completely:

1. Check the last `after` token in logs
2. Restart with that token (requires code modification)

## Advanced Usage

### Scrape Multiple Subreddits

```bash
# Terminal 1
python streaming_coordinator.py python 2024-01-01 25

# Terminal 2
python streaming_coordinator.py MachineLearning 2024-01-01 25

# Terminal 3
python streaming_coordinator.py singularity 2024-01-01 25
```

### Custom Date Ranges

```bash
# Last month
python streaming_coordinator.py python 2024-11-01 25

# Last week
python streaming_coordinator.py python 2024-11-24 25

# Last year
python streaming_coordinator.py python 2023-01-01 25
```

## Output Files

### During Scraping

```
data/
├── worker_0_python_partial.json
├── worker_1_python_partial.json
├── worker_2_python_partial.json
...
└── worker_24_python_partial.json
```

### After Merging

```
data/
├── python_complete_20241203_115430.json  # Final merged file
└── worker_*_partial.json  # Can be deleted
```

## Troubleshooting

### Queue Fills Up

If queue reaches maxsize (1000):
- Collector will wait until workers catch up
- This is normal and prevents memory overflow

### Workers Idle

If workers are idle but collector is running:
- Check queue size
- Increase collector speed (reduce sleep time)
- Decrease worker rate limit

### Rate Limiting Errors

If you see 429 errors:
- Increase worker sleep time to 2.0 seconds
- Reduce number of workers to 10-15
- Increase collector sleep time to 1.0 second

## Best Practices

1. **Start conservative:** Use 10 workers first
2. **Monitor queue:** Should stay between 50-200
3. **Save often:** Workers save every 10 posts
4. **Merge after:** Always merge results when done
5. **Check logs:** Monitor for errors

## Example Session

```bash
# Start scraping
PS> python streaming_coordinator.py python 2024-01-01 25

Starting streaming scraper with 25 workers
Subreddit: r/python
Target date: 2024-01-01

[Collector] Starting to collect posts from r/python
[Worker 0] Started
[Worker 1] Started
...
[Worker 24] Started

[Collector] Collected 100 posts, Queue size: 95
[Worker 0] Processed 10 posts
[Worker 5] Processed 10 posts

[Monitor] Collected: 500 | Processed: 450 | Queue: 50

[Collector] Reached target date: 2024-01-01
[Collector] Finished! Total posts collected: 18250

[Worker 0] No more posts, finishing...
[Worker 0] Finished! Processed 730 posts
...
[Worker 24] Finished! Processed 730 posts

✅ All done! Total posts processed: 18250
Check data/worker_*_python_partial.json for results

# Merge results
PS> python merge_worker_results.py python

Found 25 worker files
Merging: data/worker_0_python_partial.json
Merging: data/worker_1_python_partial.json
...

✅ Merge complete!
Output: data/python_complete_20241203_115430.json
Total posts: 18250
Total comments: 182500
File size: 456.78 MB
```

## Summary

The streaming scraper is the **fastest and most efficient** method:

- ✅ **Real-time processing** - No waiting between phases
- ✅ **Optimal resource usage** - Workers never idle
- ✅ **Simple to use** - One command to run everything
- ✅ **Production ready** - Error handling and progress saving

**Use this for large-scale scraping!**
