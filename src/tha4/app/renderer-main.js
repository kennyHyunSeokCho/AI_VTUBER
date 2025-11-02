// 메인 렌더러 로직 (sh/app/renderer.js 기반)
// Firebase 인증 및 이미지/모델 생성 통합

const { ipcRenderer } = require('electron');

// Firebase 모듈 동적 import (ES6 module을 require 환경에서 사용)
let loginModule, imageModelModule;

// 모듈 로드 (비동기)
(async function loadModules() {
  try {
    loginModule = await import('./login-logic.js');
    imageModelModule = await import('./image_model.js');
    
    console.log('Firebase 모듈 로드 완료');
    initializeApp();
  } catch (error) {
    console.error('모듈 로드 실패:', error);
  }
})();

function initializeApp() {
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
  const imagePromptInput = document.getElementById('imagePromptInput');
  const downloadImageBtn = document.getElementById('downloadImageBtn');
  const modelDownloadBtn = document.getElementById('modelDownloadBtn');
  const checkModelRequestBtn = document.getElementById('checkModelReqeustBtn');
  const cancelModelRequestBtn = document.getElementById('cancelModelRequestBtn');

  const mainScreen = document.getElementById('mainScreen');
  const imageRequestScreen = document.getElementById('imageRequestScreen');

  const gotoImageRequestScreenBtn = document.getElementById('gotoImageRequestScreenBtn');
  const gotoMainScreenBtn = document.getElementById('gotoMainScreenBtn');

  // State
  let overlayRunning = false;

  // Overlay button - 토글 기능
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

  // 화면 전환 버튼
  if (gotoMainScreenBtn) {
    gotoMainScreenBtn.addEventListener('click', () => {
      if (mainScreen) mainScreen.style.display = 'block';
      if (imageRequestScreen) imageRequestScreen.style.display = 'none';
    });
  }

  if (gotoImageRequestScreenBtn) {
    gotoImageRequestScreenBtn.addEventListener('click', () => {
      if (mainScreen) mainScreen.style.display = 'none';
      if (imageRequestScreen) imageRequestScreen.style.display = 'block';
    });
  }

  // 로그인 버튼
  if (loginBtn && loginModule) {
    loginBtn.addEventListener('click', loginModule.toggleSignIn);
  }

  // 회원가입 버튼
  if (signUpBtn && loginModule) {
    signUpBtn.addEventListener('click', loginModule.handleSignUp);
  }

  // 이미지 프롬프트 전송 버튼
  if (sendImagePromptBtn && imagePromptInput && imageModelModule) {
    sendImagePromptBtn.addEventListener('click', () => {
      if (imagePromptInput.value.length === 0) {
        alert("프롬프트를 입력해주세요.");
        return;
      }
      
      const prompt = {
        prompt: imagePromptInput.value
      };
      imageModelModule.callGenerateImageFunction(prompt);
    });
  }

  // 이미지 다운로드 버튼
  if (downloadImageBtn && imageModelModule) {
    downloadImageBtn.addEventListener('click', imageModelModule.downloadUserImage);
  }

  // 모델 생성 요청 버튼
  if (modelRequestBtn && imageModelModule) {
    modelRequestBtn.addEventListener('click', imageModelModule.callGenerateTha4ModelFunction);
  }

  // 모델 다운로드 버튼
  if (modelDownloadBtn && imageModelModule) {
    modelDownloadBtn.addEventListener('click', imageModelModule.downloadModel);
  }

  // 모델 상태 확인 버튼
  if (checkModelRequestBtn && imageModelModule) {
    checkModelRequestBtn.addEventListener('click', imageModelModule.callCheckModelRequestFunction);
  }

  // 모델 생성 취소 버튼
  if (cancelModelRequestBtn && imageModelModule) {
    cancelModelRequestBtn.addEventListener('click', imageModelModule.callCancelModelRequestCallable);
  }

  // Log functions
  function addLog(message, type = '') {
    if (!logContent) {
      console.log(`[LOG] ${message}`);
      return;
    }
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
}

