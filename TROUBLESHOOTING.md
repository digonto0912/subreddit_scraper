# Troubleshooting Guide - Subreddit Scraper

This comprehensive guide covers all potential issues you might encounter and their solutions.

## Table of Contents
1. [Installation Issues](#installation-issues)
2. [Server Issues](#server-issues)
3. [Scraping Issues](#scraping-issues)
4. [Data Issues](#data-issues)
5. [Performance Issues](#performance-issues)
6. [Network Issues](#network-issues)
7. [UI Issues](#ui-issues)
8. [Advanced Configuration](#advanced-configuration)

---

## Installation Issues

### Issue: `pip install` fails with dependency conflicts

**Symptoms:**
```
ERROR: pip's dependency resolver does not currently take into account...
```

**Solutions:**

1. **Use a virtual environment (Recommended):**
```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux/Mac)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

2. **Force reinstall:**
```bash
pip install --force-reinstall -r requirements.txt
```

3. **Install individually:**
```bash
pip install fastapi==0.104.1
pip install uvicorn[standard]==0.24.0
pip install httpx==0.25.2
pip install aiofiles==0.8.0
pip install pydantic==2.5.0
```

### Issue: Python version incompatibility

**Symptoms:**
```
ERROR: Package requires a different Python version
```

**Solution:**
- Requires Python 3.8 or higher
- Check version: `python --version`
- Upgrade Python if needed

---

## Server Issues

### Issue: Port 8000 already in use

**Symptoms:**
```
ERROR: [Errno 10048] error while attempting to bind on address ('0.0.0.0', 8000)
```

**Solutions:**

1. **Find and kill the process:**
```bash
# Windows
netstat -ano | findstr :8000
taskkill /F /PID <PID>

# Linux/Mac
lsof -i :8000
kill -9 <PID>
```

2. **Use a different port:**
Edit `main.py` (last line):
```python
uvicorn.run(app, host="0.0.0.0", port=8080)  # Change to 8080 or any available port
```

### Issue: Server crashes immediately

**Symptoms:**
Server starts then immediately exits

**Solutions:**

1. **Check for syntax errors:**
```bash
python -m py_compile main.py
python -m py_compile scraper.py
```

2. **Check dependencies:**
```bash
pip list | findstr "fastapi httpx aiofiles"
```

3. **Run with verbose logging:**
```bash
python main.py --log-level debug
```

### Issue: Server runs but UI doesn't load

**Symptoms:**
- Server shows "Running on http://0.0.0.0:8000"
- Browser shows "Connection refused" or blank page

**Solutions:**

1. **Check firewall:**
   - Allow Python through Windows Firewall
   - Temporarily disable firewall to test

2. **Try localhost instead:**
   - Use `http://localhost:8000` instead of `http://0.0.0.0:8000`

3. **Check static files:**
```bash
# Verify static directory exists
dir static
# Should show: index.html, style.css, script.js
```

---

## Scraping Issues

### Issue: No data being collected

**Symptoms:**
- Scraper starts but posts count stays at 0
- Empty JSON files created

**Solutions:**

1. **Check internet connection:**
```bash
ping reddit.com
```

2. **Verify subreddit exists:**
   - Visit `https://reddit.com/r/{subreddit_name}` in browser
   - Check spelling of subreddit name

3. **Check target date:**
   - Ensure target date is in the past
   - Subreddit might not have posts that old

4. **Check logs:**
```bash
# View latest log file
type logs\*.log | more
```

### Issue: "429 Too Many Requests" error

**Symptoms:**
```
ERROR: Error fetching https://reddit.com/...: 429 Too Many Requests
```

**Solutions:**

1. **Increase rate limit delay:**
Edit `scraper.py` (line ~42):
```python
self.min_request_interval = 2.0  # Increase from 1.0 to 2.0 seconds
```

2. **Wait and retry:**
   - Reddit may have temporarily rate-limited your IP
   - Wait 5-10 minutes before retrying

3. **Use VPN (if persistent):**
   - Switch to a different IP address

### Issue: Comments not being scraped

**Symptoms:**
- Posts are scraped but `comments_scraped_count` is 0

**Solutions:**

1. **Check if posts have comments:**
   - Verify on Reddit that posts actually have comments

2. **Increase comment fetch limit:**
Edit `scraper.py` (line ~230):
```python
data = await self.fetch_json(url, params={'limit': 1000})  # Increase from 500
```

3. **Check for "load more" comments:**
   - Some comments are hidden behind "load more"
   - Current implementation skips these (by design)

### Issue: Scraper stops unexpectedly

**Symptoms:**
- Scraping stops mid-way
- No error messages

**Solutions:**

1. **Check partial files:**
```bash
dir data\*_partial.json
```
   - Partial files contain progress before crash

2. **Check system resources:**
   - Task Manager → Check RAM usage
   - Close other applications if RAM is low

3. **Add more frequent saves:**
Edit `scraper.py` (line ~107):
```python
if self.posts_scraped % 5 == 0:  # Save every 5 posts instead of 10
```

### Issue: Author info not being fetched

**Symptoms:**
- `author_info` fields are empty or default values

**Solutions:**

1. **Check rate limiting:**
   - Too many author requests might trigger rate limits
   - Author caching should prevent this

2. **Deleted accounts:**
   - `[deleted]` authors won't have info
   - This is expected behavior

3. **Increase timeout:**
Edit `scraper.py` (line ~50):
```python
async with httpx.AsyncClient(headers=self.headers, timeout=60.0) as client:
```

---

## Data Issues

### Issue: JSON files are empty or incomplete

**Symptoms:**
```json
{
  "posts": []
}
```

**Solutions:**

1. **Check if scraping completed:**
   - Look for "Scraping finished" in logs

2. **Check target date:**
   - Might be no posts in that date range

3. **Verify data structure:**
```bash
python -m json.tool data\latest_file.json
```

### Issue: Invalid JSON format

**Symptoms:**
```
JSONDecodeError: Expecting value
```

**Solutions:**

1. **Validate JSON:**
```bash
python -m json.tool data\file.json
```

2. **Check for corruption:**
   - Delete corrupted file
   - Use partial file if available

3. **Re-scrape:**
   - Delete bad file and scrape again

### Issue: Missing fields in scraped data

**Symptoms:**
- Some posts missing `title`, `body`, or other fields

**Solutions:**

1. **Check Reddit's data:**
   - Some posts might not have all fields
   - Deleted posts lose content

2. **Verify template matching:**
   - Compare with `data-template.json`

3. **Check scraper version:**
   - Ensure using latest `scraper.py`

---

## Performance Issues

### Issue: Scraping is very slow

**Symptoms:**
- Taking hours to scrape a few hundred posts

**Solutions:**

1. **Reduce rate limit (carefully):**
Edit `scraper.py`:
```python
self.min_request_interval = 0.5  # Reduce from 1.0 (risky!)
```
⚠️ **Warning:** Too fast may get you blocked

2. **Disable author info fetching:**
Edit `scraper.py` (line ~180):
```python
# Comment out author info fetch for speed
# author_info = await self.get_author_info(author_name)
author_info = {"username": author_name, ...}  # Use defaults
```

3. **Skip comments (if not needed):**
Edit `scraper.py` (line ~200):
```python
# Skip comment fetching
# comments = await self.fetch_comments(post_id, permalink)
comments = []
```

### Issue: High memory usage

**Symptoms:**
- RAM usage keeps increasing
- System becomes slow

**Solutions:**

1. **Increase save frequency:**
Edit `scraper.py`:
```python
if self.posts_scraped % 5 == 0:  # Save more frequently
```

2. **Clear cache periodically:**
Edit `scraper.py` (add after line ~110):
```python
# Clear author cache every 100 posts
if self.posts_scraped % 100 == 0:
    self.author_cache.clear()
```

3. **Restart scraper periodically:**
   - For very large scrapes (100k+ posts)
   - Scrape in batches by date range

### Issue: CPU usage is high

**Symptoms:**
- CPU at 100%
- Computer becomes unresponsive

**Solutions:**

1. **Increase rate limit:**
```python
self.min_request_interval = 2.0  # More delay = less CPU
```

2. **Reduce concurrent operations:**
   - Current implementation is already sequential
   - No changes needed

---

## Network Issues

### Issue: Connection timeout

**Symptoms:**
```
ERROR: Timeout while fetching...
```

**Solutions:**

1. **Increase timeout:**
Edit `scraper.py`:
```python
async with httpx.AsyncClient(headers=self.headers, timeout=60.0) as client:
```

2. **Check internet stability:**
```bash
ping -t reddit.com
```

3. **Retry failed requests:**
   - Scraper will continue after timeout
   - Check logs for which posts failed

### Issue: SSL/TLS errors

**Symptoms:**
```
ERROR: SSL: CERTIFICATE_VERIFY_FAILED
```

**Solutions:**

1. **Update certificates:**
```bash
pip install --upgrade certifi
```

2. **Disable SSL verification (not recommended):**
Edit `scraper.py`:
```python
async with httpx.AsyncClient(headers=self.headers, verify=False) as client:
```

### Issue: DNS resolution failures

**Symptoms:**
```
ERROR: Failed to resolve 'reddit.com'
```

**Solutions:**

1. **Check DNS:**
```bash
nslookup reddit.com
```

2. **Use different DNS:**
   - Change to Google DNS: 8.8.8.8
   - Or Cloudflare DNS: 1.1.1.1

---

## UI Issues

### Issue: CSS/JS not loading

**Symptoms:**
- UI looks unstyled
- No functionality

**Solutions:**

1. **Check static paths:**
Verify in `index.html`:
```html
<link rel="stylesheet" href="/static/style.css">
<script src="/static/script.js"></script>
```

2. **Clear browser cache:**
   - Ctrl + Shift + Delete
   - Or use incognito mode

3. **Check server logs:**
   - Should show 200 OK for static files
   - If 404, check file paths

### Issue: Real-time updates not working

**Symptoms:**
- Stats don't update
- Logs don't appear

**Solutions:**

1. **Check SSE connection:**
   - Open browser console (F12)
   - Look for EventSource errors

2. **Firewall blocking:**
   - Allow EventSource connections
   - Check browser security settings

3. **Browser compatibility:**
   - Use modern browser (Chrome, Firefox, Edge)
   - Update browser to latest version

### Issue: Form submission doesn't work

**Symptoms:**
- Clicking "Start Scraping" does nothing

**Solutions:**

1. **Check browser console:**
   - F12 → Console tab
   - Look for JavaScript errors

2. **Verify API endpoint:**
```bash
curl -X POST http://localhost:8000/api/scrape -H "Content-Type: application/json" -d "{\"subreddit\":\"python\",\"target_date\":\"2025-11-29\"}"
```

3. **Check script.js:**
   - Ensure file loaded correctly
   - Check for syntax errors

---

## Advanced Configuration

### Scraping Large Subreddits (1M+ posts)

**Strategy:**

1. **Split by date ranges:**
```python
# Scrape in 1-month chunks
# Month 1: 2024-01-01 to 2024-01-31
# Month 2: 2024-02-01 to 2024-02-28
# etc.
```

2. **Run multiple instances:**
   - Use different ports (8000, 8001, 8002)
   - Scrape different subreddits simultaneously

3. **Optimize settings:**
```python
# In scraper.py
self.min_request_interval = 0.8  # Slightly faster
# Save less frequently for speed
if self.posts_scraped % 50 == 0:
```

### Custom User-Agent

**To avoid detection:**

Edit `scraper.py` (line ~37):
```python
self.headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
    'Accept': 'application/json',
}
```

### Proxy Support

**For IP rotation:**

Edit `scraper.py`:
```python
async def fetch_json(self, url: str, params: dict = None) -> Optional[dict]:
    await self.rate_limit()
    
    proxies = {
        "http://": "http://proxy.example.com:8080",
        "https://": "http://proxy.example.com:8080"
    }
    
    async with httpx.AsyncClient(headers=self.headers, proxies=proxies, timeout=30.0) as client:
        # ... rest of code
```

### Resume Interrupted Scraping

**Using partial files:**

1. **Find partial file:**
```bash
dir data\*_partial.json
```

2. **Rename to final:**
```bash
ren data\job_id_partial.json subreddit_date_timestamp.json
```

3. **Extract last post ID:**
   - Open JSON file
   - Find last `post_id`
   - Manually continue from there (requires code modification)

---

## Logging and Debugging

### Enable Debug Logging

Edit `logger.py`:
```python
logger.setLevel(logging.DEBUG)  # Change from INFO
```

### View Live Logs

```bash
# Windows
Get-Content logs\latest.log -Wait

# Linux/Mac
tail -f logs/latest.log
```

### Common Log Messages

| Message | Meaning | Action |
|---------|---------|--------|
| `Starting scrape for r/...` | Scraping started | Normal |
| `Reached target date` | Finished successfully | Normal |
| `Error fetching...` | Network/API error | Check network |
| `401 HTTP response` | Not used anymore | N/A |
| `429 Too Many Requests` | Rate limited | Increase delay |
| `Saved partial progress` | Auto-save triggered | Normal |

---

## Emergency Recovery

### If Everything Breaks

1. **Backup data:**
```bash
xcopy data backup\data /E /I
xcopy logs backup\logs /E /I
```

2. **Clean reinstall:**
```bash
# Delete virtual environment
rmdir /S venv

# Recreate
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

3. **Reset to defaults:**
```bash
git checkout scraper.py main.py
```

### Contact & Support

- Check GitHub issues
- Review `walkthrough.md` for examples
- Check `data-template.json` for data structure

---

## Quick Reference

### File Locations
- **Scraped Data:** `data/`
- **Logs:** `logs/`
- **Config:** `scraper.py` (lines 37-42)
- **UI:** `static/`

### Key Configuration
- **Rate Limit:** `scraper.py` line 42
- **Save Frequency:** `scraper.py` line 107
- **Server Port:** `main.py` last line
- **Timeout:** `scraper.py` line 50

### Quick Commands
```bash
# Start server
python main.py

# Install dependencies
pip install -r requirements.txt

# Check logs
type logs\*.log

# Validate JSON
python -m json.tool data\file.json
```
