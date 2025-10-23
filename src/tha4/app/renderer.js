const { ipcRenderer } = require('electron');

// UI Elements
const overlayBtn = document.getElementById('overlayBtn');
const voiceChangerBtn = document.getElementById('voiceChangerBtn');
const statusText = document.getElementById('statusText');
const logContent = document.getElementById('logContent');

// State
let overlayRunning = false;

// Overlay button - 토글 기능
overlayBtn.addEventListener('click', () => {
    ipcRenderer.send('toggle-overlay');
    overlayRunning = !overlayRunning;
    
    if (overlayRunning) {
        overlayBtn.textContent = 'Hide Overlay';
        overlayBtn.style.backgroundColor = '#cc0066';
        statusText.textContent = 'Status: Overlay Running';
        addLog('Overlay started - 60 FPS', 'success');
    } else {
        overlayBtn.textContent = 'Show Overlay';
        overlayBtn.style.backgroundColor = '';
        statusText.textContent = 'Status: Ready';
        addLog('Overlay stopped', 'success');
    }
});

// Overlay가 닫혔을 때 버튼 상태 초기화
ipcRenderer.on('overlay-closed', () => {
    overlayRunning = false;
    overlayBtn.textContent = 'Show Overlay';
    overlayBtn.style.backgroundColor = '';
    statusText.textContent = 'Status: Ready';
    addLog('Overlay closed', 'success');
});

// Voice Changer button
voiceChangerBtn.addEventListener('click', () => {
    ipcRenderer.send('start-voice-changer');
    addLog('Starting voice changer...', 'success');
});

// Log functions
function addLog(message, type = '') {
    const entry = document.createElement('div');
    entry.className = `log-entry ${type}`;
    const timestamp = new Date().toLocaleTimeString();
    entry.textContent = `[${timestamp}] ${message}`;
    logContent.appendChild(entry);
    logContent.scrollTop = logContent.scrollHeight;
    
    // Keep only last 50 entries
    while (logContent.children.length > 50) {
        logContent.removeChild(logContent.firstChild);
    }
}

// IPC listeners
ipcRenderer.on('python-log', (event, data) => {
    const lines = data.trim().split('\n');
    lines.forEach(line => {
        if (line.trim()) {
            addLog(line);
        }
    });
});

ipcRenderer.on('python-error', (event, data) => {
    addLog(`Error: ${data}`, 'error');
});

ipcRenderer.on('voice-changer-started', () => {
    addLog('Voice changer started successfully!', 'success');
});

ipcRenderer.on('voice-changer-error', (event, error) => {
    addLog(`Voice changer error: ${error}`, 'error');
});

// Initialize
addLog('VTuber Controller initialized', 'success');
addLog('Click "Show Overlay" to start tracking', 'success');
addLog('Enhanced eye recognition ready (60 FPS)', 'success');