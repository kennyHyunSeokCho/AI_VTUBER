const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const { spawn, exec } = require('child_process');
const http = require('http');
const fs = require('fs');
const { pathToFileURL } = require('url');

let mainWindow;
let overlayProcess = null;  // wxPython overlay 프로세스
let voiceTrainWindow = null; // 음성 학습(Vite) 창
let viteDevProcess = null;   // Vite 개발 서버 프로세스
let backendProcess = null;   // FastAPI 백엔드 프로세스
let voiceChangerWindow = null; // VoiceChanger UI 창
let voiceChangerProcess = null; // VoiceChanger 서버 프로세스
let isVoiceChangerStarting = false; // VoiceChanger 시작 중 플래그

function createMainWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 900,
    minWidth: 1100,
    minHeight: 800,
    backgroundColor: '#000000',
    icon: path.join(__dirname, 'icon.png'),  // 아이콘 설정!
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    }
  });

  // 한글 주석: 앱 최초 로드는 로그인 페이지로 시작
  mainWindow.loadFile('login.html');
  
  mainWindow.on('closed', () => {
    if (overlayProcess) {
      overlayProcess.kill();
    }
    mainWindow = null;
  });
}

function createOverlayWindow() {
  if (overlayProcess) {
    console.log('Overlay already running');
    return;
  }

  const overlayScript = path.join(__dirname, 'overlay_window.py');
  const dataPath = path.resolve(__dirname, '../../../data');
  
  console.log('Starting wxPython overlay...');
  console.log('Overlay script:', overlayScript);
  console.log('Data path:', dataPath);
  
  const env = Object.assign({}, process.env, {
    VTUBER_DATA_PATH: dataPath
  });
  
  // 가상환경의 Python 사용 (프로젝트 루트의 .venv)
  const venvPython = path.join(__dirname, '../../../.venv/bin/python3');
  const pythonCmd = fs.existsSync(venvPython) ? venvPython : 'python3';
  
  overlayProcess = spawn(pythonCmd, [overlayScript], {
    env: env,
    cwd: __dirname
  });
  
  overlayProcess.stdout.on('data', (data) => {
    console.log(`[Overlay] ${data}`);
    // 한글 주석: 오버레이 표준출력을 렌더러 로그 패널로 전달
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('python-log', String(data));
      mainWindow.webContents.send('process-log', { source: 'overlay', level: 'info', message: String(data) });
    }
  });
  
  overlayProcess.stderr.on('data', (data) => {
    console.error(`[Overlay Error] ${data}`);
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('python-error', String(data));
      mainWindow.webContents.send('process-log', { source: 'overlay', level: 'error', message: String(data) });
    }
  });
  
  overlayProcess.on('close', (code) => {
    console.log(`[Overlay] Process exited with code ${code}`);
    overlayProcess = null;
    
    // 메인 창에 overlay 종료 알림
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('overlay-closed');
    }
  });
}

// 서버 준비 대기 함수 (개선 버전)
function waitForServer(url = 'http://localhost:3000', maxAttempts = 50, intervalMs = 300) {
  return new Promise((resolve, reject) => {
    let attempts = 0;

    const tryRequest = () => {
      attempts += 1;
      console.log(`[waitForServer] Attempt ${attempts}/${maxAttempts} for ${url}`);
      
      // IPv4 강제 (family: 4)
      const urlObj = new URL(url);
      const options = {
        hostname: urlObj.hostname,
        port: urlObj.port || 80,
        path: urlObj.pathname + urlObj.search,
        timeout: 5000,
        family: 4 // IPv4 강제
      };
      
      const req = http.get(options, (res) => {
        // 2xx/3xx면 서버가 뜬 것으로 간주
        if (res.statusCode && res.statusCode < 400) {
          res.resume();
          console.log(`[waitForServer] Server ready at ${url} (status: ${res.statusCode})`);
          resolve();
        } else {
          res.resume();
          console.log(`[waitForServer] Server responded with status ${res.statusCode}`);
          if (attempts >= maxAttempts) {
            reject(new Error(`Server not ready: ${url} (status ${res.statusCode})`));
          } else {
            setTimeout(tryRequest, intervalMs);
          }
        }
      });
      
      req.on('error', (err) => {
        console.log(`[waitForServer] Connection error (attempt ${attempts}): ${err.message}`);
        if (attempts >= maxAttempts) {
          reject(new Error(`Server not reachable: ${url} after ${maxAttempts} attempts`));
        } else {
          setTimeout(tryRequest, intervalMs);
        }
      });
      
      req.on('timeout', () => {
        console.log(`[waitForServer] Request timeout (attempt ${attempts})`);
        req.destroy();
        if (attempts >= maxAttempts) {
          reject(new Error(`Server timeout: ${url}`));
        } else {
          setTimeout(tryRequest, intervalMs);
        }
      });
      
      req.end();
    };

    tryRequest();
  });
}

