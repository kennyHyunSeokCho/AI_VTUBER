# 설치·실행 가이드

[프로젝트 소개로 돌아가기](../README.md)

기존 README의 설치·설정·사용 안내를 이 문서에 모았습니다. 명령은 저장소 루트를 기준으로 작성했으며, 외부 서비스와 GPU 모델은 별도 준비가 필요합니다. 이번 문서 정리에서는 실제 학습이나 외부 서비스 호출을 실행하지 않았습니다.

## 실행 구성

| 구성 | 필요 환경 |
| --- | --- |
| Electron 앱 | Node.js 18 이상, npm, Firebase 설정 |
| 음성 웹 UI | React·Vite 개발 서버, FastAPI 8000 포트 |
| Python API | Python 3.10 이상, AWS S3 설정, ffmpeg |
| 아바타·오버레이 | wxPython, 캐릭터 모델 또는 사전 생성 표정 PNG, iFacialMocap |
| THA4 표정 생성 | 모델 가중치와 PyTorch 실행 환경. 현재 `fmpm.py` 진입점은 CUDA 장치를 지정 |
| 원격 생성·학습 | 배포한 Firebase callable 함수, Runpod 작업 엔드포인트 또는 외부 학습 서버 |

운영체제별로 모든 기능이 동일하게 실행된다고 가정하지 않습니다. 특히 CUDA를 사용하는 도구와 iFacialMocap 장치 준비는 앱 UI 실행과 별개입니다.

## 1. 저장소와 의존성 준비

```bash
git clone https://github.com/kennyHyunSeokCho/AI_VTUBER.git
cd AI_VTUBER
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
npm --prefix src/tha4/app install
npm --prefix src/tha4/app/voice_train install
```

현재 `requirements.txt`에는 직접 사용하는 `boto3`, `runpod`, `python-dotenv`, `wxPython`이 모두 명시되어 있지는 않습니다. 사용하는 기능에 맞춰 해당 패키지를 추가 설치해야 합니다. 오디오 변환에는 시스템 `ffmpeg` 또는 `imageio-ffmpeg`가 필요합니다. PyTorch·CUDA 버전은 실행 GPU 환경과 맞춰 준비합니다.

Electron은 저장소 루트의 `.venv`를 찾는 경로를 사용하므로, 가상환경을 앱 하위 폴더가 아닌 루트에 준비합니다.

## 2. Firebase 설정

`src/tha4/app/login-logic.js`가 import하는 `src/tha4/app/config.js`를 로컬에서 준비합니다. 이 파일은 현재 추적된 소스에 포함되어 있지 않습니다.

```javascript
export const firebaseConfig = {
  apiKey: "YOUR_FIREBASE_API_KEY",
  authDomain: "YOUR_PROJECT.firebaseapp.com",
  projectId: "YOUR_PROJECT",
  storageBucket: "YOUR_STORAGE_BUCKET",
  messagingSenderId: "YOUR_MESSAGING_SENDER_ID",
  appId: "YOUR_APP_ID"
};
```

Firebase 프로젝트에서는 이메일·비밀번호 로그인과 Google 로그인을 활성화하고, 사용 중인 도메인을 인증 허용 도메인에 등록합니다. Firestore와 Storage의 사용자별 접근 규칙도 해당 배포 환경에 맞게 설정합니다.

클라이언트가 호출하는 함수는 다음과 같습니다.

| callable 함수 | 역할 |
| --- | --- |
| `generate_image` | 프롬프트 기반 이미지 생성 요청 |
| `generate_tha4_model` | 최신 이미지 경로를 이용한 캐릭터 모델 생성 요청 |
| `check_runpod_pod` | 모델 생성 작업 상태 확인 |
| `cancel_runpod_pod` | 모델 생성 작업 취소 요청 |

이 저장소에는 호출 클라이언트가 있으며, callable 서버 함수와 Cloud Tasks·GPU 워커 배포는 별도 준비 영역입니다. Firestore `users/{uid}` 문서에는 클라이언트가 읽을 `imagePath`와 `tha4ModelPath`가 기록되어야 합니다.

