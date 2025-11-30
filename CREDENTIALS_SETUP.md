# Reddit API Credentials Setup

## Quick Setup (5 minutes)

### Step 1: Create Reddit App
1. Go to: https://www.reddit.com/prefs/apps
2. Scroll to bottom and click **"Create App"** or **"Create Another App"**
3. Fill in the form:
   - **name**: `SubredditScraper` (or any name you like)
   - **App type**: Select **"script"**
   - **description**: (leave blank or add description)
   - **about url**: (leave blank)
   - **redirect uri**: `http://localhost:8080` (required but not used)
4. Click **"Create app"**

### Step 2: Get Your Credentials
After creating the app, you'll see:
- **client_id**: The string under your app name (looks like: `abc123XYZ456`)
- **client_secret**: The string next to "secret" (looks like: `xyz789ABC123def456`)

### Step 3: Set Environment Variables

**Windows PowerShell (Current Session):**
```powershell
$env:REDDIT_CLIENT_ID="your_client_id_here"
$env:REDDIT_CLIENT_SECRET="your_client_secret_here"
```

**Windows PowerShell (Permanent - Optional):**
```powershell
[System.Environment]::SetEnvironmentVariable('REDDIT_CLIENT_ID', 'your_client_id_here', 'User')
[System.Environment]::SetEnvironmentVariable('REDDIT_CLIENT_SECRET', 'your_client_secret_here', 'User')
```

**Windows CMD:**
```cmd
set REDDIT_CLIENT_ID=your_client_id_here
set REDDIT_CLIENT_SECRET=your_client_secret_here
```

### Step 4: Restart the Server
After setting the environment variables, restart the Python server:
1. Stop the current server (Ctrl+C in the terminal)
2. Run: `python main.py`
3. The scraper will now work!

## Verification
To check if credentials are set:
```powershell
echo $env:REDDIT_CLIENT_ID
echo $env:REDDIT_CLIENT_SECRET
```

If they show your values (not empty), you're ready to scrape!

## Troubleshooting

**"YOUR_CLIENT_ID" error:**
- You haven't set the environment variables yet
- Set them using the commands above

**"401 Unauthorized" error:**
- Your credentials are incorrect
- Double-check the client_id and client_secret from Reddit

**No data being scraped:**
- Make sure you restarted the server AFTER setting the environment variables
- Check the logs in the `logs/` folder for detailed error messages
