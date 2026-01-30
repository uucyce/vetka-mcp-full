/**
 * MCP Console - JavaScript Client
 *
 * @file mcp_console.js
 * @status ACTIVE
 * @phase Phase 80.41
 * @created 2026-01-22
 *
 * Displays MCP agent communications in real-time.
 * Connects to FastAPI backend via Socket.IO and REST API.
 */

class MCPConsole {
    constructor() {
        this.logs = [];
        this.socket = null;
        this.container = null;
        this.initialized = false;
    }

    /**
     * Initialize MCP Console UI
     */
    init() {
        if (this.initialized) return;

        // Create console container
        this.createConsoleUI();

        // Connect to Socket.IO
        this.connectSocket();

        // Load initial history
        this.loadHistory();

        this.initialized = true;
        console.log('[MCP Console] Initialized');
    }

    /**
     * Create console UI elements
     */
    createConsoleUI() {
        // Check if container already exists
        if (document.getElementById('mcp-console')) {
            this.container = document.getElementById('mcp-console');
            return;
        }

        // Create main container
        const consoleDiv = document.createElement('div');
        consoleDiv.id = 'mcp-console';
        consoleDiv.className = 'mcp-console hidden';
        consoleDiv.innerHTML = `
            <div class="mcp-console-header">
                <h3>MCP Debug Console</h3>
                <div class="mcp-console-controls">
                    <button id="mcp-save-btn" class="mcp-btn" title="Save logs">💾 Save</button>
                    <button id="mcp-clear-btn" class="mcp-btn" title="Clear logs">🗑️ Clear</button>
                    <button id="mcp-close-btn" class="mcp-btn" title="Close console">✖️</button>
                </div>
            </div>
            <div class="mcp-console-stats">
                <span id="mcp-stats-requests">Requests: 0</span>
                <span id="mcp-stats-responses">Responses: 0</span>
                <span id="mcp-stats-tokens">Tokens: 0</span>
            </div>
            <div id="mcp-log-container" class="mcp-log-container"></div>
        `;

        document.body.appendChild(consoleDiv);
        this.container = consoleDiv;

        // Add toggle button to top bar
        const topBar = document.getElementById('vis-mode-icons');
        if (topBar) {
            const toggleBtn = document.createElement('button');
            toggleBtn.id = 'mcp-toggle-btn';
            toggleBtn.innerHTML = '🤖 MCP';
            toggleBtn.title = 'Toggle MCP Console';
            toggleBtn.onclick = () => this.toggle();
            topBar.appendChild(toggleBtn);
        }

        // Attach event listeners
        document.getElementById('mcp-save-btn').onclick = () => this.saveLogs();
        document.getElementById('mcp-clear-btn').onclick = () => this.clearLogs();
        document.getElementById('mcp-close-btn').onclick = () => this.hide();
    }

    /**
     * Connect to Socket.IO for real-time updates
     */
    connectSocket() {
        if (typeof io === 'undefined') {
            console.warn('[MCP Console] Socket.IO not available');
            return;
        }

        // Use existing socket or create new one
        if (window.socket) {
            this.socket = window.socket;
        } else {
            this.socket = io();
            window.socket = this.socket;
        }

        // Listen for MCP log events
        this.socket.on('mcp_log', (data) => {
            this.addLog(data);
        });

        console.log('[MCP Console] Socket.IO connected');
    }

    /**
     * Load initial log history from API
     */
    async loadHistory() {
        try {
            const response = await fetch('/api/mcp-console/history?limit=100');
            const data = await response.json();

            if (data.success && data.logs) {
                this.logs = data.logs;
                this.renderLogs();
                this.updateStats();
            }
        } catch (error) {
            console.error('[MCP Console] Failed to load history:', error);
        }
    }

    /**
     * Add new log entry
     */
    addLog(logEntry) {
        this.logs.push(logEntry);

        // Keep only last 100 entries in UI
        if (this.logs.length > 100) {
            this.logs = this.logs.slice(-100);
        }

        this.renderLogs();
        this.updateStats();
    }

    /**
     * Render all logs in the container
     */
    renderLogs() {
        const logContainer = document.getElementById('mcp-log-container');
        if (!logContainer) return;

        logContainer.innerHTML = '';

        // Group request/response pairs
        const pairs = this.groupRequestResponsePairs();

        pairs.forEach(pair => {
            const pairElement = this.createLogPairElement(pair);
            logContainer.appendChild(pairElement);
        });

        // Auto-scroll to bottom
        logContainer.scrollTop = logContainer.scrollHeight;
    }

    /**
     * Group logs into request/response pairs
     */
    groupRequestResponsePairs() {
        const pairs = [];
        const requestMap = new Map();

        this.logs.forEach(log => {
            if (log.type === 'request') {
                requestMap.set(log.id, { request: log, response: null });
            } else if (log.type === 'response') {
                // Find matching request
                const requestId = log.id.replace('res-', 'req-');
                if (requestMap.has(requestId)) {
                    requestMap.get(requestId).response = log;
                } else {
                    // Standalone response
                    pairs.push({ request: null, response: log });
                }
            }
        });

        // Convert map to array
        requestMap.forEach(pair => pairs.push(pair));

        return pairs;
    }

