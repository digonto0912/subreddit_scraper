# Subreddit Scraper

A production-grade custom subreddit scraper with a modern web UI, designed to handle large-scale data collection (1M+ posts).

## Features

- 🎨 **Modern Web UI** - Clean, dark-themed interface with real-time updates
- ⚡ **Custom HTTP Scraper** - No Reddit API required! Direct JSON endpoint access
- 📊 **Real-time Logging** - Live progress updates via Server-Sent Events
- 💾 **Incremental Saving** - Saves progress every 10 posts to prevent data loss
- 🔄 **Author Caching** - Reduces HTTP requests by caching author information
- 📝 **Detailed Logging** - Session logs saved in `logs` folder
- 📦 **Structured Data** - All data saved according to `data-template.json` structure
- 🚀 **No Rate Limits** - Custom scraper with smart rate limiting (1 req/sec)

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

**That's it!** No API credentials needed!

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
  - `r/MachineLearning`
  - `MachineLearning`
  - `https://reddit.com/r/MachineLearning`
  
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

## How It Works

### Custom HTTP Scraper
Instead of using Reddit's official API, this scraper:

1. **Direct JSON Access**: Fetches data from Reddit's public JSON endpoints
2. **No Authentication**: No API keys or OAuth required
3. **Smart Rate Limiting**: 1 request per second to avoid being blocked
4. **Recursive Comment Fetching**: Automatically processes nested comment threads

## Performance Notes

### Advantages of Custom Scraper

✅ **No API Limits** - Not restricted by Reddit's API rate limits  
✅ **No Authentication** - Works immediately without setup  
✅ **More Reliable** - Direct access to public data  
✅ **Faster Setup** - No credential configuration needed  

## Troubleshooting

### No Data Being Scraped
- Check the `logs/` folder for error messages
- Verify the subreddit name is correct
- Check your internet connection

### "Too Many Requests" Error
- The scraper has built-in rate limiting (1 req/sec)
- If you still get this error, increase `min_request_interval` in `scraper.py`

## License

MIT License - feel free to use and modify as needed.
