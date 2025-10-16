@echo off
setlocal

cd /d "%~dp0"
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

REM 서버 실행
if exist voice-changer\server\dist\ai-vtuber-backend\ai-vtuber-backend.exe (
  start "server" /b voice-changer\server\dist\ai-vtuber-backend\ai-vtuber-backend.exe -p 18888 --https false
) else (
  pushd voice-changer\server
  start "server" /b python MMVCServerSIO.py -p 18888 --https false
  popd
)

REM 서버 준비 대기 (최대 180초)
set PORT=18888
powershell -NoProfile -Command "$ProgressPreference='SilentlyContinue'; $url='http://localhost:%PORT%/api/hello'; for($i=0;$i -lt 180;$i++){ try{ $r=Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 $url; if($r.StatusCode -ge 200 -and $r.StatusCode -lt 400){ exit 0 } } catch { } Start-Sleep -Milliseconds 1000 }; exit 1"
if errorlevel 1 (
  echo 서버가 준비되지 않았습니다. http://localhost:%PORT%/ 를 수동으로 확인하세요.
  exit /b 1
)

REM electron-packager 산출물 우선
for /r electron\dist-win %%F in (*voice-changer-native-client*.exe) do (
  set CLIENT_EXE=%%F
)

REM fallback: electron-builder 산출물
if not defined CLIENT_EXE (
  for /r electron\dist %%F in (*voice-changer-native-client*.exe) do (
    set CLIENT_EXE=%%F
  )
)

REM fallback: win-unpacked
if not defined CLIENT_EXE (
  if exist electron\dist\win-unpacked\voice-changer-native-client.exe (
    set CLIENT_EXE=electron\dist\win-unpacked\voice-changer-native-client.exe
  )
)

if defined CLIENT_EXE (
  echo Electron client: %CLIENT_EXE%
  start "client" "%CLIENT_EXE%" --disable-gpu -u http://localhost:%PORT%/
) else (
  start http://localhost:%PORT%/
)

exit /b 0


