const { ipcRenderer } = require('electron');

import { toggleSignIn, handleSignUp } from './login.js'
import {
  callGenerateTha4ModelFunction,
  callGenerateImageFunction,
  downloadUserImage,
  downloadModel,
} from './image_model.js';

// UI Elements
const overlayBtn = document.getElementById('overlayBtn');
const voiceChangerBtn = document.getElementById('voiceChangerBtn');
const voiceTrainBtn = document.getElementById('voiceTrainBtn');
const statusText = document.getElementById('statusText');
const logContent = document.getElementById('logContent');

const loginBtn = document.getElementById('loginBtn');
const modelRequestBtn = document.getElementById('modelRequestBtn');
const signUpBtn = document.getElementById('signUpBtn');
const sendImagePromptBtn = document.getElementById('sendImagePrompt');
const imagePromptInput = document.getElementById('imagePromptInput')
const downloadImageBtn = document.getElementById('downloadImageBtn');
const modelDownloadBtn = document.getElementById('modelDownloadBtn');

const mainScreen = document.getElementById('mainScreen');
const imageRequestScreen = document.getElementById('imageRequestScreen');

const gotoImageRequestScreenBtn = document.getElementById('gotoImageRequestScreenBtn');
const gotoMainScreenBtn = document.getElementById('gotoMainScreenBtn');

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

// 음성 학습(웹 UI) 버튼
voiceTrainBtn.addEventListener('click', () => {
  ipcRenderer.send('open-voice-train');
  addLog('Opening voice training web UI...', 'success');
});

gotoMainScreenBtn.addEventListener('click', () => {
  mainScreen.style.display = 'block';
  imageRequestScreen.style.display = 'none';
})

loginBtn.addEventListener('click', toggleSignIn);

sendImagePromptBtn.addEventListener('click', () => {
  if (imagePromptInput.value.length === 0) {
    alert("프롬프트를 입력해주세요.");
    return;
  }
  
  const prompt = {
    prompt: imagePromptInput.value
  }
  callGenerateImageFunction(prompt);
});

downloadImageBtn.addEventListener('click', downloadUserImage);

gotoImageRequestScreenBtn.addEventListener('click', () => {
  mainScreen.style.display = 'none';
  imageRequestScreen.style.display = 'block';
});

modelRequestBtn.addEventListener('click', callGenerateTha4ModelFunction);

modelDownloadBtn.addEventListener('click', downloadModel);

signUpBtn.addEventListener('click', handleSignUp);


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

// Initialize
addLog('VTuber Controller initialized', 'success');
addLog('Click "Show Overlay" to start tracking', 'success');
addLog('Enhanced eye recognition ready (60 FPS)', 'success');