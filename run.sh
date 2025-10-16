#!/usr/bin/env bash
set -euo pipefail

# 한국어 주석: other.sh 흐름을 적용한 실행 스크립트

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVER_DIR="$BASE_DIR/voice-changer/server"
DIST_BIN="$SERVER_DIR/dist/ai-vtuber-backend/ai-vtuber-backend"
SPEC_FILE="$SERVER_DIR/ai-vtuber-backend.spec"
ELECTRON_DIR="$BASE_DIR/electron"
VENV_DIR="$BASE_DIR/voice-changer/venv"
PORT="${PORT:-18888}"

# macOS MPS 백엔드 fallback (선택)
export PYTORCH_ENABLE_MPS_FALLBACK=1

# 1) venv 활성화 (필요 시 생성 - 3.10 우선)
if [ ! -d "$VENV_DIR" ]; then
  if command -v python3.10 >/dev/null 2>&1; then PY_CAND="python3.10"; else PY_CAND="python3"; fi
  "$PY_CAND" -m venv "$VENV_DIR"
fi
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate" || true
PY_BIN="$(command -v python3 || command -v python)"

# pip 고정 및 필수 설치
"$PY_BIN" -m pip install --upgrade "pip==24.0"

# 2) 서버 실행용 runner 생성
RUNNER="$SERVER_DIR/run_server.sh"
cat > "$RUNNER" <<'EOS'
#!/usr/bin/env bash
set -euo pipefail
BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
export PYTORCH_ENABLE_MPS_FALLBACK=1
cd "$BASE_DIR"
PY_BIN="$(cd "$(dirname "$0")"/../venv/bin && pwd)/python3"
PORT="${PORT:-18888}"
if [ -x "./dist/ai-vtuber-backend/ai-vtuber-backend" ]; then
  ./dist/ai-vtuber-backend/ai-vtuber-backend -p "$PORT" --https false
else
  "$PY_BIN" MMVCServerSIO.py -p "$PORT" --https false
fi
EOS
chmod +x "$RUNNER"

# 3) 포트 점유 프로세스 정리
if command -v lsof >/dev/null 2>&1; then
  PIDS=$(lsof -ti tcp:$PORT -sTCP:LISTEN || true)
  if [ -n "$PIDS" ]; then
    echo "$PIDS" | tr ' ' '\n' | while read -r pid; do
      [ -n "$pid" ] && kill -TERM "$pid" 2>/dev/null || true
    done
  fi
fi

# 4) 서버 백그라운드 실행
( cd "$SERVER_DIR" && PORT="$PORT" "$RUNNER" ) &

# 5) 서버 준비 대기
ATTEMPTS=120; SLEEP_SEC=1; READY=0
for i in $(seq 1 $ATTEMPTS); do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:$PORT/api/hello" || true)
  if [[ "$STATUS" == 2* || "$STATUS" == 3* ]]; then READY=1; break; fi
  sleep $SLEEP_SEC
done

# 6) Electron 또는 기본 브라우저 실행
CLIENT_APP=$(ls "$ELECTRON_DIR"/dist/*.AppImage 2>/dev/null || true)
if [ -n "$CLIENT_APP" ]; then
  chmod +x "$CLIENT_APP"
  "$CLIENT_APP" --disable-gpu -u "http://localhost:$PORT/" &
else
  if command -v xdg-open >/dev/null 2>&1; then xdg-open "http://localhost:$PORT/";
  elif command -v open >/dev/null 2>&1; then open "http://localhost:$PORT/";
  else echo "브라우저를 수동으로 열어 http://localhost:$PORT/ 접속하세요"; fi
fi

wait


