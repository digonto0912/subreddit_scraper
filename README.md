# Subreddit Scraper

A production-grade subreddit scraper with a modern web UI, designed to handle large-scale data collection (1M+ posts).

## Features

- 🎨 **Modern Web UI** - Clean, dark-themed interface with real-time updates
- ⚡ **Async Architecture** - Built with AsyncIO for maximum performance
- 📊 **Real-time Logging** - Live progress updates via Server-Sent Events
- 💾 **Incremental Saving** - Saves progress every 10 posts to prevent data loss
- 🔄 **Author Caching** - Reduces API calls by caching author information
- 📝 **Detailed Logging** - Session logs saved in `logs/` folder
- 📦 **Structured Data** - All data saved according to `data-template.json` structure

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Reddit API Credentials

You need to create a Reddit application to get API credentials:

1. Go to https://www.reddit.com/prefs/apps
2. Click "Create App" or "Create Another App"
3. Fill in the form:
   - **name**: Your app name (e.g., "Subreddit Scraper")
   - **App type**: Select "script"
   - **description**: Optional
   - **about url**: Optional
   - **redirect uri**: http://localhost:8080 (required but not used)
4. Click "Create app"
5. Note your `client_id` (under the app name) and `client_secret`

### 3. Set Environment Variables

**Windows (PowerShell):**
```powershell
$env:REDDIT_CLIENT_ID="your_client_id_here"
$env:REDDIT_CLIENT_SECRET="your_client_secret_here"
```

**Linux/Mac:**
```bash
export REDDIT_CLIENT_ID="your_client_id_here"
export REDDIT_CLIENT_SECRET="your_client_secret_here"
```

## Usage

### 1. Start the Server

```bash
python main.py
```

The server will start at `http://localhost:8000`

### 2. Open the Web UI

Navigate to `http://localhost:8000` in your browser.

### 3. Configure Scraping

- **Subreddit URL or Name**: Enter either:
  - `r/learnpython`
  - `learnpython`
  - `https://reddit.com/r/learnpython`
  
- **Target Date**: Select the oldest post date you want to scrape back to

### 4. Start Scraping

Click "Start Scraping" and monitor the real-time logs and statistics.

## Output

### Data Files
All scraped data is saved in the `data/` folder with the format:
```
{subreddit_name}_{target_date}_{timestamp}.json
```

### Log Files
Session logs are saved in the `logs/` folder with the format:
```
{subreddit_name}_{target_date}_{timestamp}.log
```

## Data Structure

All scraped data follows the structure defined in `data-template.json`, including:

- Post metadata (title, body, author, score, etc.)
- Author information (karma, account age, etc.)
- All comments with nested structure
- Comment author information
- Timestamps in ISO format

## Performance Notes

### Reddit API Limitations

- **Rate Limits**: Reddit's API has rate limits (~60 requests/minute for unauthenticated, ~600/minute for authenticated)
- **Pagination**: Standard API pagination is limited to ~1000 posts per listing
- **Comment Depth**: The scraper limits `replace_more` to 5 to balance completeness vs speed

### For 1M+ Posts

To scrape 1M+ posts efficiently:

1. **Multiple Time Windows**: Run multiple scraping sessions with different date ranges
2. **Parallel Workers**: Run multiple instances with different subreddits
3. **Optimize Comment Depth**: Adjust `replace_more(limit=X)` in `scraper.py` based on your needs
4. **Consider Pushshift**: For historical data, consider using Pushshift archives (if available)

### Optimization Settings

In `scraper.py`, you can adjust:

- **Comment depth**: `await post.comments.replace_more(limit=5)` (line ~198)
- **Save frequency**: `if self.posts_scraped % 10 == 0` (line ~68)
- **Author info caching**: Already implemented to reduce API calls

## Architecture

```
├── main.py              # FastAPI backend
├── scraper.py           # Core scraping logic
├── logger.py            # Logging configuration
├── static/
│   ├── index.html       # Web UI
│   ├── style.css        # Styling
│   └── script.js        # Frontend logic
├── data/                # Scraped data output
└── logs/                # Session logs
```

## Troubleshooting

### "YOUR_CLIENT_ID" Error
Make sure you've set the environment variables correctly before starting the server.

### Rate Limit Errors
The scraper will automatically retry with exponential backoff. If you hit rate limits frequently, consider:
- Reducing comment depth
- Adding delays between posts
- Using authenticated API access

### Missing Comments
If comments are missing, increase the `replace_more(limit=X)` value in `scraper.py`, but note this will slow down scraping significantly.

## License

MIT License - feel free to use and modify as needed.
"# subreddit_scraper" 