## 3. 음성 서버 환경 변수

저장소 루트의 `.env`에 사용하는 서비스의 설정을 입력합니다. 아래 값은 예시입니다.

```dotenv
AWS_ACCESS_KEY_ID=YOUR_AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY=YOUR_AWS_SECRET_ACCESS_KEY
AWS_DEFAULT_REGION=ap-northeast-2
S3_BUCKET_NAME=YOUR_BUCKET
S3_MODELS_PREFIX=voice_blend/models/
ARTIFACT_EXTS=.pth,.index

RUNPOD_API_KEY=YOUR_RUNPOD_API_KEY
RUNPOD_ENDPOINT_ID=YOUR_ENDPOINT_ID
EXTERNAL_TRAIN_URL=https://YOUR_TRAINING_SERVER/train
```

- `RUNPOD_ENDPOINT_ID`는 `/train`이 제출할 Serverless 엔드포인트입니다.
- `EXTERNAL_TRAIN_URL`은 업로드 이후 알림을 보낼 외부 학습 서버 주소입니다. 실제 운영할 주소를 명시적으로 설정합니다.
- `RUNPOD_POD_IMAGE`, `RUNPOD_POD_TEMPLATE_ID`는 Pod 제출 도우미에서 사용하는 선택 설정입니다. 기본 업로드 API는 이 도우미 대신 외부 학습 알림 경로를 호출합니다.
- `S3_DATA_PREFIX` 설정 필드는 있지만, 현재 업로드 API의 실제 경로는 `voice_blend/{user_id}/uploads/`로 코드에 지정되어 있습니다.

## 4. 개발 모드 실행

### Electron 앱

루트 가상환경을 활성화한 터미널에서 실행합니다.

```bash
source .venv/bin/activate
npm --prefix src/tha4/app start
```

로그인 후 이미지 생성·캐릭터 모델·음성 학습·Live 등 기능을 선택합니다. Electron 메인 프로세스에는 로컬 서버와 Python 도구를 시작하는 경로가 있습니다. 서버를 따로 실행할 때는 같은 포트를 중복 사용하지 않도록 합니다.

### FastAPI만 실행

```bash
source .venv/bin/activate
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

### 음성 웹 UI만 실행

별도 터미널에서 다음 명령을 실행합니다.

```bash
npm --prefix src/tha4/app/voice_train run dev
```

브라우저에서 `http://localhost:3000`으로 접근합니다. Vite의 `/api` 요청은 `localhost:8000`으로 프록시됩니다. 파일 업로더도 로컬 8000 포트 API를 사용합니다.

## 5. 기능별 사용

### 이미지·캐릭터 모델

1. Firebase 계정으로 로그인합니다.
2. 아바타 생성 화면에서 캐릭터 특징을 입력해 생성을 요청합니다.
3. 생성 완료 후 최신 이미지를 조회·다운로드합니다.
4. 해당 이미지로 THA4 모델 생성을 요청합니다.
5. 상태 확인·취소 버튼을 사용하고, 완료 후 모델을 다운로드합니다.

상태 확인은 callable 요청에 대한 결과를 표시하는 방식입니다. 학습 퍼센트를 자동 구독하는 기능으로 설명하지 않습니다.

### 음성 업로드·모델 조회

1. 음성 학습 UI에서 영문자로 된 사용자 ID를 입력합니다.
2. 음성 파일을 업로드합니다. 서버는 WAV로 변환해 S3에 저장하고 외부 학습 알림을 예약합니다.
3. 별도 `/train` 경로를 쓰는 경우 준비된 Runpod 엔드포인트에 작업을 제출합니다.
4. 모델 파일 찾기에서 `.pth`·`.index`를 조회하고 다운로드합니다.
5. 블렌딩 탭에서는 호환되는 `.pth` 두 개와 이름·혼합 비율을 입력합니다.

