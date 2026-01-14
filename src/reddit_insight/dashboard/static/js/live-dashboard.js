/**
 * Live Dashboard - SSE Client for real-time subreddit monitoring
 *
 * Handles Server-Sent Events connection, UI updates, and activity visualization.
 */

const liveDashboard = {
    // State
    eventSource: null,
    subreddit: null,
    isConnected: false,
    startTime: null,
    reconnectAttempts: 0,
    maxReconnectAttempts: 5,
    reconnectDelay: 2000,

    // Stats
    stats: {
        posts: 0,
        spikes: 0,
    },

    // Activity chart
    chart: null,
    activityData: [],
    maxDataPoints: 30,

    /**
     * Initialize the dashboard
     */
    init: function() {
        this.initChart();
        this.updateUI();

        // Update connection time every second
        setInterval(() => {
            if (this.isConnected && this.startTime) {
                this.updateConnectionTime();
            }
        }, 1000);
    },

    /**
     * Initialize the activity chart
     */
    initChart: function() {
        const ctx = document.getElementById('activity-chart');
        if (!ctx) return;

        // Check for dark mode
        const isDark = document.documentElement.classList.contains('dark');
        const gridColor = isDark ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)';
        const textColor = isDark ? '#9CA3AF' : '#6B7280';

        this.chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Posts per minute',
                    data: [],
                    borderColor: 'rgb(59, 130, 246)',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    fill: true,
                    tension: 0.3,
                    pointRadius: 2,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: {
                    duration: 300,
                },
                scales: {
                    x: {
                        display: false,
                    },
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: gridColor,
                        },
                        ticks: {
                            color: textColor,
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false,
                    }
                }
            }
        });
    },

    /**
     * Connect to a subreddit's live stream
     */
    connect: function() {
        const input = document.getElementById('subreddit-input');
        const subreddit = input.value.trim().toLowerCase();

        if (!subreddit) {
            this.showAlert('Please enter a subreddit name');
            return;
        }

        // Disconnect existing connection
        if (this.eventSource) {
            this.disconnect();
        }

        this.subreddit = subreddit;
        this.setConnectionStatus('connecting');
        this.logEvent('info', `Connecting to r/${subreddit}...`);

        // Create EventSource
        const url = `/dashboard/live/stream/${subreddit}`;
        this.eventSource = new EventSource(url);

        this.eventSource.onopen = () => {
            this.isConnected = true;
            this.startTime = new Date();
            this.reconnectAttempts = 0;
            this.setConnectionStatus('connected');
            this.logEvent('success', `Connected to r/${subreddit}`);
            this.updateUI();
        };

        this.eventSource.onmessage = (event) => {
            this.handleMessage(event);
        };

        this.eventSource.onerror = (error) => {
            console.error('SSE Error:', error);
            this.handleError();
        };
    },

    /**
     * Disconnect from the live stream
     */
    disconnect: function() {
        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
        }

        this.isConnected = false;
        this.subreddit = null;
        this.startTime = null;
        this.setConnectionStatus('disconnected');
        this.logEvent('info', 'Disconnected');
        this.updateUI();
    },

    /**
     * Handle incoming SSE message
     */
    handleMessage: function(event) {
        try {
            const data = JSON.parse(event.data);
            // console.log('SSE message:', data);

            switch (data.type) {
                case 'connected':
                    // Connection confirmed
                    break;

                case 'new_post':
                    this.handleNewPost(data.data);
                    break;

                case 'activity_spike':
                    this.handleActivitySpike(data.data);
                    break;

                case 'status':
                    this.logEvent('info', data.data.message);
                    break;

                case 'heartbeat':
                    // Silent heartbeat
                    break;

                case 'error':
                    this.logEvent('error', data.message);
                    break;

                default:
                    console.log('Unknown message type:', data.type);
            }
        } catch (e) {
            console.error('Failed to parse SSE message:', e);
        }
    },

    /**
     * Handle new post update
     */
    handleNewPost: function(post) {
        this.stats.posts++;
        this.updateStats();

        // Add to activity data
        this.activityData.push({
            time: new Date(),
            count: 1,
        });
        this.updateChart();

        // Add to feed
        this.addPostToFeed(post);

        // Log event
        this.logEvent('post', `New post: ${post.title.substring(0, 50)}...`);

        // Hide placeholder
        const placeholder = document.getElementById('feed-placeholder');
        if (placeholder) {
            placeholder.style.display = 'none';
        }
    },

    /**
     * Handle activity spike alert
     */
    handleActivitySpike: function(data) {
        this.stats.spikes++;
        this.updateStats();

        // Show alert banner
        this.showAlert(data.message);

        // Log event
        this.logEvent('spike', `Activity spike: ${data.spike_factor}x`);
    },

    /**
     * Add a post to the live feed
     */
    addPostToFeed: function(post) {
        const feed = document.getElementById('live-feed');
        if (!feed) return;

        const postElement = document.createElement('div');
        postElement.className = 'p-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors animate-fade-in';
        postElement.innerHTML = `
            <div class="flex justify-between items-start">
                <div class="flex-1 min-w-0">
                    <a href="${post.url}" target="_blank" class="text-sm font-medium text-gray-900 dark:text-white hover:text-primary-600 dark:hover:text-primary-400 line-clamp-2">
                        ${this.escapeHtml(post.title)}
                    </a>
                    <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
                        by u/${this.escapeHtml(post.author)} &middot;
                        <span class="inline-flex items-center">
                            <svg class="w-3 h-3 mr-0.5" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" d="M4.5 10.5L12 3m0 0l7.5 7.5M12 3v18" />
                            </svg>
                            ${post.score}
                        </span>
                        &middot;
                        <span class="inline-flex items-center">
                            <svg class="w-3 h-3 mr-0.5" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.41 20.97a5.969 5.969 0 01-.474-.065 4.48 4.48 0 00.978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25z" />
                            </svg>
                            ${post.num_comments}
                        </span>
                    </p>
                </div>
                <span class="ml-2 text-xs text-gray-400 dark:text-gray-500 whitespace-nowrap">
                    ${this.formatTime(new Date())}
                </span>
            </div>
        `;

        // Insert at top
        feed.insertBefore(postElement, feed.firstChild);

        // Update count
        const countEl = document.getElementById('feed-count');
        if (countEl) {
            const count = feed.querySelectorAll('.p-4.hover\\:bg-gray-50').length;
            countEl.textContent = `(${count} posts)`;
        }

        // Limit feed size
        while (feed.children.length > 100) {
            feed.removeChild(feed.lastChild);
        }
    },

    /**
     * Clear the live feed
     */
    clearFeed: function() {
        const feed = document.getElementById('live-feed');
        if (!feed) return;

        feed.innerHTML = `
            <div class="p-8 text-center text-gray-500 dark:text-gray-400" id="feed-placeholder">
                <svg class="mx-auto h-12 w-12 text-gray-400 dark:text-gray-500" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M9.348 14.651a3.75 3.75 0 010-5.303m5.304 0a3.75 3.75 0 010 5.303m-7.425 2.122a6.75 6.75 0 010-9.546m9.546 0a6.75 6.75 0 010 9.546M5.106 18.894c-3.808-3.808-3.808-9.98 0-13.789m13.788 0c3.808 3.808 3.808 9.981 0 13.79M12 12h.008v.007H12V12zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z" />
                </svg>
                <p class="mt-2 text-sm">Connect to a subreddit to see live posts</p>
            </div>
        `;

        const countEl = document.getElementById('feed-count');
        if (countEl) {
            countEl.textContent = '(0 posts)';
        }
    },

    /**
     * Handle SSE connection error
     */
    handleError: function() {
        if (!this.isConnected) return;

        this.reconnectAttempts++;

        if (this.reconnectAttempts <= this.maxReconnectAttempts) {
            this.setConnectionStatus('reconnecting');
            this.logEvent('warning', `Connection lost. Reconnecting (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);

            setTimeout(() => {
                if (this.subreddit) {
                    this.connect();
                }
            }, this.reconnectDelay * this.reconnectAttempts);
        } else {
            this.disconnect();
            this.logEvent('error', 'Failed to reconnect. Please try again.');
        }
    },

    /**
     * Update the activity chart
     */
    updateChart: function() {
        if (!this.chart) return;

        // Aggregate data into time buckets
        const now = new Date();
        const bucketSize = 60000; // 1 minute buckets

        // Get counts per minute for last 30 minutes
        const labels = [];
        const data = [];

        for (let i = this.maxDataPoints - 1; i >= 0; i--) {
            const bucketEnd = new Date(now.getTime() - i * bucketSize);
            const bucketStart = new Date(bucketEnd.getTime() - bucketSize);

            const count = this.activityData.filter(d =>
                d.time >= bucketStart && d.time < bucketEnd
            ).reduce((sum, d) => sum + d.count, 0);

            labels.push(this.formatTime(bucketEnd));
            data.push(count);
        }

        this.chart.data.labels = labels;
        this.chart.data.datasets[0].data = data;
        this.chart.update('none');
    },

    /**
     * Log an event to the event log
     */
    logEvent: function(type, message) {
        const log = document.getElementById('event-log');
        if (!log) return;

        // Remove placeholder
        const placeholder = log.querySelector('.text-center');
        if (placeholder) {
            placeholder.remove();
        }

        const colors = {
            info: 'text-gray-600 dark:text-gray-400',
            success: 'text-green-600 dark:text-green-400',
            warning: 'text-yellow-600 dark:text-yellow-400',
            error: 'text-red-600 dark:text-red-400',
            post: 'text-blue-600 dark:text-blue-400',
            spike: 'text-orange-600 dark:text-orange-400',
        };

        const icons = {
            info: 'M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z',
            success: 'M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
            warning: 'M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z',
            error: 'M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z',
            post: 'M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z',
            spike: 'M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z',
        };

        const eventEl = document.createElement('div');
        eventEl.className = `flex items-start gap-2 ${colors[type] || colors.info}`;
        eventEl.innerHTML = `
            <svg class="w-4 h-4 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" d="${icons[type] || icons.info}" />
            </svg>
            <span class="flex-1 break-words">${this.escapeHtml(message)}</span>
            <span class="text-xs text-gray-400 dark:text-gray-500 whitespace-nowrap">${this.formatTime(new Date())}</span>
        `;

        // Insert at top
        log.insertBefore(eventEl, log.firstChild);

        // Limit log size
        while (log.children.length > 50) {
            log.removeChild(log.lastChild);
        }
    },

    /**
     * Set the connection status indicator
     */
    setConnectionStatus: function(status) {
        const statusEl = document.getElementById('connection-status');
        if (!statusEl) return;

        const statuses = {
            disconnected: {
                text: 'Disconnected',
                class: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300',
            },
            connecting: {
                text: 'Connecting...',
                class: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300',
            },
            connected: {
                text: 'Connected',
                class: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300',
            },
            reconnecting: {
                text: 'Reconnecting...',
                class: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300',
            },
        };

        const config = statuses[status] || statuses.disconnected;
        statusEl.textContent = config.text;
        statusEl.className = `ml-3 inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${config.class}`;
    },

    /**
     * Show an alert banner
     */
    showAlert: function(message) {
        const banner = document.getElementById('alert-banner');
        const messageEl = document.getElementById('alert-message');

        if (banner && messageEl) {
            messageEl.textContent = message;
            banner.classList.remove('hidden');

            // Auto-hide after 10 seconds
            setTimeout(() => {
                banner.classList.add('hidden');
            }, 10000);
        }
    },

    /**
     * Update stats display
     */
    updateStats: function() {
        const postsEl = document.getElementById('stat-posts');
        const spikesEl = document.getElementById('stat-spikes');

        if (postsEl) postsEl.textContent = this.stats.posts;
        if (spikesEl) spikesEl.textContent = this.stats.spikes;
    },

    /**
     * Update connection time display
     */
    updateConnectionTime: function() {
        const timeEl = document.getElementById('stat-time');
        if (!timeEl || !this.startTime) return;

        const elapsed = Math.floor((new Date() - this.startTime) / 1000);
        const minutes = Math.floor(elapsed / 60);
        const seconds = elapsed % 60;

        timeEl.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    },

    /**
     * Update UI based on connection state
     */
    updateUI: function() {
        const btnConnect = document.getElementById('btn-connect');
        const btnDisconnect = document.getElementById('btn-disconnect');
        const input = document.getElementById('subreddit-input');

        if (btnConnect) btnConnect.disabled = this.isConnected;
        if (btnDisconnect) btnDisconnect.disabled = !this.isConnected;
        if (input) input.disabled = this.isConnected;
    },

    /**
     * Format time for display
     */
    formatTime: function(date) {
        return date.toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false,
        });
    },

    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml: function(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },
};

// Add fade-in animation
if (typeof document !== 'undefined') {
    const style = document.createElement('style');
    style.textContent = `
        @keyframes fade-in {
            from { opacity: 0; transform: translateY(-10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .animate-fade-in {
            animation: fade-in 0.3s ease-out;
        }
    `;
    document.head.appendChild(style);
}
