# VTuber 통합 플랫폼

Firebase 기반 인증 시스템을 갖춘 VTuber 아바타 생성 및 제어 플랫폼입니다. Electron 앱으로 구동되며, 아바타 이미지 생성, THA4 모델 학습, 음성 모델 학습, 실시간 오버레이 기능을 제공합니다.

## 주요 기능

### 1. 사용자 인증
- 이메일/비밀번호 기반 회원가입 및 로그인
- Google OAuth 2.0 소셜 로그인
- Firebase Authentication을 통한 안전한 사용자 관리
- 자동 세션 유지 및 UID 기반 데이터 관리

### 2. 아바타 이미지 생성
- 텍스트 프롬프트 기반 AI 아바타 이미지 생성
- Firebase Cloud Functions를 통한 Runpod 연동
- Firebase Storage에 자동 저장 및 다운로드
- 사용자별 이미지 관리

### 3. THA4 모델 생성
- 생성된 아바타 이미지로 THA4 캐릭터 모델 자동 학습
- Runpod GPU 인스턴스를 활용한 고속 처리
- 학습 상태 실시간 확인 및 취소 기능
- 완성된 모델 자동 다운로드

### 4. 음성 모델 학습
- 음성 파일 업로드 및 전처리
- RVC 기반 음성 변환 모델 학습
- 두 개의 음성 모델 블렌딩 기능
- 학습 진행 상황 실시간 모니터링

### 5. 실시간 오버레이
- iFacialMocap UDP 데이터 수신
- 실시간 표정 인식 및 매칭
- OBS 연동을 위한 투명 윈도우
- 여러 표정 이미지 자동 전환

## 시스템 요구사항

### 필수 환경
- macOS 또는 Linux (Windows는 일부 기능 제한)
- Python 3.10 이상
- Node.js 18 이상
- npm 또는 yarn

### 외부 서비스
- Firebase 프로젝트 (Authentication, Functions, Storage, Firestore)
- AWS S3 버킷
- Runpod API 키 및 엔드포인트

## 설치 방법

### 1. 저장소 클론
```bash
git clone <repository-url>
cd runpod_
```

### 2. Python 환경 설정
```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Node.js 의존성 설치
```bash
# Electron 앱
cd src/tha4/app
npm install

# 음성 학습 웹 UI
cd voice_train
npm install
cd ../..
```

## 환경 설정

### 1. Firebase 설정
`src/tha4/app/config.js` 파일에 Firebase 프로젝트 정보를 입력합니다:
```javascript
export const firebaseConfig = {
    apiKey: "your-api-key",
    authDomain: "your-project.firebaseapp.com",
    projectId: "your-project-id",
    storageBucket: "your-project.appspot.com",
    messagingSenderId: "your-sender-id",
    appId: "your-app-id"
};
```

### 2. Firebase Console 설정
Firebase Console에서 다음 설정을 완료해야 합니다:

**Authentication**
- 이메일/비밀번호 로그인 활성화
- Google 로그인 활성화
- Authorized domains에 localhost 추가

**Firestore Database**
- 데이터베이스 생성
- 규칙 설정 (사용자별 읽기/쓰기 권한)

**Storage**
- 스토리지 버킷 생성
- 규칙 설정 (사용자별 읽기/쓰기 권한)

**Cloud Functions**
- generate_image 함수 배포
- generate_tha4_model 함수 배포
- check_runpod_pod 함수 배포
- cancel_runpod_pod 함수 배포

### 3. 환경 변수 설정
프로젝트 루트에 `.env` 파일을 생성합니다:
```bash
# AWS S3 설정
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=ap-northeast-2

# S3 버킷 정보
S3_BUCKET_NAME=your-bucket-name
S3_DATA_PREFIX=voice_blend/uploads/
S3_MODELS_PREFIX=voice_blend/models/

# Runpod 설정
RUNPOD_API_KEY=your_runpod_api_key
RUNPOD_ENDPOINT_ID=your_endpoint_id

# 모델 파일 확장자
ARTIFACT_EXTS=.pth,.index
```

## 실행 방법

### Electron 앱 실행 (권장)
```bash
cd src/tha4/app
npm start
```

앱이 실행되면:
1. 로그인 페이지에서 회원가입 또는 로그인
2. 메인 화면에서 원하는 기능 선택
3. 아바타 생성, 음성 학습, 오버레이 등 사용

### 개별 컴포넌트 실행

**백엔드만 실행**
```bash
cd /path/to/runpod_
export PYTHONPATH=$(pwd)
source .venv/bin/activate
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

**음성 학습 웹 UI만 실행**
```bash
cd src/tha4/app/voice_train
npm run dev
```
브라우저에서 http://localhost:3000 접속

**오버레이 윈도우만 실행**
```bash
cd src/tha4/app
python overlay_window.py
```

## 프로젝트 구조

```
runpod_/
├── backend/                      # FastAPI 백엔드
│   ├── main.py                  # API 서버 메인
│   └── ...
├── src/
│   ├── config.py                # 설정 관리
│   ├── s3_utils.py              # S3 유틸리티
│   ├── runpod_client.py         # Runpod API 클라이언트
│   └── tha4/app/                # Electron 앱
│       ├── main.js              # Electron 메인 프로세스
│       ├── renderer.js          # 메인 화면 렌더러
│       ├── index.html           # 메인 화면 UI
│       ├── login.html           # 로그인 페이지
│       ├── login-logic.js       # 인증 로직
│       ├── avatar.html          # 아바타 생성 페이지
│       ├── avatar-logic.js      # 아바타 생성 로직
│       ├── image_model.js       # 이미지/모델 생성 API
│       ├── config.js            # Firebase 설정
│       ├── overlay_window.py    # VTuber 오버레이
│       ├── fmpm.py              # 표정 생성 도구
│       └── voice_train/         # 음성 학습 웹 UI
│           ├── src/
│           │   ├── App.jsx
│           │   └── components/
│           │       ├── FileUploader.jsx    # 파일 업로드
│           │       ├── AudioRecorder.jsx   # 녹음 기능
│           │       └── ModelBlender.jsx    # 모델 블렌딩
│           └── vite.config.js
└── .env                         # 환경 변수
```

