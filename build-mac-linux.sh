#!/usr/bin/env bash
set -euo pipefail

# 한국어 주석: other.sh 흐름을 적용한 Unix/macOS 빌드 스크립트

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVER_DIR="$BASE_DIR/voice-changer/server"
SPEC_FILE="$SERVER_DIR/ai-vtuber-backend.spec"
ELECTRON_DIR="$BASE_DIR/electron"
VENV_DIR="$BASE_DIR/voice-changer/venv"

echo "[1/7] Node.js 의존성 설치 및 클라이언트 라이브러리 빌드"
pushd "$BASE_DIR/voice-changer/client/lib" >/dev/null
[ -d node_modules ] || npm install
npm run build:prod
popd >/dev/null

echo "[2/7] 데모 프론트엔드 빌드"
pushd "$BASE_DIR/voice-changer/client/demo" >/dev/null
[ -d node_modules ] || npm install
npm run build:web:prod || npm run build:prod
popd >/dev/null

echo "[3/7] Electron 클라이언트 빌드"
pushd "$ELECTRON_DIR" >/dev/null
[ -d node_modules ] || npm install
npm run build:linux || npm run build:mac || true
popd >/dev/null

echo "[4/7] Python 가상환경 준비 (3.10 우선)"
if [ ! -d "$VENV_DIR" ]; then
  if command -v python3.10 >/dev/null 2>&1; then PY_CAND="python3.10"; else PY_CAND="python3"; fi
  "$PY_CAND" -m venv "$VENV_DIR"
fi
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
PY_BIN="$(command -v python3 || command -v python)"

echo "[5/7] Python 의존성 설치"
"$PY_BIN" -m pip install -U "pip==24.0"
"$PY_BIN" -m pip install pyinstaller==6.10.0
"$PY_BIN" -m pip install -r "$SERVER_DIR/requirements.txt"

echo "[6/7] PyInstaller 빌드 (ai-vtuber-backend)"
pushd "$SERVER_DIR" >/dev/null
"$PY_BIN" -m PyInstaller -y "$SPEC_FILE"
popd >/dev/null

echo "[7/7] 완료"


