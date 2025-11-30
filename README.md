# Subreddit Scraper

A production-grade custom subreddit scraper with a modern web UI, designed to handle large-scale data collection (1M+ posts).

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start server
python main.py

# 3. Open browser
# Navigate to http://localhost:8000

# 4. Start scraping!
# Enter subreddit name and target date, then click "Start Scraping"
```

**That's it!** No API credentials needed!

---

## ✨ Features

- 🎨 **Modern Web UI** - Clean, dark-themed interface with real-time updates
- ⚡ **Custom HTTP Scraper** - No Reddit API required! Direct JSON endpoint access
- 📊 **Real-time Logging** - Live progress updates via Server-Sent Events
- 💾 **Incremental Saving** - Saves progress every 10 posts to prevent data loss
- 🔄 **Author Caching** - Reduces HTTP requests by caching author information
- 📝 **Detailed Logging** - Session logs saved in `logs` folder
- 📦 **Structured Data** - All data saved according to `data-template.json` structure
- 🚀 **No Rate Limits** - Custom scraper with smart rate limiting (1 req/sec)
- 🔧 **Production Ready** - Error handling, recovery, and comprehensive documentation

---

## 📚 Documentation

- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Comprehensive guide for all potential issues
- **[API_DOCUMENTATION.md](API_DOCUMENTATION.md)** - API reference for developers
- **[data-template.json](data-template.json)** - Data structure reference
- **[walkthrough.md](walkthrough.md)** - Implementation walkthrough with examples

---

## 🎯 How It Works

### Custom HTTP Scraper (No API Required!)

Instead of using Reddit's official API, this scraper:

1. **Direct JSON Access**: Fetches data from Reddit's public JSON endpoints
   - Posts: `https://reddit.com/r/{subreddit}/new.json`
   - Comments: `https://reddit.com/r/{subreddit}/comments/{post_id}.json`
   - Users: `https://reddit.com/user/{username}/about.json`

2. **No Authentication**: No API keys or OAuth required

3. **Smart Rate Limiting**: 1 request per second to avoid being blocked

4. **Recursive Comment Fetching**: Automatically processes nested comment threads

---

## 📁 Output

### Data Files
All scraped data is saved in the `data/` folder:
```
data/
├── python_20251129_20251130_152409.json
├── MachineLearning_20251129_20251130_145523.json
└── ...
```

Format: `{subreddit}_{target_date}_{timestamp}.json`

### Log Files
Session logs are saved in the `logs/` folder:
```
logs/
├── python_20251129_20251130_152409.log
├── MachineLearning_20251129_20251130_145522.log
└── ...
```

Format: `{subreddit}_{target_date}_{timestamp}.log`

---

## 📊 Data Structure

All scraped data follows the structure defined in `data-template.json`:

```json
{
  "scraped_at": "2025-11-30T15:24:09.192",
  "subreddit": "python",
  "date_range": {
    "start": "2025-11-29",
    "end": "2025-11-30"
  },
  "posts": [
    {
      "post_id": "abc123",
      "url": "https://reddit.com/r/python/...",
      "title": "Post title",
      "body": "Post content",
      "author": "username",
      "created_utc": "2025-11-30T10:00:00+00:00",
      "score": 42,
      "upvote_ratio": 0.95,
      "num_comments": 15,
      "author_info": { /* full author details */ },
      "comments": [ /* all comments with nested structure */ ]
    }
  ]
}
```

See [data-template.json](data-template.json) for complete structure.

---

## ⚙️ Configuration

### Rate Limiting
Edit `scraper.py` (line ~42):
```python
self.min_request_interval = 1.0  # Seconds between requests
```

### Save Frequency
Edit `scraper.py` (line ~107):
```python
if self.posts_scraped % 10 == 0:  # Save every N posts
```

### Server Port
Edit `main.py` (last line):
```python
uvicorn.run(app, host="0.0.0.0", port=8000)  # Change port here
```

