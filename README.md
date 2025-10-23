# 🎙️ Voice Blend - AI 음성 학습 파이프라인

음성 파일을 S3에 업로드하고 Runpod GPU 클라우드에서 학습하여 AI 음성 모델을 생성하는 풀스택 애플리케이션

## 📋 프로젝트 구조

```
voice_blend/
├── backend/           # FastAPI 백엔드
│   └── main.py       # REST API 서버
├── frontend/          # React 프론트엔드
│   ├── src/
│   │   ├── components/
│   │   │   ├── AudioRecorder.jsx    # 녹음 기능
│   │   │   └── FileUploader.jsx     # 파일 업로드
│   │   ├── App.jsx
│   │   └── main.jsx
│   └── package.json
├── src/               # Python 유틸리티
│   ├── config.py      # 설정 로더
│   ├── s3_utils.py    # S3 업로드/다운로드
│   └── runpod_client.py  # Runpod API
├── manage.py          # CLI 스크립트
├── .env               # 환경변수 (직접 생성)
└── requirements.txt   # Python 패키지
```

## 🚀 빠른 시작

### 1. 환경 설정

```powershell
# 가상환경 생성 및 활성화
python -m venv .venv
.venv\Scripts\Activate.ps1

# Python 패키지 설치
pip install -r requirements.txt

# .env 파일 생성
copy env.sample .env
# .env 파일을 열어 AWS, S3, Runpod 정보 입력

# S3 연결 확인
python manage.py check
```

### 2. 웹 애플리케이션 실행

**터미널 1 - 백엔드 실행:**
```powershell
.venv\Scripts\Activate.ps1
python backend/main.py
# 또는
start_backend.bat
```
→ http://localhost:8000 (API 서버)

**터미널 2 - 프론트엔드 실행:**
```powershell
cd frontend
npm install  # 최초 1회만
npm run dev
# 또는 루트에서
start_frontend.bat
```
→ http://localhost:3000 (React 웹 앱)

### 3. 웹 UI 사용법

1. **사용자 ID 입력**: 본인의 고유 식별자 입력 (예: `user1`)
2. **녹음 또는 업로드**:
   - 🎤 **음성 녹음**: "녹음 시작" → 녹음 → "녹음 정지" → "S3에 업로드"
   - 📁 **파일 업로드**: 파일을 드래그 앤 드롭 또는 클릭하여 선택 → "S3에 업로드"
3. 업로드된 파일은 하단 **업로드 기록**에 표시됩니다

## 🖥️ CLI 사용법 (고급)

### 연결 확인
```powershell
python manage.py check
```

### 파일 업로드
```powershell
python manage.py upload <로컬_파일_또는_폴더> --user user1
```

### 학습 실행 및 대기
```powershell
python manage.py train --endpoint-id <ENDPOINT_ID> --input-prefix voice_blend/uploads/user1/ --output-prefix voice_blend/models/user1/run1/
```

### 산출물 다운로드
```powershell
python manage.py download --prefix voice_blend/models/user1/run1/ --out downloads
```

### 전체 파이프라인 (업로드→학습→다운로드)
```powershell
python manage.py pipeline <로컬_파일_또는_폴더> --endpoint-id <ENDPOINT_ID> --user user1
```

## 📡 API 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/` | 헬스체크 |
| POST | `/upload` | 단일 파일 업로드 |
| POST | `/upload-multiple` | 다중 파일 업로드 |
| GET | `/health` | S3 연결 상태 확인 |

## 🔧 환경변수 (.env)

```env
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_DEFAULT_REGION=ap-southeast-2

S3_BUCKET_NAME=vtubervoice
S3_DATA_PREFIX=voice_blend/uploads/
S3_MODELS_PREFIX=voice_blend/models/

RUNPOD_API_KEY=your-runpod-api-key
RUNPOD_ENDPOINT_ID=your-endpoint-id

ARTIFACT_EXTS=.pth,.index
```

## 📝 주의사항

- **Runpod 엔드포인트**: 컨테이너는 `s3_input_prefix`, `s3_output_prefix`를 입력으로 받아 S3에서 데이터를 읽고 결과를 작성해야 합니다
- **지원 오디오 형식**: WAV, MP3, OGG, WEBM, M4A, FLAC
- **브라우저 권한**: 녹음 기능 사용 시 마이크 접근 권한 필요

## 🎨 기능

✅ 브라우저 실시간 녹음 (MediaRecorder API)  
✅ 드래그 앤 드롭 파일 업로드  
✅ 다중 파일 일괄 업로드  
✅ S3 자동 업로드 및 관리  
✅ 반응형 UI 및 애니메이션  
✅ CLI 도구로 고급 작업 지원