function startViteServerIfNeeded() {
  const frontendDir = path.resolve(__dirname, './voice_train');
  const url = 'http://localhost:3000';

  return waitForServer(url, 10, 200).catch(() => {
    if (!viteDevProcess) {
      console.log('[Vite] Starting dev server...');

      const viteBin = path.join(frontendDir, 'node_modules', 'vite', 'bin', 'vite.js');
      const ensureDeps = () => new Promise((resolve, reject) => {
        if (fs.existsSync(viteBin)) {
          return resolve();
        }
        console.log('[Vite] node_modules not ready, running npm install...');
        const installer = spawn('npm', ['install'], { cwd: frontendDir, shell: true, env: process.env });
        installer.stdout.on('data', d => console.log(`[Vite:npm] ${d}`));
        installer.stderr.on('data', d => console.warn(`[Vite:npm-err] ${d}`));
        installer.on('close', (code) => {
          if (code === 0 && fs.existsSync(viteBin)) resolve();
          else reject(new Error(`npm install failed with code ${code}`));
        });
      });

      viteDevProcess = null; // 보수적 초기화

      return ensureDeps().then(() => {
        // npm run dev 대신 node로 vite.js를 직접 실행하여 권한 이슈를 회피
        const nodeCmd = 'node';
        viteDevProcess = spawn(nodeCmd, [viteBin], {
          cwd: frontendDir,
          env: process.env,
          shell: true
        });
        viteDevProcess.stdout.on('data', (data) => {
          console.log(`[Vite] ${data}`);
          if (mainWindow && !mainWindow.isDestroyed()) {
            mainWindow.webContents.send('process-log', { source: 'vite', level: 'info', message: String(data) });
          }
        });
        viteDevProcess.stderr.on('data', (data) => {
          console.warn(`[Vite:err] ${data}`);
          if (mainWindow && !mainWindow.isDestroyed()) {
            mainWindow.webContents.send('process-log', { source: 'vite', level: 'error', message: String(data) });
          }
        });
        viteDevProcess.on('close', (code) => {
          console.log(`[Vite] process exited with code ${code}`);
          viteDevProcess = null;
        });
      }).then(() => waitForServer(url, 100, 300));
    }

    // 이미 프로세스가 있다면 서버가 뜰 때까지 대기
    return waitForServer(url, 100, 300);
  });
}

