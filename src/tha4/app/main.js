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
  
  overlayProcess = spawn('python', [overlayScript], {
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

// Vite 개발 서버 준비 함수
function waitForServer(url = 'http://localhost:3000', maxAttempts = 50, intervalMs = 300) {
  return new Promise((resolve, reject) => {
    let attempts = 0;

    const tryRequest = () => {
      attempts += 1;
      const req = http.get(url, (res) => {
        // 2xx/3xx면 서버가 뜬 것으로 간주
        if (res.statusCode && res.statusCode < 400) {
          res.resume();
          resolve();
        } else {
          res.resume();
          if (attempts >= maxAttempts) {
            reject(new Error(`Server not ready: ${url} (status ${res.statusCode})`));
          } else {
            setTimeout(tryRequest, intervalMs);
          }
        }
      });
      req.on('error', () => {
        if (attempts >= maxAttempts) {
          reject(new Error(`Server not reachable: ${url}`));
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

function openVoiceTrainWindow() {
  if (voiceTrainWindow && !voiceTrainWindow.isDestroyed()) {
    voiceTrainWindow.focus();
    return;
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
    voiceTrainWindow = null;
  });

  // 한글 주석: 프로덕션 빌드(dist)가 있으면 파일을 직접 로드, 없으면 dev 서버 사용
  const distIndex = path.resolve(__dirname, './voice_train/dist/index.html');
  if (fs.existsSync(distIndex)) {
    voiceTrainWindow.loadFile(distIndex);
  } else {
    voiceTrainWindow.loadURL('http://localhost:3000');
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

// --- 이 부분이 '../../../dist/main'으로 수정되었습니다 ---
ipcMain.on('start-voice-changer', (event) => {
  let scriptName;
  let execCommand;
  
  if (process.platform === 'darwin') { // macOS
    scriptName = 'start_https.command';
    const voiceChangerPath = path.join(__dirname, '../../../dist', scriptName); // 경로 수정됨
    execCommand = `open "${voiceChangerPath}"`;
    
  } else if (process.platform === 'win32' && process.arch === 'x64') { // Windows 64-bit
    scriptName = 'start_https.bat';
    const voiceChangerPath = path.join(__dirname, '../../../dist/main', scriptName); // 경로 수정됨
    execCommand = `start "" "${voiceChangerPath}"`;
    
  } else {
    // 다른 OS 또는 32-bit Windows 지원하지 않음
    const unsupportedError = `Unsupported OS/Arch: ${process.platform} ${process.arch}`;
    console.error(unsupportedError);
    event.reply('voice-changer-error', unsupportedError);
    return;
  }
  
  exec(execCommand, (error, stdout, stderr) => {
    if (error) {
      console.error(`Voice Changer Error: ${error.message}`);
      event.reply('voice-changer-error', error.message);
      return;
    }
    if (stderr) {
      console.warn(`Voice Changer Stderr: ${stderr}`);
    }
    console.log('Voice Changer start command issued.');
    event.reply('voice-changer-started');
  });
});
// --- 여기까지 수정되었습니다 ---

// 음성 학습(웹 UI) 열기
ipcMain.on('open-voice-train', async (event) => {
  try {
    await ensureBackendRunning();
    await startViteServerIfNeeded();
    openVoiceTrainWindow();
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
