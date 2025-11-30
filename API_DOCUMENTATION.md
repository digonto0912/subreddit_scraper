# API Documentation - Subreddit Scraper

This document provides detailed API documentation for developers who want to extend, modify, or integrate the scraper.

## Table of Contents
1. [REST API Endpoints](#rest-api-endpoints)
2. [WebSocket/SSE Events](#websocketsse-events)
3. [Scraper Class API](#scraper-class-api)
4. [Data Models](#data-models)
5. [Extension Examples](#extension-examples)

---

## REST API Endpoints

### POST /api/scrape

Start a new scraping job.

**Request Body:**
```json
{
  "subreddit": "python",
  "target_date": "2025-11-29"
}
```

**Parameters:**
- `subreddit` (string, required): Subreddit name or URL
  - Accepts: `"python"`, `"r/python"`, `"https://reddit.com/r/python"`
- `target_date` (string, required): Oldest post date to scrape (YYYY-MM-DD format)

**Response:**
```json
{
  "job_id": "uuid-string",
  "status": "started"
}
```

**Status Codes:**
- `200 OK`: Job started successfully
- `400 Bad Request`: Invalid parameters
- `500 Internal Server Error`: Server error

**Example:**
```bash
curl -X POST http://localhost:8000/api/scrape \
  -H "Content-Type: application/json" \
  -d '{"subreddit":"python","target_date":"2025-11-29"}'
```

---

### POST /api/stop

Stop all active scraping jobs.

**Request Body:** None

**Response:**
```json
{
  "status": "stopped"
}
```

**Status Codes:**
- `200 OK`: Jobs stopped successfully

**Example:**
```bash
curl -X POST http://localhost:8000/api/stop
```

---

### GET /api/stream/{job_id}

Server-Sent Events (SSE) stream for real-time updates.

**Parameters:**
- `job_id` (string, required): Job ID from `/api/scrape` response

**Event Types:**

1. **Log Event:**
```json
{
  "type": "log",
  "message": "Scraped: Post title...",
  "level": "info"
}
```

2. **Stats Event:**
```json
{
  "type": "stats",
  "stats": {
    "posts": 10,
    "comments": 45,
    "errors": 0
  }
}
```

3. **Complete Event:**
```json
{
  "type": "complete"
}
```

4. **Error Event:**
```json
{
  "type": "error",
  "message": "Error description"
}
```

**Example (JavaScript):**
```javascript
const eventSource = new EventSource(`/api/stream/${jobId}`);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data);
};
```

---

## Scraper Class API

### Class: `SubredditScraper`

**Location:** `scraper.py`

#### Constructor

```python
SubredditScraper(
    subreddit_name: str,
    target_date_str: str,
    job_id: str,
    logger: logging.Logger,
    update_callback: Callable
)
```

**Parameters:**
- `subreddit_name`: Name of subreddit (without r/ prefix)
- `target_date_str`: Target date in YYYY-MM-DD format
- `job_id`: Unique identifier for this scraping job
- `logger`: Python logger instance
- `update_callback`: Async function for sending updates to UI

---

#### Methods

##### `async run()`

Main scraping loop. Fetches posts and comments until target date is reached.

**Returns:** None

**Raises:**
- `Exception`: On critical errors

**Example:**
```python
scraper = SubredditScraper("python", "2025-11-29", "job-123", logger, callback)
await scraper.run()
```

---

##### `async fetch_json(url: str, params: dict = None) -> Optional[dict]`

Fetch JSON data from a URL with rate limiting.

**Parameters:**
- `url`: Full URL to fetch
- `params`: Optional query parameters

**Returns:** Parsed JSON dict or None on error

**Example:**
```python
data = await scraper.fetch_json(
    "https://reddit.com/r/python/new.json",
    params={"limit": 100}
)
```

---

##### `async process_post(post: dict)`

Process a single post and extract all data.

**Parameters:**
- `post`: Raw post data from Reddit JSON

**Returns:** None (updates internal state)

**Side Effects:**
- Adds post to `scraped_data`
- Increments `posts_scraped` counter
- Calls `update_callback` with progress

---

##### `async fetch_comments(post_id: str, permalink: str) -> List[Dict]`

Fetch all comments for a post.

**Parameters:**
- `post_id`: Reddit post ID
- `permalink`: Post permalink path

**Returns:** List of comment dictionaries

**Example:**
```python
comments = await scraper.fetch_comments(
    "abc123",
    "/r/python/comments/abc123/title/"
)
```

---

##### `async get_author_info(author_name: str) -> Dict[str, Any]`

Fetch author information with caching.

**Parameters:**
- `author_name`: Reddit username

**Returns:** Dictionary with author info

**Caching:** Results are cached in `self.author_cache`

---

##### `stop()`

Stop the scraping process gracefully.

**Returns:** None

**Example:**
```python
scraper.stop()
```

---

#### Properties

##### `is_running: bool`

Whether the scraper is currently running.

##### `posts_scraped: int`

Number of posts scraped so far.

##### `comments_scraped: int`

Number of comments scraped so far.

##### `errors: int`

Number of errors encountered.

##### `scraped_data: dict`

Complete scraped data structure.

---

## Data Models

### Post Data Structure

```python
{
    "post_id": str,              # Reddit post ID
    "url": str,                  # Full post URL
    "title": str,                # Post title
    "body": str,                 # Post body/selftext
    "author": str,               # Author username
    "created_utc": str,          # ISO timestamp
    "subreddit": str,            # Subreddit name
    "flair": Optional[str],      # Post flair
    "score": int,                # Post score
    "upvote_ratio": float,       # Upvote ratio (0-1)
    "num_comments": int,         # Comment count
    "awards": int,               # Total awards
    "is_nsfw": bool,             # NSFW flag
    "num_shares": int,           # Share count (always 0)
    "num_saves": int,            # Save count (always 0)
    "author_info": AuthorInfo,   # Author details
    "comments": List[Comment],   # All comments
    "comments_scraped_count": int # Comment count
}
```

### Comment Data Structure

```python
{
    "comment_id": str,           # Reddit comment ID
    "parent_id": str,            # Parent ID (post or comment)
    "author": str,               # Author username
    "body": str,                 # Comment text
    "created_utc": str,          # ISO timestamp
    "score": int,                # Comment score
    "depth": int,                # Nesting depth
    "author_info": AuthorInfo    # Author details
}
```

### Author Info Structure

```python
{
    "username": str,                      # Reddit username
    "account_created_utc": Optional[str], # ISO timestamp
    "post_karma": int,                    # Link karma
    "comment_karma": int,                 # Comment karma
    "total_karma": int,                   # Total karma
    "num_posts": int,                     # Post count (always 0)
    "num_comments": int,                  # Comment count (always 0)
    "subreddits_participated_in": List[str] # Subreddits (always [])
}
```

---

## Extension Examples

### Example 1: Custom Data Processing

Add custom processing after each post is scraped:

```python
# In scraper.py, add to process_post method:

async def process_post(self, post: dict):
    # ... existing code ...
    
    # Custom processing
    if self.custom_processor:
        await self.custom_processor(post_data)
    
    # ... rest of code ...
```

### Example 2: Export to Database

Instead of JSON files, save to database:

```python
# In scraper.py, modify save_final method:

async def save_final(self):
    try:
        # Save to database instead of file
        await self.save_to_database(self.scraped_data)
        
    except Exception as e:
        self.logger.error(f"Error saving to database: {e}")

async def save_to_database(self, data: dict):
    # Your database logic here
    async with aiosqlite.connect("reddit.db") as db:
        for post in data["posts"]:
            await db.execute(
                "INSERT INTO posts VALUES (?, ?, ?)",
                (post["post_id"], post["title"], post["body"])
            )
        await db.commit()
```

### Example 3: Real-time Webhook Notifications

Send webhook when scraping completes:

```python
# In scraper.py, add to run method:

async def run(self):
    try:
        # ... existing scraping code ...
        
    finally:
        await self.save_final()
        await self.send_webhook_notification()
        await self.reddit.close()

async def send_webhook_notification(self):
    webhook_url = "https://your-webhook.com/notify"
    async with httpx.AsyncClient() as client:
        await client.post(webhook_url, json={
            "job_id": self.job_id,
            "posts_scraped": self.posts_scraped,
            "comments_scraped": self.comments_scraped
        })
```

### Example 4: Filter Posts by Keywords

Only scrape posts matching certain keywords:

```python
# In scraper.py, modify process_post:

async def process_post(self, post: dict):
    # Filter by keywords
    keywords = ["machine learning", "AI", "neural network"]
    title_lower = post.get('title', '').lower()
    
    if not any(keyword in title_lower for keyword in keywords):
        return  # Skip this post
    
    # ... rest of existing code ...
```

### Example 5: Add Custom Metrics

Track additional metrics:

```python
# In scraper.py, add to __init__:

def __init__(self, ...):
    # ... existing code ...
    self.custom_metrics = {
        "nsfw_posts": 0,
        "gilded_posts": 0,
        "high_score_posts": 0
    }

# In process_post:
async def process_post(self, post: dict):
    # ... existing code ...
    
    # Track custom metrics
    if post.get('over_18'):
        self.custom_metrics["nsfw_posts"] += 1
    if post.get('gilded', 0) > 0:
        self.custom_metrics["gilded_posts"] += 1
    if post.get('score', 0) > 1000:
        self.custom_metrics["high_score_posts"] += 1
    
    # Send to UI
    await self.update_callback({
        "posts": self.posts_scraped,
        "comments": self.comments_scraped,
        "errors": self.errors,
        **self.custom_metrics
    }, "stats")
```

---

## Configuration Reference

### Rate Limiting

```python
# scraper.py, line ~42
self.min_request_interval = 1.0  # Seconds between requests
```

### HTTP Headers

```python
# scraper.py, line ~37
self.headers = {
    'User-Agent': 'Mozilla/5.0...',
    'Accept': 'application/json',
    'Accept-Language': 'en-US,en;q=0.9',
}
```

### Timeouts

```python
# scraper.py, line ~50
async with httpx.AsyncClient(headers=self.headers, timeout=30.0) as client:
```

### Save Frequency

```python
# scraper.py, line ~107
if self.posts_scraped % 10 == 0:  # Save every N posts
    await self.save_partial()
```

---

## Testing

### Unit Test Example

```python
import pytest
from scraper import SubredditScraper

@pytest.mark.asyncio
async def test_fetch_json():
    scraper = SubredditScraper("python", "2025-11-29", "test", logger, callback)
    data = await scraper.fetch_json("https://reddit.com/r/python/new.json")
    assert data is not None
    assert "data" in data
```

### Integration Test Example

```python
@pytest.mark.asyncio
async def test_full_scrape():
    scraper = SubredditScraper("test", "2025-11-29", "test", logger, callback)
    await scraper.run()
    assert scraper.posts_scraped > 0
    assert len(scraper.scraped_data["posts"]) > 0
```

---

## Best Practices

1. **Always use rate limiting** to avoid being blocked
2. **Cache author info** to reduce requests
3. **Save progress frequently** for large scrapes
4. **Handle errors gracefully** and log them
5. **Use async/await** for better performance
6. **Validate data** before saving
7. **Monitor memory usage** for large scrapes
8. **Use type hints** for better code quality

---

## Support

For issues or questions:
- Check `TROUBLESHOOTING.md`
- Review `walkthrough.md` for examples
- Check GitHub issues
