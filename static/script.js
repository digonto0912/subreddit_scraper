document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('scrapeForm');
    const startBtn = document.getElementById('startBtn');
    const stopBtn = document.getElementById('stopBtn');
    const statusIndicator = document.getElementById('statusIndicator');
    const postsCountEl = document.getElementById('postsCount');
    const commentsCountEl = document.getElementById('commentsCount');
    const errorCountEl = document.getElementById('errorCount');
    const elapsedTimeEl = document.getElementById('elapsedTime');
    const logOutput = document.getElementById('logOutput');
    const clearLogsBtn = document.getElementById('clearLogs');
    const workersPanel = document.getElementById('workers-panel');
    const workersGrid = document.getElementById('workers-grid');
    const activeWorkersCount = document.getElementById('active-workers-count');

    let eventSource = null;
    let startTime = null;
    let timerInterval = null;

    // Set default date to 1 year ago
    const today = new Date();
    const oneYearAgo = new Date(today.setFullYear(today.getFullYear() - 1));
    document.getElementById('targetDate').valueAsDate = oneYearAgo;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const subreddit = document.getElementById('subreddit').value;
        const targetDate = document.getElementById('targetDate').value;
        const numWorkers = parseInt(document.getElementById('numWorkers').value);

        if (!subreddit || !targetDate) {
            alert('Please fill in all fields');
            return;
        }

        // Reset UI
        resetStats();
        log('Starting scrape job...', 'system');
        setRunningState(true);
        
        // Show/hide workers panel based on mode
        if (numWorkers > 1) {
            workersPanel.style.display = 'block';
            workersGrid.innerHTML = ''; // Clear previous workers
            // Initialize worker cards
            for (let i = 0; i < numWorkers; i++) {
                updateWorkerCard(i, { status: 'idle', items_processed: 0 });
            }
        } else {
            workersPanel.style.display = 'none';
        }

        try {
            const response = await fetch('/api/scrape', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    subreddit, 
                    target_date: targetDate,
                    num_workers: numWorkers
                }),
            });

            const data = await response.json();
            
            if (data.job_id) {
                log(`Job started with ID: ${data.job_id}`, 'success');
                if (numWorkers > 1) {
                    log(`Running in distributed mode with ${numWorkers} workers`, 'info');
                }
                connectEventSource(data.job_id);
                startTimer();
            } else {
                throw new Error('No job ID returned');
            }
        } catch (error) {
            log(`Error starting job: ${error.message}`, 'error');
            setRunningState(false);
        }
    });

    stopBtn.addEventListener('click', async () => {
        try {
            await fetch('/api/stop', { method: 'POST' });
            log('Stop signal sent...', 'warning');
            stopBtn.disabled = true;
        } catch (error) {
            log(`Error stopping job: ${error.message}`, 'error');
        }
    });

    clearLogsBtn.addEventListener('click', () => {
        logOutput.innerHTML = '';
    });

    function connectEventSource(jobId) {
        if (eventSource) {
            eventSource.close();
        }

        eventSource = new EventSource(`/api/stream/${jobId}`);

        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);

            if (data.type === 'log') {
                log(data.message, data.level);
            } else if (data.type === 'stats') {
                updateStats(data.stats);
            } else if (data.type === 'workers_stats') {
                updateWorkersGrid(data.stats);
            } else if (data.type === 'complete') {
                log('Scraping completed successfully!', 'success');
                stopScraping();
            } else if (data.type === 'error') {
                log(`Error: ${data.message}`, 'error');
                stopScraping();
            }
        };

        eventSource.onerror = () => {
            log('Connection to server lost.', 'error');
            stopScraping();
        };
    }

    function updateWorkersGrid(stats) {
        // Update active count
        const workingCount = Object.values(stats).filter(w => w.status === 'working').length;
        activeWorkersCount.textContent = `${workingCount} Active`;
        
        // Update each worker card
        Object.entries(stats).forEach(([workerId, workerState]) => {
            updateWorkerCard(workerId, workerState);
        });
    }

    function updateWorkerCard(workerId, state) {
        let card = document.getElementById(`worker-${workerId}`);
        
        if (!card) {
            card = document.createElement('div');
            card.id = `worker-${workerId}`;
            card.className = 'worker-card';
            workersGrid.appendChild(card);
        }
        
        // Update classes based on status
        // Handle enum values which might be uppercase or lowercase
        const status = (state.status || 'idle').toLowerCase();
        card.className = `worker-card ${status}`;
        
        const itemsProcessed = state.items_processed || 0;
        const itemsFailed = state.items_failed || 0;
        
        card.innerHTML = `
            <div class="worker-header">
                <span>Worker ${workerId}</span>
                <span class="worker-status ${status}">${status}</span>
            </div>
            <div class="worker-info">
                ${itemsProcessed} items
            </div>
            <div class="worker-progress">
                ${itemsFailed > 0 ? `${itemsFailed} failed` : ''}
            </div>
        `;
    }

    function setRunningState(running) {
        startBtn.disabled = running;
        stopBtn.disabled = !running;
        document.getElementById('subreddit').disabled = running;
        document.getElementById('targetDate').disabled = running;
        document.getElementById('numWorkers').disabled = running;
        
        if (running) {
            statusIndicator.textContent = 'Running';
            statusIndicator.className = 'badge running';
        } else {
            statusIndicator.textContent = 'Idle';
            statusIndicator.className = 'badge idle';
        }
    }

    function stopScraping() {
        stopTimer();
        setRunningState(false);
        if (eventSource) {
            eventSource.close();
            eventSource = null;
        }
    }

    function log(message, level = 'info') {
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