async function openVoiceTrainWindow() {
  if (voiceTrainWindow && !voiceTrainWindow.isDestroyed()) {
    console.log('[VoiceTrain] Window already exists, focusing...');
    voiceTrainWindow.focus();
    return;
  }

  console.log('[VoiceTrain] Opening new window...');
  
  // 한글 주석: 메인 윈도우에서 로그인한 UID 가져오기
  let userUid = '';
  if (mainWindow && !mainWindow.isDestroyed()) {
    console.log('[VoiceTrain] Main window exists, getting UID...');
    try {
      // 모든 localStorage 내용 확인
      const allStorage = await mainWindow.webContents.executeJavaScript(
        'JSON.stringify(Object.assign({}, localStorage))'
      );
      console.log('[VoiceTrain] Main window localStorage:', allStorage);
      
      // UID 가져오기
      userUid = await mainWindow.webContents.executeJavaScript(
        'localStorage.getItem("vtuber_user_uid")'
      );
      console.log('[VoiceTrain] Retrieved UID from main window:', userUid);
      
      if (!userUid) {
        console.warn('[VoiceTrain] ⚠️ UID is null or empty!');
        console.warn('[VoiceTrain] User may not be logged in.');
      }
    } catch (err) {
      console.error('[VoiceTrain] ❌ Failed to get UID from main window:', err);
    }
  } else {
    console.error('[VoiceTrain] ❌ Main window does not exist or is destroyed!');
  }

  voiceTrainWindow = new BrowserWindow({
    width: 1100,
    height: 800,
    backgroundColor: '#111111',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true
    }
  });

  voiceTrainWindow.on('closed', () => {
    console.log('[VoiceTrain] Window closed');
    voiceTrainWindow = null;
  });

  // 한글 주석: URL에 UID를 쿼리 파라미터로 추가
  const uidParam = userUid ? `?uid=${encodeURIComponent(userUid)}` : '';
  console.log('[VoiceTrain] UID parameter:', uidParam || '(empty)');
  
  // 한글 주석: 프로덕션 빌드(dist)가 있으면 파일을 직접 로드, 없으면 dev 서버 사용
  const distIndex = path.resolve(__dirname, './voice_train/dist/index.html');
  if (fs.existsSync(distIndex)) {
    const finalUrl = `file://${distIndex}${uidParam}`;
    console.log('[VoiceTrain] Loading from dist:', finalUrl);
    voiceTrainWindow.loadFile(distIndex, { query: userUid ? { uid: userUid } : {} });
  } else {
    const finalUrl = `http://localhost:3000${uidParam}`;
    console.log('[VoiceTrain] Loading from dev server:', finalUrl);
    voiceTrainWindow.loadURL(finalUrl);
  }
}

function ensureBackendRunning() {
  return new Promise((resolve) => {
    const url = 'http://localhost:8000/health';
    // 기존 서버가 이미 뜨는 중일 수 있으므로 여유 있게 대기
    waitForServer(url, 50, 200)
      .then(resolve)
      .catch(() => {
        if (backendProcess) return resolve();
        console.log('[Backend] Starting FastAPI...');
        // 한글 주석: 워크스페이스 루트를 CWD로 설정하여 .env 로딩 및 모듈 경로 일관화
        const projectRoot = path.resolve(__dirname, '../../../');
        const venvUvicorn = path.resolve(__dirname, '../../../.venv/bin/uvicorn');
        const args = ['backend.main:app', '--host', '0.0.0.0', '--port', '8000'];
        backendProcess = spawn(venvUvicorn, args, {
          cwd: projectRoot,
          env: Object.assign({}, process.env, {
            // 한글 주석: 루트(src)만 import 경로로 사용 (AI_VTUBER 제거)
            PYTHONPATH: projectRoot,
          }),
          shell: true
        });
        backendProcess.stdout.on('data', (d) => {
          console.log(`[Backend] ${d}`);
          if (mainWindow && !mainWindow.isDestroyed()) {
            mainWindow.webContents.send('process-log', { source: 'backend', level: 'info', message: String(d) });
          }
        });
        backendProcess.stderr.on('data', (d) => {
          console.warn(`[Backend:err] ${d}`);
          if (mainWindow && !mainWindow.isDestroyed()) {
            mainWindow.webContents.send('process-log', { source: 'backend', level: 'error', message: String(d) });
          }
          // 포트가 이미 사용 중인 경우(Errno 48/EADDRINUSE) 기존 서버가 있을 수 있으므로 준비 완료를 대기 후 진행
          const msg = String(d).toLowerCase();
          if (msg.includes('address already in use') || msg.includes('eaddrinuse') || msg.includes('errno 48')) {
            waitForServer(url, 100, 300).then(resolve).catch(resolve);
          }
        });
        backendProcess.on('close', (code) => { console.log(`[Backend] exited ${code}`); backendProcess = null; });
        // 서버가 뜰 때까지 대기
        waitForServer('http://localhost:8000/health', 50, 200).then(resolve).catch(resolve);
      });
  });
}

