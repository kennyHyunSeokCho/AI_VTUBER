const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const { spawn, exec } = require('child_process');

let mainWindow;
let overlayProcess = null;  // wxPython overlay 프로세스

function createMainWindow() {
  mainWindow = new BrowserWindow({
    width: 700,
    height: 650,
    backgroundColor: '#000000',
    icon: path.join(__dirname, 'icon.png'),  // 아이콘 설정!
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    }
  });

  mainWindow.loadFile('index.html');
  
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
  });
  
  overlayProcess.stderr.on('data', (data) => {
    console.error(`[Overlay Error] ${data}`);
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

ipcMain.on('start-voice-changer', (event) => {
  const voiceChangerPath = path.join(__dirname, '../../../dist/start_https.command');
  
  exec(`open "${voiceChangerPath}"`, (error, stdout, stderr) => {
    if (error) {
      console.error(`Voice Changer Error: ${error}`);
      event.reply('voice-changer-error', error.message);
      return;
    }
    console.log('Voice Changer started');
    event.reply('voice-changer-started');
  });
});