# Quick Start Guide - For Beginners

This guide will help you get the Subreddit Scraper running in 5 minutes, even if you've never used Python before.

## Prerequisites

### 1. Install Python

**Windows:**
1. Go to https://www.python.org/downloads/
2. Download Python 3.8 or higher
3. Run the installer
4. ✅ **IMPORTANT:** Check "Add Python to PATH" during installation

**Verify Installation:**
```bash
python --version
```
Should show: `Python 3.x.x`

### 2. Install Git (Optional)

Only needed if you want to clone the repository.

**Windows:**
1. Go to https://git-scm.com/downloads
2. Download and install

---

## Installation

### Step 1: Get the Code

**Option A: Download ZIP**
1. Download the project as ZIP
2. Extract to a folder (e.g., `C:\subreddit_scraper`)

**Option B: Clone with Git**
```bash
git clone <repository-url>
cd subreddit_scraper
```

### Step 2: Open Terminal

**Windows:**
1. Press `Win + R`
2. Type `cmd` and press Enter
3. Navigate to project folder:
```bash
cd "C:\path\to\subreddit_scraper"
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

Wait for installation to complete (1-2 minutes).

---

## Running the Scraper

### Step 1: Start the Server

```bash
python main.py
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

✅ **Server is running!**

### Step 2: Open the Web Interface

1. Open your web browser (Chrome, Firefox, Edge)
2. Go to: `http://localhost:8000`

You should see the Subreddit Scraper interface.

### Step 3: Start Scraping

1. **Enter Subreddit Name:**
   - Type: `python` (or any subreddit name)
   - You can also use: `r/python` or full URL

2. **Select Target Date:**
   - Click the date field
   - Choose how far back you want to scrape
   - Example: Select yesterday's date

3. **Click "Start Scraping"**
   - Watch the live stats update
   - See logs in real-time

4. **Wait for Completion**
   - The scraper will run until it reaches the target date
   - You can click "Stop" anytime

---

## Finding Your Data

### Scraped Data

**Location:** `data` folder in the project directory

**File Format:** `{subreddit}_{date}_{timestamp}.json`

**Example:**
```
data/
└── python_20251129_20251130_152409.json
```

**Open with:**
- Any text editor (Notepad, VS Code, etc.)
- Or use: `python -m json.tool data\filename.json` for formatted view

### Logs

**Location:** `logs` folder

**File Format:** `{subreddit}_{date}_{timestamp}.log`

**Example:**
```
logs/
└── python_20251129_20251130_152409.log
```

---

## Common First-Time Issues

### Issue: "python is not recognized"

**Solution:**
- Python not installed or not in PATH
- Reinstall Python and check "Add to PATH"
- Or use full path: `C:\Python312\python.exe main.py`

### Issue: "pip is not recognized"

**Solution:**
```bash
python -m pip install -r requirements.txt
```

### Issue: "Port 8000 already in use"

**Solution:**
```bash
# Find what's using port 8000
netstat -ano | findstr :8000

# Kill the process (replace <PID> with actual number)
taskkill /F /PID <PID>
```

### Issue: Browser shows "Can't reach this page"

**Solution:**
- Make sure server is running (check terminal)
- Try `http://127.0.0.1:8000` instead
- Check firewall settings

### Issue: No data being collected

**Solution:**
- Check internet connection
- Verify subreddit name is correct
- Make sure target date is in the past
- Check logs folder for error messages

---

## Understanding the Interface

### Input Fields

**Subreddit URL or Name:**
- Accepts: `python`, `r/python`, or `https://reddit.com/r/python`
- Case-insensitive

**Target Date:**
- The oldest post you want to scrape
- Scraper works backwards from newest to this date

### Live Stats

**Posts Scraped:**
- Number of posts collected so far

**Comments Scraped:**
- Total comments from all posts

**Errors:**
- Number of errors encountered (should stay at 0)

**Elapsed Time:**
- How long the scraper has been running

### System Logs

Real-time log messages showing:
- What the scraper is doing
- Posts being scraped
- Any errors or warnings

---

## Tips for Beginners

### 1. Start Small

For your first scrape:
- Choose a small subreddit
- Set target date to yesterday
- This will scrape just 1 day of posts

### 2. Check the Data

After scraping:
1. Open the `data` folder
2. Find the JSON file
3. Open with a text editor
4. Verify the data looks correct

### 3. Read the Logs

If something goes wrong:
1. Open the `logs` folder
2. Find the latest log file
3. Look for ERROR messages
4. See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for solutions

### 4. Stop Safely

To stop the scraper:
- Click "Stop" button in UI (recommended)
- Or press `Ctrl+C` in terminal

### 5. Restart Fresh

If things get messy:
1. Stop the server (`Ctrl+C`)
2. Delete `data` and `logs` folders (optional)
3. Start server again: `python main.py`

---

## Next Steps

### Learn More

- **[README.md](README.md)** - Full documentation
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Solve any issues
- **[API_DOCUMENTATION.md](API_DOCUMENTATION.md)** - For developers

### Scrape Larger Datasets

Once comfortable:
1. Increase date range (e.g., last month)
2. Try larger subreddits
3. Scrape multiple subreddits

### Customize

Edit `scraper.py` to:
- Change rate limiting
- Modify data structure
- Add custom processing

See [API_DOCUMENTATION.md](API_DOCUMENTATION.md) for examples.

---

## Quick Reference Card

### Start Server
```bash
python main.py
```

### Open UI
```
http://localhost:8000
```

### Stop Server
```
Ctrl + C
```

### Check Data
```bash
dir data
```

### Check Logs
```bash
type logs\*.log
```

### Reinstall
```bash
pip install --force-reinstall -r requirements.txt
```

---

## Getting Help

1. **Check logs** - `logs` folder
2. **Read troubleshooting** - [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
3. **Verify setup** - Python version, dependencies
4. **Test internet** - `ping reddit.com`

---

## Success Checklist

✅ Python installed and in PATH  
✅ Dependencies installed (`pip install -r requirements.txt`)  
✅ Server starts without errors  
✅ UI loads in browser  
✅ Can enter subreddit and date  
✅ Scraping starts and shows progress  
✅ Data appears in `data` folder  
✅ Logs appear in `logs` folder  

**If all checked, you're ready to scrape!** 🎉

---

## Example Workflow

```bash
# 1. Navigate to project
cd "C:\subreddit_scraper"

# 2. Start server
python main.py

# 3. Open browser
# Go to: http://localhost:8000

# 4. Enter details
# Subreddit: python
# Date: (yesterday)

# 5. Click "Start Scraping"

# 6. Wait for completion

# 7. Check data
dir data

# 8. Stop server
# Press Ctrl+C in terminal
```

---

**You're all set! Happy scraping!** 🚀