app.whenReady().then(() => {
  createMainWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createMainWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (overlayProcess) {
    overlayProcess.kill();
  }
  if (viteDevProcess) {
    try { viteDevProcess.kill(); } catch (_) {}
    viteDevProcess = null;
  }
  if (backendProcess) {
    try { backendProcess.kill(); } catch (_) {}
    backendProcess = null;
  }
  if (voiceChangerProcess) {
    try { voiceChangerProcess.kill(); } catch (_) {}
    voiceChangerProcess = null;
  }
  
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// IPC handlers
ipcMain.on('start-python', (event) => {
  // overlay_window.py가 모든 것을 처리하므로 별도 백엔드 불필요
  console.log('[Info] Overlay handles all mocap data.');
  event.reply('python-log', 'Overlay is handling iFacialMocap data directly.\n');
});

ipcMain.on('stop-python', (event) => {
  console.log('[Info] No separate backend to stop.');
});

ipcMain.on('toggle-overlay', () => {
  if (overlayProcess) {
    overlayProcess.kill();
    overlayProcess = null;
    console.log('[Overlay] Stopped');
  } else {
    createOverlayWindow();
  }
});

// VoiceChanger IndexedDB LOCK 파일 정리 헬퍼 함수
function cleanVoiceChangerLockFiles() {
  try {
    const lockDir = path.join(
      app.getPath('appData'),
      'voice-changer-native-client',
      'IndexedDB',
      'http_127.0.0.1_18888.indexeddb.leveldb'
    );
    const lockFile = path.join(lockDir, 'LOCK');
    
    if (fs.existsSync(lockFile)) {
      console.log('[VoiceChanger] Cleaning up stale LOCK file...');
      try {
        fs.unlinkSync(lockFile);
        console.log('[VoiceChanger] LOCK file removed successfully');
      } catch (err) {
        console.warn('[VoiceChanger] Could not remove LOCK file:', err.message);
      }
    }
  } catch (err) {
    // 무시 (파일이 없거나 접근 불가)
  }
}

// 포트 18888을 사용하는 프로세스 종료
function killProcessOnPort18888() {
  return new Promise((resolve) => {
    if (process.platform === 'darwin' || process.platform === 'linux') {
      // macOS/Linux: lsof로 포트 확인 후 kill
      exec("lsof -ti:18888", (error, stdout, stderr) => {
        if (error || !stdout.trim()) {
          console.log('[VoiceChanger] Port 18888 is free');
          resolve();
          return;
        }
        
        const pids = stdout.trim().split('\n');
        console.log('[VoiceChanger] Found processes on port 18888:', pids);
        
        // 모든 프로세스 종료
        pids.forEach(pid => {
          try {
            exec(`kill -9 ${pid}`, (killError) => {
              if (!killError) {
                console.log(`[VoiceChanger] Killed process ${pid}`);
              }
            });
          } catch (err) {
            console.warn(`[VoiceChanger] Could not kill process ${pid}`);
          }
        });
        
        // 1초 대기 후 완료
        setTimeout(resolve, 1000);
      });
    } else if (process.platform === 'win32') {
      // Windows: netstat으로 포트 확인 후 taskkill
      exec('netstat -ano | findstr :18888', (error, stdout, stderr) => {
        if (error || !stdout.trim()) {
          console.log('[VoiceChanger] Port 18888 is free');
          resolve();
          return;
        }
        
        const lines = stdout.trim().split('\n');
        const pids = new Set();
        
        lines.forEach(line => {
          const parts = line.trim().split(/\s+/);
          const pid = parts[parts.length - 1];
          if (pid && !isNaN(pid)) {
            pids.add(pid);
          }
        });
        
        console.log('[VoiceChanger] Found processes on port 18888:', Array.from(pids));
        
        pids.forEach(pid => {
          try {
            exec(`taskkill /F /PID ${pid}`, (killError) => {
              if (!killError) {
                console.log(`[VoiceChanger] Killed process ${pid}`);
              }
            });
          } catch (err) {
            console.warn(`[VoiceChanger] Could not kill process ${pid}`);
          }
        });
        
        setTimeout(resolve, 1000);
      });
    } else {
      resolve();
    }
  });
}

// VoiceChanger 실행: startHttp.command 실행 후 팝업 창 열기
ipcMain.on('start-voice-changer', async (event) => {
  // 이미 시작 중이면 무시
  if (isVoiceChangerStarting) {
    console.log('[VoiceChanger] Already starting, ignoring duplicate request...');
    return;
  }
  
  // 이미 창이 열려있으면 포커스만 이동
  if (voiceChangerWindow && !voiceChangerWindow.isDestroyed()) {
    console.log('[VoiceChanger] Window already exists, focusing...');
    voiceChangerWindow.focus();
    return;
  }
  
  // 이미 서버가 실행 중이면 무시
  if (voiceChangerProcess && !voiceChangerProcess.killed) {
    console.log('[VoiceChanger] Server process already running, waiting for window...');
    return;
  }

  isVoiceChangerStarting = true; // 시작 플래그 설정
  console.log('[VoiceChanger] Starting server and opening window...');
  
  // 포트 18888 충돌 방지: 기존 프로세스 종료
  await killProcessOnPort18888();
  
  // LOCK 파일 정리 시도
  cleanVoiceChangerLockFiles();
  
  // 메인 창에 초기 상태 전송
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send('process-log', { 
      source: 'voice-changer', 
      level: 'info', 
      message: '초기화 중...' 
    });
  }
  
  // VoiceChanger 스크립트 경로 (src/tha4/app/voice_changer/startHttp.command)
  const voiceChangerDir = path.join(__dirname, 'voice_changer');
  const scriptPath = path.join(voiceChangerDir, 'startHttp.command');
  
  // 파일 존재 확인
  if (!fs.existsSync(scriptPath)) {
    console.error('[VoiceChanger] Script not found:', scriptPath);
    event.reply('voice-changer-error', 'startHttp.command 파일을 찾을 수 없습니다.');
    return;
  }
  
  console.log('[VoiceChanger] Script path:', scriptPath);
  
  // 모델 파일 존재 여부 확인
  const pretrainDir = path.join(voiceChangerDir, 'pretrain');
  const modelExists = fs.existsSync(pretrainDir);
  
  if (mainWindow && !mainWindow.isDestroyed()) {
    if (!modelExists) {
      mainWindow.webContents.send('process-log', { 
        source: 'voice-changer', 
        level: 'info', 
        message: '첫 실행입니다. 모델 다운로드 중... (3~5분 소요)' 
      });
    } else {
      mainWindow.webContents.send('process-log', { 
        source: 'voice-changer', 
        level: 'info', 
        message: '모델 로딩 중...' 
      });
    }
  }
  
  // 서버 프로세스 시작
  let serverReady = false; // 서버 준비 상태 플래그
  
  if (!voiceChangerProcess) {
    console.log('[VoiceChanger] Starting server process...');
    
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('process-log', { 
        source: 'voice-changer', 
        level: 'info', 
        message: 'Starting server process...' 
      });
    }
    
    voiceChangerProcess = spawn('bash', [scriptPath], {
      cwd: voiceChangerDir,
      env: Object.assign({}, process.env, {
        PYTORCH_ENABLE_MPS_FALLBACK: '1'
      })
    });
    
    voiceChangerProcess.stdout.on('data', (data) => {
      const message = String(data).trim();
      const lowerMsg = message.toLowerCase();
      console.log(`[VoiceChanger] ${message}`);
      
      // 서버 준비 완료 감지
      if (lowerMsg.includes('done 200') || 
          lowerMsg.includes('web server') || 
          lowerMsg.includes('listening')) {
        serverReady = true;
        console.log('[VoiceChanger] Server ready signal detected!');
      }
      
      if (mainWindow && !mainWindow.isDestroyed()) {
        // 의미있는 로그만 전송
        if (message.length > 0) {
          mainWindow.webContents.send('process-log', { 
            source: 'voice-changer', 
            level: 'info', 
            message: message
          });
        }
      }
    });
    
    voiceChangerProcess.stderr.on('data', (data) => {
      const message = String(data).trim();
      const lowerMsg = message.toLowerCase();
      
      // 비치명적 에러는 무시 (LevelDB LOCK 에러 등)
      const isIgnorableError = lowerMsg.includes('leveldb') || 
                               lowerMsg.includes('indexeddb') ||
                               lowerMsg.includes('lock: file currently in use');
      
      if (isIgnorableError) {
        console.log(`[VoiceChanger Info] ${message}`); // 콘솔에는 info로
        return; // 사용자에게는 표시하지 않음
      }
      
      console.error(`[VoiceChanger Error] ${message}`);
      
      if (mainWindow && !mainWindow.isDestroyed()) {
        // stderr도 의미있는 로그만 전송 (일부는 info로 처리)
        if (message.length > 0) {
          // 다운로드, 로딩, 초기화 관련 메시지는 info로
          const isInfoMessage = lowerMsg.includes('download') || 
                                 lowerMsg.includes('loading') ||
                                 lowerMsg.includes('initialize') ||
                                 lowerMsg.includes('booting') ||
                                 lowerMsg.includes('starting');
          
          mainWindow.webContents.send('process-log', { 
            source: 'voice-changer', 
            level: isInfoMessage ? 'info' : 'error', 
            message: message
          });
        }
      }
    });
    
    voiceChangerProcess.on('close', (code) => {
      console.log(`[VoiceChanger] Server process exited with code ${code}`);
      voiceChangerProcess = null;
      
      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send('process-log', { 
          source: 'voice-changer', 
          level: 'info', 
          message: `Server stopped (code: ${code})`
        });
      }
    });
  }
  
  // 서버가 준비될 때까지 대기 (포트 18888)
  // IPv4 주소 명시 (localhost는 IPv6로 해석될 수 있음)
  const voiceChangerUrl = 'http://127.0.0.1:18888';
  try {
    console.log('[VoiceChanger] Waiting for server to be ready...');
    
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('process-log', { 
        source: 'voice-changer', 
        level: 'info', 
        message: '서버 연결 대기 중... (최대 90초)'
      });
    }
    
    // VoiceChanger 서버는 초기화에 시간이 걸리므로 충분한 시간 제공
    // 서버 로그에서 "done 200" 시그널이 보이면 바로 연결 시도
    console.log('[VoiceChanger] Waiting for server... (max 90 seconds)');
    
    // 서버 준비 신호를 기다림 (최대 20초)
    const waitForSignal = new Promise((resolve) => {
      const checkInterval = setInterval(() => {
        if (serverReady) {
          clearInterval(checkInterval);
          console.log('[VoiceChanger] Server ready signal received, attempting connection...');
          resolve();
        }
      }, 100);
      
      // 타임아웃 후에도 연결 시도
      setTimeout(() => {
        clearInterval(checkInterval);
        resolve();
      }, 20000);
    });
    
    await waitForSignal;
    
    // 실제 HTTP 연결 확인 (최대 90초, IPv4로 명시)
    await waitForServer(voiceChangerUrl, 180, 500);
    console.log('[VoiceChanger] Server is ready!');
    
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('process-log', { 
        source: 'voice-changer', 
        level: 'info', 
        message: 'Server is ready! Opening window...'
      });
    }
    
    // 새 창 열기
    voiceChangerWindow = new BrowserWindow({
      width: 1200,
      height: 800,
      backgroundColor: '#0a0a0a',
      title: 'Realtime VoiceChanger',
      webPreferences: {
        nodeIntegration: false,
        contextIsolation: true,
        // IndexedDB 세션 격리로 충돌 방지
        partition: 'persist:voicechanger',
        // 콘솔 에러 필터링을 위한 설정
        webSecurity: true
      }
    });
    
    // 콘솔 에러 메시지 필터링 (LevelDB/IndexedDB 에러 숨김)
    voiceChangerWindow.webContents.on('console-message', (event, level, message, line, sourceId) => {
      const lowerMsg = message.toLowerCase();
      const isIgnorableError = lowerMsg.includes('leveldb') || 
                               lowerMsg.includes('indexeddb') ||
                               lowerMsg.includes('lock') ||
                               lowerMsg.includes('failed to open');
      
      if (isIgnorableError) {
        // 무시 (DevTools에 표시 안 함)
        return;
      }
      
      // 다른 에러만 로그
      if (level === 2 || level === 3) { // warning or error
        console.log(`[VoiceChanger Browser] ${message}`);
      }
    });
    
    voiceChangerWindow.loadURL(voiceChangerUrl);
    
    // 창이 로드되면 메인 창으로 포커스 복귀
    voiceChangerWindow.webContents.once('did-finish-load', () => {
      console.log('[VoiceChanger] Window loaded, returning focus to main window');
      
      // 메인 창에 VoiceChanger 열렸음을 알림 (사이드바 닫기용)
      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send('voice-changer-window-opened');
        
        // 메인 창으로 포커스 이동
        setTimeout(() => {
          if (mainWindow && !mainWindow.isDestroyed()) {
            mainWindow.focus();
          }
        }, 500);
      }
    });
    
    voiceChangerWindow.on('closed', () => {
      console.log('[VoiceChanger] Window closed');
      voiceChangerWindow = null;
      isVoiceChangerStarting = false; // 플래그 초기화
      
      // 창 닫을 때 서버 프로세스도 종료
      if (voiceChangerProcess) {
        console.log('[VoiceChanger] Stopping server process...');
        try {
          voiceChangerProcess.kill('SIGTERM'); // 정상 종료 시도
          setTimeout(() => {
            if (voiceChangerProcess) {
              voiceChangerProcess.kill('SIGKILL'); // 강제 종료
            }
            voiceChangerProcess = null;
          }, 2000);
        } catch (err) {
          console.error('[VoiceChanger] Error killing process:', err);
          voiceChangerProcess = null;
        }
      }
    });
    
    event.reply('voice-changer-started');
    isVoiceChangerStarting = false; // 시작 완료
    
  } catch (error) {
    console.error('[VoiceChanger] Failed to start:', error);
    event.reply('voice-changer-error', error.message);
    
    // 실패 시 프로세스 정리
    if (voiceChangerProcess) {
      voiceChangerProcess.kill();
      voiceChangerProcess = null;
    }
    
    isVoiceChangerStarting = false; // 시작 실패, 플래그 해제
  }
});

