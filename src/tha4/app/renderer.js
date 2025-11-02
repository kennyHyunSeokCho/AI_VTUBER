const { ipcRenderer } = require('electron');

// UI Elements (널 안전 처리)
const overlayBtn = document.getElementById('overlayBtn') || null;
const voiceChangerBtn = document.getElementById('voiceChangerBtn') || null;
const voiceTrainBtn = document.getElementById('voiceTrainBtn') || null;
const statusText = document.getElementById('statusText') || null;
const logContent = document.getElementById('logContent') || null;

// State
let overlayRunning = false;

// Overlay button - 토글 기능 (존재 시에만 바인딩)
if (overlayBtn) {
    overlayBtn.addEventListener('click', () => {
        ipcRenderer.send('toggle-overlay');
        overlayRunning = !overlayRunning;
        if (overlayRunning) {
            overlayBtn.textContent = 'Hide Overlay';
            overlayBtn.style.backgroundColor = '#cc0066';
            if (statusText) statusText.textContent = 'Status: Overlay Running';
            addLog('Overlay started - 60 FPS', 'success');
        } else {
            overlayBtn.textContent = 'Show Overlay';
            overlayBtn.style.backgroundColor = '';
            if (statusText) statusText.textContent = 'Status: Ready';
            addLog('Overlay stopped', 'success');
        }
    });
}

// Overlay가 닫혔을 때 버튼 상태 초기화
ipcRenderer.on('overlay-closed', () => {
    overlayRunning = false;
    if (overlayBtn) {
        overlayBtn.textContent = 'Show Overlay';
        overlayBtn.style.backgroundColor = '';
    }
    if (statusText) statusText.textContent = 'Status: Ready';
    addLog('Overlay closed', 'success');
});

// Voice Changer button
if (voiceChangerBtn) {
    voiceChangerBtn.addEventListener('click', () => {
        ipcRenderer.send('start-voice-changer');
        addLog('Starting voice changer...', 'success');
    });
}

// 음성 학습(웹 UI) 버튼
if (voiceTrainBtn) {
    voiceTrainBtn.addEventListener('click', () => {
        ipcRenderer.send('open-voice-train');
        addLog('Opening voice training web UI...', 'success');
    });
}

// Log functions
function addLog(message, type = '') {
    if (!logContent) {
        // 로그인 페이지 등 로그 영역이 없을 때는 콘솔로 대체
        try { console.log(`[LOG] ${message}`); } catch (_) {}
        return;
    }
    const entry = document.createElement('div');
    entry.className = `log-entry ${type}`;
    const timestamp = new Date().toLocaleTimeString();
    entry.textContent = `[${timestamp}] ${message}`;
    logContent.appendChild(entry);
    logContent.scrollTop = logContent.scrollHeight;
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

// 프로세스 로그 집계 (backend / vite / overlay)
ipcRenderer.on('process-log', (event, payload) => {
    try {
        const { source, level, message } = payload || {};
        const tag = source ? `[${String(source).toUpperCase()}] ` : '';
        addLog(tag + String(message).trim(), level === 'error' ? 'error' : '');
    } catch (_) {
        // ignore
    }
});

ipcRenderer.on('voice-changer-started', () => {
    addLog('Voice changer started successfully!', 'success');
});

ipcRenderer.on('voice-changer-error', (event, error) => {
    addLog(`Voice changer error: ${error}`, 'error');
});

// Initialize (로그 영역이 있는 페이지에서만 시각화)
addLog('VTuber Controller initialized', 'success');
addLog('Click "Show Overlay" to start tracking', 'success');
addLog('Enhanced eye recognition ready (60 FPS)', 'success');