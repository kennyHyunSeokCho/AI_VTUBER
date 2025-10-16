const { app, BrowserWindow, session } = require('electron')

// 단일 인스턴스 잠금
if (!app.requestSingleInstanceLock()) {
  app.quit()
}

let mainWindow

async function createWindow() {
  // 캐시 비우기 (구번들 로드 방지)
  try {
    await session.defaultSession.clearCache()
  } catch (_) {}

  mainWindow = new BrowserWindow({
    width: 1100, // 창 기본 너비 축소
    height: 700, // 창 기본 높이 축소
    minWidth: 900, // 최소 너비
    minHeight: 600, // 최소 높이
    webPreferences: {
      nodeIntegration: false, // 보안 상 권장
      contextIsolation: true
    },
    title: 'AI Vtuber Studio'
  })

  // 서버 UI 로드 (PORT 환경변수 사용 가능)
  const port = process.env.PORT || '18888'
  const cacheBuster = Date.now().toString()
  mainWindow.loadURL(`http://localhost:${port}/?v=${cacheBuster}`)

  mainWindow.on('closed', () => {
    mainWindow = null
  })
}

app.whenReady().then(createWindow)

app.on('second-instance', () => {
  if (mainWindow) {
    if (mainWindow.isMinimized()) mainWindow.restore()
    mainWindow.focus()
  }
})

app.on('window-all-closed', () => {
  // macOS에서는 윈도우 모두 닫혀도 앱 유지
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

app.on('activate', () => {
  if (mainWindow === null) {
    createWindow()
  }
})