// VTuber Live (absolute.py) 실행
ipcMain.on('start-vtuber-live', (event) => {
  const absolutePyPath = path.join(__dirname, 'absolute.py');
  
  console.log('[VTuber Live] Starting absolute.py:', absolutePyPath);
  
  if (!fs.existsSync(absolutePyPath)) {
    console.error('[VTuber Live] absolute.py not found:', absolutePyPath);
    event.reply('vtuber-live-error', 'absolute.py 파일을 찾을 수 없습니다.');
    return;
  }
  
  // 가상환경의 Python 사용 (프로젝트 루트의 .venv)
  const venvPython = path.join(__dirname, '../../../.venv/bin/python3');
  const pythonCmd = fs.existsSync(venvPython) ? venvPython : 'python3';
  
  console.log('[VTuber Live] Using Python:', pythonCmd);
  
  const vtuberProcess = spawn(pythonCmd, [absolutePyPath], {
    cwd: __dirname,
    env: process.env
  });
  
  vtuberProcess.stdout.on('data', (data) => {
    console.log(`[VTuber Live] ${data}`);
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('process-log', { 
        source: 'vtuber-live', 
        level: 'info', 
        message: String(data) 
      });
    }
  });
  
  vtuberProcess.stderr.on('data', (data) => {
    console.error(`[VTuber Live Error] ${data}`);
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('process-log', { 
        source: 'vtuber-live', 
        level: 'error', 
        message: String(data) 
      });
    }
  });
  
  vtuberProcess.on('close', (code) => {
    console.log(`[VTuber Live] Process exited with code ${code}`);
  });
  
  event.reply('vtuber-live-started');
});

// 음성 학습(웹 UI) 열기
ipcMain.on('open-voice-train', async (event) => {
  try {
    await ensureBackendRunning();
    await startViteServerIfNeeded();
    await openVoiceTrainWindow();
  } catch (err) {
    console.error('[VoiceTrain] failed to open:', err && err.message ? err.message : err);
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('python-error', String(err));
    }
  }
});

// 보이스 트레인 앱을 iframe으로 임베드하기 위한 준비 신호
ipcMain.on('ensure-voice-train', async (event) => {
  try {
    await ensureBackendRunning();
    await startViteServerIfNeeded();
    const distIndex = path.resolve(__dirname, './voice_train/dist/index.html');
    let url = 'http://localhost:3000';
    if (fs.existsSync(distIndex)) {
      url = pathToFileURL(distIndex).toString();
    }
    event.reply('voice-train-ready', { url });
  } catch (err) {
    const msg = err && err.message ? err.message : String(err);
    console.error('[VoiceTrain] ensure failed:', msg);
    event.reply('voice-train-error', msg);
  }
});