### Timeout
Edit `scraper.py` (line ~50):
```python
async with httpx.AsyncClient(headers=self.headers, timeout=30.0) as client:
```

---

## 🚀 Performance

### Advantages Over API-Based Scrapers

| Feature | Custom Scraper | API Scraper |
|---------|---------------|-------------|
| Setup Time | **Instant** | 5-10 minutes |
| Authentication | **None** | Required |
| Rate Limits | **Self-managed** | Strict (600/min) |
| Reliability | **High** | Medium |
| Cost | **Free** | Free (with limits) |

### For Large-Scale Scraping (1M+ posts)

1. **Split by date ranges** - Scrape in monthly chunks
2. **Run multiple instances** - Different ports for different subreddits
3. **Optimize settings** - Adjust rate limiting and save frequency
4. **Monitor resources** - Check RAM and CPU usage

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for detailed optimization guide.

---

## 🛠️ Troubleshooting

### Common Issues

**No data being collected?**
- Check internet connection
- Verify subreddit name spelling
- Check target date (must be in the past)
- See [TROUBLESHOOTING.md](TROUBLESHOOTING.md#scraping-issues)

**Server won't start?**
- Port 8000 might be in use
- Check dependencies are installed
- See [TROUBLESHOOTING.md](TROUBLESHOOTING.md#server-issues)

**Scraping is slow?**
- Adjust rate limiting in `scraper.py`
- Disable author info fetching if not needed
- See [TROUBLESHOOTING.md](TROUBLESHOOTING.md#performance-issues)

For all issues, see **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - comprehensive guide covering:
- Installation issues
- Server issues
- Scraping issues
- Data issues
- Performance issues
- Network issues
- UI issues
- Advanced configuration

---

## 📖 For Developers

### API Documentation

See [API_DOCUMENTATION.md](API_DOCUMENTATION.md) for:
- REST API endpoints
- WebSocket/SSE events
- Scraper class API
- Data models
- Extension examples

### Extending the Scraper

```python
# Example: Add custom processing
async def process_post(self, post: dict):
    # ... existing code ...
    
    # Your custom logic here
    if self.custom_processor:
        await self.custom_processor(post_data)
```

See [API_DOCUMENTATION.md](API_DOCUMENTATION.md#extension-examples) for more examples.

---

## 📁 Project Structure

```
subreddit_scraper/
├── main.py                    # FastAPI backend
├── scraper.py                 # Custom HTTP scraper
├── logger.py                  # Logging configuration
├── requirements.txt           # Dependencies
├── README.md                  # This file
├── TROUBLESHOOTING.md         # Troubleshooting guide
├── API_DOCUMENTATION.md       # API reference
├── data-template.json         # Data structure reference
├── static/
│   ├── index.html             # Web UI
│   ├── style.css              # Styling
│   └── script.js              # Frontend logic
├── data/                      # Scraped data (created on first run)
└── logs/                      # Session logs (created on first run)
```

---

## 🔒 Privacy & Ethics

This scraper:
- ✅ Only accesses **public** Reddit data
- ✅ Respects rate limits to avoid server overload
- ✅ Does not require authentication or personal data
- ✅ Follows Reddit's public JSON endpoints

**Please use responsibly:**
- Don't scrape private or restricted subreddits
- Respect Reddit's terms of service
- Use reasonable rate limits
- Don't use scraped data for harassment or spam

---

## 📝 License

MIT License - feel free to use and modify as needed.

---

## 🙏 Support

- **Issues?** Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **Development?** See [API_DOCUMENTATION.md](API_DOCUMENTATION.md)
- **Questions?** Review [walkthrough.md](walkthrough.md)

---

## 🎉 Quick Reference

### Installation
```bash
pip install -r requirements.txt
```

### Start Server
```bash
python main.py
```

### Access UI
```
http://localhost:8000
```

### Check Logs
```bash
type logs\*.log
```

### Validate Data
```bash
python -m json.tool data\latest.json
```

---

**Ready to scrape? Start the server and open http://localhost:8000!** 🚀
