@echo off
setlocal

chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

cd /d "%~dp0"

echo [1/4] electron 의존성 설치 및 윈도우 빌드
pushd electron
if exist package-lock.json (
  call npm ci || call npm install
) else (
  call npm install
)
call npm run build:win || goto :error
popd

echo [2/4] client lib 빌드
pushd voice-changer\client\lib
if exist package-lock.json (
  call npm ci || call npm install
) else (
  call npm install
)
call npm run build:prod || goto :error
popd

echo [3/4] client demo 빌드(dist 생성)
pushd voice-changer\client\demo
if exist package-lock.json (
  call npm ci || call npm install
) else (
  call npm install
)
call npm run build:prod || goto :error
if not exist dist (
  if exist dist_web xcopy /E /I /Y dist_web dist >nul
)
popd

echo [4/4] 서버 PyInstaller 빌드
if not exist .venv (
  py -3.10 -m venv .venv || goto :error
)
call .venv\Scripts\activate
pip install -U pip==24.0 || goto :error
pip install pyinstaller==6.10.0 || goto :error
pip install -r voice-changer\server\requirements.txt || goto :error
pushd voice-changer\server
python -m PyInstaller -y ai-vtuber-backend.spec || goto :error
popd

echo 완료. electron\dist-win 및 voice-changer\server\dist 확인
exit /b 0

:error
echo 빌드 실패
exit /b 1