현재 React의 ID 입력은 영숫자를 허용하지만 서버는 영문자만 남깁니다. 혼동을 피하려면 영문자 ID를 사용합니다. Firebase 로그인 UID가 현재 음성 UI의 수동 ID로 자동 연결된다고 가정하지 않습니다.

`AudioRecorder.jsx`에는 녹음 구현이 있으나 현재 `App.jsx`에 연결되어 있지는 않습니다. 기본 화면은 파일 업로드를 기준으로 안내합니다. 표시되는 다운로드 진행률은 모델 학습 진행률과 다릅니다.

### 표정 이미지 준비와 Live

`fmpm.py`는 THA4 poser로 표정 PNG를 사전 생성하는 도구입니다. 필요한 모델 가중치와 CUDA 환경이 준비된 경우 저장소 루트에서 실행합니다.

```bash
PYTHONPATH=src python src/tha4/app/fmpm.py
```

기본 출력은 루트 `data/eye_face_optimized_patches/`입니다. 두 실행 경로는 기본 데이터 위치가 다르므로 PNG 폴더 위치를 맞춰야 합니다.

| 실행 경로 | 기본 입력 위치 |
| --- | --- |
| Electron Live → `absolute.py` | `src/tha4/app/data/eye_face_optimized_patches/` |
| 별도 `overlay_window.py` | 루트 `data/eye_face_optimized_patches/` |

Live 창의 `Start VTuber Mode`로 모캡 수신을 시작하고 `Show Overlay`로 출력 창을 표시합니다. iFacialMocap은 실행 PC의 UDP 수신 주소로 전송하도록 설정하며 기본 포트는 `49983`입니다.

별도 오버레이 도구는 다음처럼 실행할 수 있습니다.

```bash
python src/tha4/app/overlay_window.py
```

OBS에서는 오버레이 창을 캡처한 뒤 초록 배경을 크로마키로 제거합니다. 두 도구는 PNG 매칭 경로이며, 실행 중 매 프레임 THA4를 추론하는 방식과 구분됩니다.

## 문제 해결

| 증상 | 확인할 항목 |
| --- | --- |
| Firebase `auth/unauthorized-domain` | 인증 허용 도메인과 현재 실행 방식 |
| Firebase 팝업·키 오류 | 팝업 허용 여부와 로컬 `config.js` 프로젝트 설정 |
| 이미지·모델 생성 실패 | 로그인 상태, callable 배포 위치·함수명, 외부 GPU 워커 상태 |
| S3 업로드·조회 실패 | 버킷·리전·자격 증명·접근 권한과 사용자 ID |
| 학습 요청 후 결과 없음 | 외부 학습 서버·Runpod 상태와 출력 prefix. 업로드 응답은 학습 완료가 아님 |
| 모듈을 찾지 못함 | 루트 가상환경 사용 여부와 추가 의존성 |
| 오버레이에 이미지가 없음 | 실행 경로별 PNG 폴더, 파일명 파라미터, iFacialMocap UDP 설정 |
| 8000·3000 포트 충돌 | `lsof -i :8000`, `lsof -i :3000`으로 점유 프로세스 확인 후 기존 개발 서버 정상 종료 |

## 패키징 상태

`src/tha4/app/build.sh`는 플랫폼별 `build:*` npm 스크립트를 호출하지만 현재 앱 `package.json`에는 해당 스크립트가 없습니다. 설치 패키지 생성이 완료된 절차로 안내하지 않으며, 배포 빌드에는 스크립트와 Electron의 정적 UI·API 주소 연결 정리가 추가로 필요합니다.

## 참고

- [Firebase UID 사용 가이드](../src/tha4/app/UID_사용법.md)
- [아바타 상세 가이드](../src/tha4/app/avatar/avatar_사용법.md)
- [THA4 모델 준비](distill.md)
- [프로젝트 발표자료](presentation/AI_VTUBER_발표자료.pdf)
