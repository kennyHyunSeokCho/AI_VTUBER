## 개요
VTuber 제어용 Electron 앱과 음성 학습 웹 UI, FastAPI 백엔드가 함께 있는 모노레포입니다. Electron 메인 화면에서 음성 학습을 열면 백엔드와 프론트엔드가 자동으로 기동됩니다.

## 폴더 구조
```
backend/                             FastAPI 백엔드 (루트 PYTHONPATH 기준)
src/
  tha4/app/                          Electron 앱 루트
    index.html, renderer.js, main.js
    build.sh                         앱 및 웹 빌드 스크립트
    voice_train/                     음성 학습 웹 프론트(Vite)
      src/                           React 컴포넌트
      vite.config.js                 /api → http://localhost:8000 프록시
  config.py, s3_utils.py, runpod_client.py  백엔드에서 사용하는 모듈
```

## 사전 요구사항
- macOS 또는 Linux, zsh/bash
- Python 3.10+ (.venv 사용 권장)
- Node.js 18+ 및 npm

## 설치
```
cd /Users/johyeonseog/runpod_
python3 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
# 필요 시 백엔드 의존성 설치
pip install -r requirements.txt

# 음성 학습 웹 의존성 (최초 1회)
cd src/tha4/app/voice_train
npm install
```

## 환경변수 (.env)
루트에 .env를 둡니다: /Users/johyeonseog/runpod_/.env
```
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=ap-northeast-2

S3_BUCKET_NAME=...
S3_DATA_PREFIX=voice_blend/uploads/
S3_MODELS_PREFIX=voice_blend/models/

RUNPOD_API_KEY=...
RUNPOD_ENDPOINT_ID=...

ARTIFACT_EXTS=.pth,.index
```

## 실행 방법
### 1) Electron에서 한 번에 실행 (권장)
```
cd /Users/johyeonseog/runpod_/src/tha4/app
npm start 
```
- 메인 화면의 "음성 학습" 버튼을 누르면 백엔드(uvicorn) → Vite dev 서버 순으로 자동 기동됩니다.
- 하단 로그 패널에서 backend / vite / overlay 로그를 바로 볼 수 있습니다.

### 2) 프론트와 백엔드를 따로 실행
백엔드
```
cd /Users/johyeonseog/runpod_
export PYTHONPATH=$(pwd)
./.venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```
프론트(음성 학습)
```
cd /Users/johyeonseog/runpod_/src/tha4/app/voice_train
npm run dev   # http://localhost:3000
```

### 3) 프로덕션 빌드
```
cd /Users/johyeonseog/runpod_/src/tha4/app
./build.sh      # voice_train도 함께 빌드됨
npm start       # dist/index.html 사용하여 dev 서버 없이 실행
```
개발 서버로 강제 실행하려면 src/tha4/app/voice_train/dist 폴더를 삭제하세요.

## API 요약 (백엔드)
- GET /                헬스체크
- GET /health          S3 연결 확인
- POST /upload         단일 파일 업로드 (mp3, m4a, wav, webm)
- POST /upload-multiple 다중 파일 업로드 (mp3, m4a, wav)
- POST /train          Runpod 학습 제출 및 옵션 대기
- GET /models/indexes  사용자별 모델 index 조회
- POST /blend/local    두 개의 .pth를 로컬에서 블렌딩 후 다운로드 링크 반환

## 트러블슈팅
- 8000 포트 충돌: 기존 uvicorn 프로세스 종료 후 재시도하거나 포트 변경
- 3000 포트 충돌: vite가 다른 포트를 선택할 수 있음. 고정하려면 vite.config.js의 server.port를 3000으로 유지
- 권한 문제로 vite 실행 실패: Electron은 node로 vite.js를 직접 실행하도록 구성됨
- S3 오류: .env 자격증명과 버킷 이름을 확인

## 주요 엔트리
- Electron 메인: src/tha4/app/main.js
- 렌더러(UI): src/tha4/app/index.html, renderer.js
- 음성 학습 웹: src/tha4/app/voice_train/src