## 백엔드 API

### 파일 업로드
- `POST /upload` - 단일 파일 업로드 (mp3, m4a, wav, webm)
- `POST /upload-multiple` - 다중 파일 업로드 (mp3, m4a, wav)

### 음성 모델 학습
- `POST /train` - Runpod에 학습 작업 제출
- `GET /models/indexes` - 사용자별 학습된 모델 조회

### 모델 블렌딩
- `POST /blend/local` - 두 개의 음성 모델 블렌딩

### 시스템
- `GET /` - 헬스 체크
- `GET /health` - S3 연결 상태 확인

## 사용 가이드

### 회원가입 및 로그인
1. Electron 앱 실행 시 로그인 페이지가 표시됩니다
2. 이메일과 비밀번호를 입력하고 "회원가입"을 클릭합니다
3. 또는 "Google로 로그인" 버튼으로 간편 로그인합니다
4. 로그인 성공 시 메인 화면으로 이동합니다

### 아바타 이미지 생성
1. 메인 화면에서 "아바타 생성" 버튼을 클릭합니다
2. 텍스트 입력란에 원하는 아바타의 특징을 입력합니다
   예: "1girl, blue eyes, long hair, school uniform"
3. "전송" 버튼을 클릭하여 이미지 생성을 요청합니다
4. 생성 완료 후 "다운로드" 버튼으로 이미지를 저장합니다

### THA4 모델 생성
1. 아바타 이미지를 먼저 생성합니다
2. 메인 화면에서 "모델 학습" 버튼을 클릭합니다
3. Runpod에서 자동으로 모델 학습이 시작됩니다
4. "학습 상태 확인" 버튼으로 진행 상황을 확인합니다
5. 완료 후 "모델 다운로드" 버튼으로 저장합니다

### 음성 모델 학습
1. 메인 화면에서 "음성 학습" 버튼을 클릭합니다
2. 음성 파일을 업로드하거나 직접 녹음합니다
3. 학습 설정을 입력하고 "학습 시작"을 클릭합니다
4. 학습 진행 상황을 모니터링합니다
5. 완료된 모델을 다운로드합니다

### VTuber 오버레이 사용
1. fmpm.py로 다양한 표정 이미지를 먼저 생성합니다
2. 메인 화면에서 "오버레이 시작" 버튼을 클릭합니다
3. iFacialMocap 앱에서 UDP 데이터를 전송합니다
4. OBS에서 투명 윈도우를 캡처합니다
5. 실시간으로 표정이 변하는 아바타를 방송에 사용합니다

## 데이터 구조

### Firestore
```
users/
  {uid}/
    imagePath: "users/{uid}/images/{image_id}.png"
    tha4ModelPath: "users/{uid}/models/{model_id}.zip"
    email: "user@example.com"
    createdAt: timestamp
```

### Firebase Storage
```
users/
  {uid}/
    images/
      {image_id}.png
    models/
      {model_id}.zip
```

## 문제 해결

### Firebase 로그인 오류

**auth/unauthorized-domain**
- Firebase Console → Authentication → Settings → Authorized domains
- 사용 중인 도메인(localhost 등)을 추가합니다

**auth/popup-blocked**
- 브라우저 설정에서 팝업 차단을 해제합니다

**auth/invalid-api-key**
- config.js의 Firebase 설정을 확인합니다

### 이미지 생성 오류

**User is not authenticated**
- 로그인 상태를 확인합니다
- 로그아웃 후 다시 로그인합니다

**Firebase Functions 오류**
- Firebase Console에서 Functions가 정상 배포되었는지 확인합니다
- Functions 로그에서 에러 메시지를 확인합니다

### 포트 충돌

**8000 포트 사용 중**
```bash
lsof -ti:8000 | xargs kill -9
```

**3000 포트 사용 중**
```bash
lsof -ti:3000 | xargs kill -9
```

### S3 연결 오류
- .env 파일의 AWS 자격 증명을 확인합니다
- S3 버킷 이름과 리전이 올바른지 확인합니다
- IAM 권한이 올바르게 설정되었는지 확인합니다

### Runpod 오류
- API 키가 유효한지 확인합니다
- 엔드포인트 ID가 올바른지 확인합니다
- Runpod 계정에 충분한 크레딧이 있는지 확인합니다

## 프로덕션 빌드

```bash
cd src/tha4/app
./build.sh
```

빌드 스크립트는 다음 작업을 수행합니다:
1. 음성 학습 웹 UI 빌드 (voice_train/dist)
2. Electron 앱 패키징 준비
3. 최적화된 번들 생성

빌드 완료 후:
```bash
npm start
```

개발 서버 없이 빌드된 파일로 실행됩니다.

## 라이선스

이 프로젝트의 라이선스 정보는 LICENSE 파일을 참조하십시오.

## 기여

버그 리포트나 기능 제안은 이슈로 등록해주시기 바랍니다.

## 참고 문서

- src/tha4/app/UID_사용법.md - Firebase UID 사용 가이드
- src/tha4/app/avatar/avatar_사용법.md - 아바타 생성 상세 가이드
