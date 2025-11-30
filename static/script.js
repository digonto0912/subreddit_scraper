document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('scrapeForm');
    const startBtn = document.getElementById('startBtn');
    const stopBtn = document.getElementById('stopBtn');
    const statusIndicator = document.getElementById('statusIndicator');
    const logOutput = document.getElementById('logOutput');
    const clearLogsBtn = document.getElementById('clearLogs');
    
    // Stats elements
    const postsCountEl = document.getElementById('postsCount');
    const commentsCountEl = document.getElementById('commentsCount');
    const errorCountEl = document.getElementById('errorCount');
    const elapsedTimeEl = document.getElementById('elapsedTime');

    let isScraping = false;
    let startTime;
    let timerInterval;
    let eventSource;

    // Set default date to 1 year ago
    const today = new Date();
    const oneYearAgo = new Date(today.setFullYear(today.getFullYear() - 1));
    document.getElementById('targetDate').valueAsDate = oneYearAgo;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (isScraping) return;

        const subreddit = document.getElementById('subreddit').value;
        const targetDate = document.getElementById('targetDate').value;

        startScraping(subreddit, targetDate);
    });

    stopBtn.addEventListener('click', () => {
        if (!isScraping) return;
        stopScraping();
    });

    clearLogsBtn.addEventListener('click', () => {
        logOutput.innerHTML = '';
        addLog('Logs cleared.', 'system');
    });

    async function startScraping(subreddit, targetDate) {
        isScraping = true;
        updateUIState(true);
        resetStats();
        startTimer();
        addLog(`Starting scrape for ${subreddit} until ${targetDate}...`, 'info');

        try {
            // Start the scraping process via API
            const response = await fetch('/api/scrape', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ subreddit, target_date: targetDate }),
            });

            if (!response.ok) {
                throw new Error(`Failed to start: ${response.statusText}`);
            }

            const data = await response.json();
            addLog(`Scraping job started. ID: ${data.job_id}`, 'success');
            
            // Connect to event stream for logs and updates
            connectToEventStream(data.job_id);

        } catch (error) {
            addLog(`Error: ${error.message}`, 'error');
            stopScraping(false); // Stop but keep UI in error state if needed, or just reset
        }
    }

    async function stopScraping(notifyServer = true) {
        isScraping = false;
        stopTimer();
        updateUIState(false);
        
        if (eventSource) {
            eventSource.close();
            eventSource = null;
        }

        if (notifyServer) {
            try {
                await fetch('/api/stop', { method: 'POST' });
                addLog('Scraping stopped by user.', 'warning');
            } catch (error) {
                addLog(`Error stopping: ${error.message}`, 'error');
            }
        }
    }

    function connectToEventStream(jobId) {
        // Close existing connection if any
        if (eventSource) eventSource.close();

        eventSource = new EventSource(`/api/stream/${jobId}`);

        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            if (data.type === 'log') {
                addLog(data.message, data.level);
            } else if (data.type === 'stats') {
                updateStats(data.stats);
            } else if (data.type === 'complete') {
                addLog('Scraping completed successfully!', 'success');
                stopScraping(false);
                statusIndicator.textContent = 'Completed';
                statusIndicator.className = 'badge completed';
            } else if (data.type === 'error') {
                addLog(`Scraper Error: ${data.message}`, 'error');
                stopScraping(false);
                statusIndicator.textContent = 'Error';
                statusIndicator.className = 'badge error';
            }
        };

        eventSource.onerror = () => {
            addLog('Lost connection to server.', 'error');
            eventSource.close();
            // Optional: retry logic
        };
    }

    function updateUIState(running) {
        startBtn.disabled = running;
        stopBtn.disabled = !running;
        document.getElementById('subreddit').disabled = running;
        document.getElementById('targetDate').disabled = running;
        
        if (running) {
            statusIndicator.textContent = 'Running';
            statusIndicator.className = 'badge running';
        } else {
            // If explicitly stopped, we might want to show Idle or Stopped. 
            // If completed, it's handled in onmessage.
            if (statusIndicator.textContent === 'Running') {
                statusIndicator.textContent = 'Idle';
                statusIndicator.className = 'badge idle';
            }
        }
    }

    function addLog(message, level = 'info') {
        const entry = document.createElement('div');
        entry.className = `log-entry ${level}`;
        const time = new Date().toLocaleTimeString();
        entry.textContent = `[${time}] ${message}`;
        logOutput.appendChild(entry);
        logOutput.scrollTop = logOutput.scrollHeight;
    }

    function updateStats(stats) {
        if (stats.posts !== undefined) postsCountEl.textContent = stats.posts.toLocaleString();
        if (stats.comments !== undefined) commentsCountEl.textContent = stats.comments.toLocaleString();
        if (stats.errors !== undefined) errorCountEl.textContent = stats.errors;
    }

    function resetStats() {
        postsCountEl.textContent = '0';
        commentsCountEl.textContent = '0';
        errorCountEl.textContent = '0';
        elapsedTimeEl.textContent = '00:00:00';
    }

    function startTimer() {
        startTime = Date.now();
        timerInterval = setInterval(() => {
            const elapsed = Date.now() - startTime;
            const date = new Date(elapsed);
            const h = String(Math.floor(elapsed / 3600000)).padStart(2, '0');
            const m = String(date.getUTCMinutes()).padStart(2, '0');
            const s = String(date.getUTCSeconds()).padStart(2, '0');
            elapsedTimeEl.textContent = `${h}:${m}:${s}`;
        }, 1000);
    }

    function stopTimer() {
        clearInterval(timerInterval);
    }
});