    /**
     * Create DOM element for request/response pair
     */
    createLogPairElement(pair) {
        const pairDiv = document.createElement('div');
        pairDiv.className = 'mcp-log-pair';

        // Request section
        if (pair.request) {
            const reqDiv = document.createElement('div');
            reqDiv.className = 'mcp-log-request';

            const timestamp = new Date(pair.request.timestamp * 1000).toLocaleTimeString();
            const agent = pair.request.agent || 'Unknown';
            const tool = pair.request.tool || 'Unknown';
            const model = pair.request.model || 'N/A';

            reqDiv.innerHTML = `
                <div class="mcp-log-header">
                    <span class="mcp-log-type">REQUEST</span>
                    <span class="mcp-log-time">${timestamp}</span>
                </div>
                <div class="mcp-log-info">
                    <span><strong>Agent:</strong> ${agent}</span>
                    <span><strong>Tool:</strong> ${tool}</span>
                    <span><strong>Model:</strong> ${model}</span>
                </div>
                <div class="mcp-log-args">
                    <pre>${JSON.stringify(pair.request.arguments || {}, null, 2)}</pre>
                </div>
            `;

            pairDiv.appendChild(reqDiv);
        }

        // Response section
        if (pair.response) {
            const resDiv = document.createElement('div');
            resDiv.className = 'mcp-log-response';

            const timestamp = new Date(pair.response.timestamp * 1000).toLocaleTimeString();
            const duration = pair.response.duration_ms ? `${pair.response.duration_ms.toFixed(0)}ms` : 'N/A';
            const tokens = pair.response.tokens || 0;
            const hasError = !!pair.response.error;

            resDiv.innerHTML = `
                <div class="mcp-log-header ${hasError ? 'error' : 'success'}">
                    <span class="mcp-log-type">RESPONSE</span>
                    <span class="mcp-log-time">${timestamp}</span>
                    <span class="mcp-log-duration">${duration}</span>
                    <span class="mcp-log-tokens">${tokens} tokens</span>
                </div>
                <div class="mcp-log-result">
                    ${hasError ?
                        `<div class="mcp-error">${pair.response.error}</div>` :
                        `<pre>${this.formatResult(pair.response.result)}</pre>`
                    }
                </div>
            `;

            pairDiv.appendChild(resDiv);
        }

        return pairDiv;
    }

    /**
     * Format result for display
     */
    formatResult(result) {
        if (!result) return 'null';

        if (typeof result === 'string') {
            // Truncate long strings
            return result.length > 500 ? result.slice(0, 500) + '...' : result;
        }

        // Format as JSON
        const jsonStr = JSON.stringify(result, null, 2);
        return jsonStr.length > 500 ? jsonStr.slice(0, 500) + '\n...' : jsonStr;
    }

    /**
     * Update statistics display
     */
    async updateStats() {
        try {
            const response = await fetch('/api/mcp-console/stats');
            const data = await response.json();

            if (data.success) {
                document.getElementById('mcp-stats-requests').textContent = `Requests: ${data.requests}`;
                document.getElementById('mcp-stats-responses').textContent = `Responses: ${data.responses}`;
                document.getElementById('mcp-stats-tokens').textContent = `Tokens: ${data.total_tokens}`;
            }
        } catch (error) {
            console.error('[MCP Console] Failed to update stats:', error);
        }
    }

    /**
     * Save logs to file
     */
    async saveLogs() {
        try {
            const sessionId = prompt('Enter session ID (or leave blank):', 'session');
            if (sessionId === null) return;

            const response = await fetch('/api/mcp-console/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ session_id: sessionId || 'default' })
            });

            const data = await response.json();

            if (data.success) {
                alert(`Logs saved to: ${data.filename}\nTotal: ${data.log_count} entries`);
            } else {
                alert('Failed to save logs');
            }
        } catch (error) {
            console.error('[MCP Console] Failed to save logs:', error);
            alert('Error saving logs');
        }
    }

    /**
     * Clear all logs
     */
    async clearLogs() {
        if (!confirm('Clear all MCP logs?')) return;

        try {
            const response = await fetch('/api/mcp-console/clear', {
                method: 'DELETE'
            });

            const data = await response.json();

            if (data.success) {
                this.logs = [];
                this.renderLogs();
                this.updateStats();
                console.log('[MCP Console] Cleared', data.cleared_count, 'logs');
            }
        } catch (error) {
            console.error('[MCP Console] Failed to clear logs:', error);
        }
    }

    /**
     * Toggle console visibility
     */
    toggle() {
        if (this.container.classList.contains('hidden')) {
            this.show();
        } else {
            this.hide();
        }
    }

    /**
     * Show console
     */
    show() {
        this.container.classList.remove('hidden');
    }

    /**
     * Hide console
     */
    hide() {
        this.container.classList.add('hidden');
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.mcpConsole = new MCPConsole();
    window.mcpConsole.init();
});
