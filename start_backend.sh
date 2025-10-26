#!/bin/bash
echo "Starting Voice Blend Backend..."

# 가상환경 활성화 (Python 가상환경이 있다면)
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# 현재 디렉토리를 PYTHONPATH에 설정
export PYTHONPATH=$(pwd)

# 백엔드 실행 (uvicorn CLI 사용: --reload 지원)
exec uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
