import asyncio
import json
import uuid
import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Dict

app = FastAPI()

# Get the directory of the current script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Store active jobs
active_jobs: Dict[str, "ScraperJob"] = {}

class ScrapeRequest(BaseModel):
    subreddit: str
    target_date: str

class ScraperJob:
    def __init__(self, job_id, subreddit, target_date):
        self.job_id = job_id
        self.subreddit = subreddit
        self.target_date = target_date
        self.is_running = True
        self.queue = asyncio.Queue()
        self.scraper = None  # Will be set when scraper starts

    async def add_log(self, message, level="info"):
        await self.queue.put(json.dumps({
            "type": "log",
            "message": message,
            "level": level
        }))

    async def update_stats(self, stats):
        await self.queue.put(json.dumps({
            "type": "stats",
            "stats": stats
        }))

    async def complete(self):
        self.is_running = False
        await self.queue.put(json.dumps({"type": "complete"}))

    async def error(self, message):
        self.is_running = False
        await self.queue.put(json.dumps({
            "type": "error",
            "message": message
        }))

@app.get("/")
async def read_root():
    with open(os.path.join(STATIC_DIR, "index.html"), "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.post("/api/scrape")
async def start_scrape(request: ScrapeRequest):
    job_id = str(uuid.uuid4())
    
    # Clean subreddit name (remove r/ prefix and URL parts if present)
    subreddit = request.subreddit.strip()
    if "reddit.com/r/" in subreddit:
        subreddit = subreddit.split("reddit.com/r/")[1].split("/")[0]
    elif subreddit.startswith("r/"):
        subreddit = subreddit[2:]
    
    job = ScraperJob(job_id, subreddit, request.target_date)
    active_jobs[job_id] = job
    
    # Start the scraping task in background
    asyncio.create_task(run_scrape_task(job))
    
    return {"job_id": job_id, "status": "started"}

@app.post("/api/stop")
async def stop_scrape():
    # Stop all active jobs
    for job in active_jobs.values():
        job.is_running = False
        if job.scraper:
            job.scraper.stop()
        await job.add_log("Stopping job...", "warning")
    return {"status": "stopped"}

@app.get("/api/stream/{job_id}")
async def stream_logs(job_id: str):
    async def event_generator():
        job = active_jobs.get(job_id)
        if not job:
            yield f"data: {json.dumps({'type': 'error', 'message': 'Job not found'})}\n\n"
            return

        try:
            while True:
                # If job is finished and queue is empty, break
                if not job.is_running and job.queue.empty():
                    break
                
                # Wait for new data
                data = await job.queue.get()
                yield f"data: {data}\n\n"
        except asyncio.CancelledError:
            pass

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# Real scraping task
async def run_scrape_task(job: ScraperJob):
    from scraper import SubredditScraper
    from logger import setup_logger
    
    # Setup logger
    session_name = f"{job.subreddit}_{job.target_date.replace('-', '')}"
    logger, log_file = setup_logger(session_name)
    
    # Callback to send updates to the UI
    async def update_callback(message, level="info"):
        if isinstance(message, dict):
            # Stats update
            await job.update_stats(message)
        else:
            # Log message
            await job.add_log(message, level)
    
    try:
        # Initialize and run scraper
        scraper = SubredditScraper(
            subreddit_name=job.subreddit,
            target_date_str=job.target_date,
            job_id=job.job_id,
            logger=logger,
            update_callback=update_callback
        )
        
        # Store scraper reference in job for stop functionality
        job.scraper = scraper
        
        await scraper.run()
        
        if job.is_running:
            await job.complete()
            
    except Exception as e:
        logger.error(f"Scraper task failed: {e}")
        await job.error(str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
