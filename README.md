# AI-VTUBER

AI를 활용한 실시간 음성 변환 소프트웨어입니다.  
*본 프로젝트는 [voice-changer](https://github.com/w-okada/voice-changer) 프로젝트를 참고하여 개발되었습니다.*

> 상태: WIP (미완성). Windows용 Electron 패키징 및 자동 실행 스크립트 정비 중입니다. 현재 `run-win.bat`로 서버 및 Electron 실행은 가능하나, 일부 환경에서 패키징/로드 타이밍 이슈가 있을 수 있습니다.

## 🚀 빠른 시작

### 1. 시스템 요구사항
- **운영체제**: Windows 10/11, macOS (M1/M2), Linux
- **Python**: 3.10.x (정확한 버전 필요 - 3.10.0 이상)
- **Node.js**: 16 이상
- **메모리**: 최소 8GB RAM 권장
- **GPU**: NVIDIA GPU (CUDA 지원) 또는 CPU 사용 가능

### 2. 설치 및 실행

#### 2.1 저장소 클론
```bash
git clone https://github.com/kennyHyunSeokCho/AI_VTUBER.git
cd AI_VTUBER
```

#### 2.2 가상환경 설정 및 의존성 설치
```bash
# Python 가상환경 생성 (Python 3.10.x 필수)
py -3.10 -m venv .venv

# 가상환경 활성화 (Windows)
.\.venv\Scripts\activate

# 가상환경 활성화 (macOS/Linux)
source .venv/bin/activate

# pip 버전 다운그레이드 (fairseq 설치 시 필요)
pip install pip==24.0

# Python 의존성 설치
pip install -r voice-changer/server/requirements.txt

# 추가 필수 패키지 설치 (버전 충돌 해결)
pip install fairseq==0.12.2
pip install pyworld
```

#### 2.3 프론트엔드 빌드
```bash
# 클라이언트 라이브러리 빌드
cd voice-changer/client/lib
npm install
npm run build:prod

# 데모 프론트엔드 빌드
cd ../demo
npm installcd
npm run build:prod

# 레코더 빌드
cd ../../recorder
npm install
npm run build
```

#### 2.4 서버 실행
```bash
# 서버 디렉토리로 이동
cd voice-changer/server

# 서버 실행 (포트 18888, HTTPS 비활성화)
python MMVCServerSIO.py -p 18888 --https false

# 또는 환경 변수와 함께 실행 (Windows에서 문자 인코딩 문제 해결)
$env:PYTHONIOENCODING='utf-8'; python MMVCServerSIO.py -p 18888 --https false
```

#### 2.5 웹 인터페이스 접속
브라우저에서 `http://localhost:18888` 접속

### ⚡ 원클릭 빌드/실행 (권장)

#### Windows
```bat
:: 빌드 (프론트/서버/Electron 포함)
build-win.bat

:: 실행 (백엔드 + Electron 클라이언트 자동 구동)
run-win.bat
```

#### macOS/Linux
```bash
chmod +x build-mac-linux.sh run.sh

# 빌드 (프론트/서버/Electron 포함)
./build-mac-linux.sh

# 실행 (백엔드 + Electron 클라이언트 자동 구동)
./run.sh
```

원클릭 실행은 서버를 18888 포트로 띄운 뒤 Electron 클라이언트(또는 기본 브라우저)에서 `http://localhost:18888/`를 열어줍니다.

### 3. 실행 순서 요약
```bash
# 1. 프로젝트 루트에서 시작
cd AI_VTUBER

# 2. 가상환경 활성화
.\.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # macOS/Linux

# 3. 백엔드 서버 실행 (터미널 1)
cd voice-changer/server
python MMVCServerSIO.py -p 18888 --https false

# 4. 프론트엔드 개발 서버 실행 (터미널 2, 선택사항)
cd ../client/demo
npm run dev  # 개발 모드
# 또는 빌드된 파일 사용 (권장)
npm run build:prod
```

## 🎯 모델 다운로드 및 설정

### 1. 자동 모델 다운로드 방법

#### 방법 1: 서버 실행 시 자동 다운로드
서버를 처음 실행하면 필요한 모델들이 자동으로 다운로드됩니다:
```bash
cd voice-changer/server
python MMVCServerSIO.py -p 18888 --https false
# 첫 실행 시 자동으로 모델 다운로드 시작
```

#### 방법 2: 수동 모델 경로 지정
모델 경로를 직접 지정하여 실행:
```bash
cd voice-changer/server
python MMVCServerSIO.py -p 18888 --https false \
    --content_vec_500 pretrain/checkpoint_best_legacy_500.pt \
    --content_vec_500_onnx pretrain/content_vec_500.onnx \
    --content_vec_500_onnx_on true \
    --hubert_base pretrain/hubert_base.pt \
    --hubert_base_jp pretrain/rinna_hubert_base_jp.pt \
    --hubert_soft pretrain/hubert/hubert-soft-0d54a1f4.pt \
    --nsf_hifigan pretrain/nsf_hifigan/model \
    --crepe_onnx_full pretrain/crepe_onnx_full.onnx \
    --crepe_onnx_tiny pretrain/crepe_onnx_tiny.onnx \
    --rmvpe pretrain/rmvpe.pt \
    --model_dir model_dir \
    --samples samples.json
```

#### 방법 3: 웹 인터페이스에서 샘플 다운로드
1. 웹 인터페이스 접속 (`http://localhost:18888`)
2. 모델 슬롯에서 **"sample"** 버튼 클릭
3. 원하는 샘플 모델 선택하여 다운로드

### 2. 다운로드되는 모델들
프로젝트에는 자동으로 필요한 모델들을 다운로드하는 기능이 내장되어 있습니다:

#### RVC 관련 모델들:
- **Hubert Base**: `https://huggingface.co/ddPn08/rvc-webui-models/resolve/main/embeddings/hubert_base.pt`
- **Hubert Base JP**: `https://huggingface.co/rinna/japanese-hubert-base/resolve/main/fairseq/model.pt`
- **Hubert Soft**: `https://huggingface.co/wok000/weights/resolve/main/ddsp-svc30/embedder/hubert-soft-0d54a1f4.pt`
- **NSF HiFiGAN**: `https://huggingface.co/wok000/weights/resolve/main/ddsp-svc30/nsf_hifigan_20221211/model.bin`
- **Content Vec**: `https://huggingface.co/wok000/weights_gpl/resolve/main/content-vec/contentvec-f.onnx`

#### 음성 분석 모델들:
- **RMVPE**: `https://huggingface.co/wok000/weights/resolve/main/rmvpe/rmvpe_20231006.pt`
- **RMVPE ONNX**: `https://huggingface.co/wok000/weights_gpl/resolve/main/rmvpe/rmvpe_20231006.onnx`
- **CREPE Full**: `https://huggingface.co/wok000/weights/resolve/main/crepe/onnx/full.onnx`
- **CREPE Tiny**: `https://huggingface.co/wok000/weights/resolve/main/crepe/onnx/tiny.onnx`
- **Whisper Tiny**: `https://openaipublic.azureedge.net/main/whisper/models/65147644a518d12f04e32d6f3b26facc3f8dd46e5390956a9424a650c0ce22b9/tiny.pt`

### 2. RVC 음성 모델 다운로드
1. **Hugging Face에서 다운로드**:
   - [RVC 모델 컬렉션](https://huggingface.co/models?library=rvc) 방문
   - 원하는 모델 선택 후 다운로드
   - `.pth` 파일을 `voice-changer/server/model` 폴더에 저장

2. **커뮤니티 모델 사이트**:
   - [RVC 모델 공유 사이트]([https://huggingface.co/spaces/akhaliq/RVC](https://voice-models.com/)) 방문
   - 다양한 캐릭터 음성 모델 다운로드 가능

### 3. Beatrice 모델 다운로드
1. **공식 사이트**: [Beatrice 프로젝트](https://prj-beatrice.com/)
2. **모델 파일**: `.beatrice` 확장자 파일
3. **설치 위치**: `voice-changer/server/model` 폴더

### 4. 모델 업로드 방법
1. 웹 인터페이스에서 **"edit"** 버튼 클릭
2. **"Upload"** 버튼으로 모델 파일 업로드
3. 모델 정보 입력 (이름, 설명 등)
4. **"Save"** 버튼으로 저장

## 🎮 사용법

### 1. 기본 설정
1. **오디오 입력/출력 설정**:
   - Input: 마이크 또는 오디오 입력 장치 선택
   - Output: 스피커 또는 헤드폰 선택
   - Monitor: 실시간 모니터링 설정

2. **품질 설정**:
   - **소음 제거(임계값)**: 배경 소음 제거 강도 조절
   - **CHUNK**: 처리 청크 크기 (낮을수록 지연시간 감소)
   - **GPU**: CUDA 사용 시 GPU 선택, CPU 사용 시 "cpu" 선택

### 2. 음성 변환 시작
1. **모델 선택**: 드롭다운에서 원하는 모델 선택
2. **GAIN 조절**: 입력/출력 볼륨 조절
3. **TUNE**: 음높이 조절 (RVC 모델)
4. **INDEX**: 음색 유사도 조절 (RVC 모델)
5. **"start"** 버튼 클릭하여 변환 시작

### 3. 실시간 모니터링
- **vol**: 현재 음량 레벨
- **buf**: 버퍼링 시간 (ms)
- **res**: 응답 시간 (ms)

## ⚙️ 고급 설정

### 1. 백엔드 서버 정보
- **메인 서버 파일**: `voice-changer/server/MMVCServerSIO.py`
- **포트**: 기본 18888 (변경 가능)
- **프로토콜**: HTTP/WebSocket
- **API 엔드포인트**: `/api/` 경로

#### 서버 실행 옵션:
```bash
# 기본 실행
python MMVCServerSIO.py -p 18888 --https false

# HTTPS 활성화 (SSL 인증서 필요)
python MMVCServerSIO.py -p 18888 --https true --key-path key.pem --cert-path cert.pem

# 서버 오디오 모드 활성화
python MMVCServerSIO.py -p 18888 --https false --enable-server-audio 1

# 로그 레벨 설정
python MMVCServerSIO.py -p 18888 --https false --log-level debug
```

### 2. 서버 모드
네트워크를 통한 분산 처리:
```bash
# 서버 모드로 실행
python MMVCServerSIO.py -p 18888 --https false --enable-server-audio 1
```

### 3. REST API 사용
```bash
# 모델 목록 조회
curl http://localhost:18888/api/models

# 음성 변환 시작
curl -X POST http://localhost:18888/api/start \
  -H "Content-Type: application/json" \
  -d '{"modelSlotIndex": 0}'
```

### 4. 환경 변수 설정
```bash
# 문자 인코딩 설정 (Windows)
set PYTHONIOENCODING=utf-8

# GPU 메모리 설정
set CUDA_VISIBLE_DEVICES=0
```

## 🔧 문제 해결

### 1. 일반적인 문제
- **모듈을 찾을 수 없음**: `pip install` 명령으로 누락된 패키지 설치
- **포트 충돌**: 다른 포트 사용 (`-p 18889`)
- **권한 오류**: 관리자 권한으로 실행

### 2. 의존성 문제 해결
- **fairseq 설치 오류**: `pip install pip==24.0` 후 `pip install fairseq==0.12.2`
- **pyworld 설치 오류**: `pip install pyworld` 실행
- **Python 버전 문제**: 정확히 Python 3.10.x 사용 필요

### 3. 오디오 문제
- **입력이 안됨**: 오디오 드라이버 확인
- **지연시간**: CHUNK 크기 줄이기
- **품질 문제**: GPU 사용 또는 모델 교체

### 4. 모델 문제
- **로딩 실패**: 모델 파일 무결성 확인
- **변환 안됨**: 모델 형식 확인 (RVC: .pth, Beatrice: .beatrice)

## 📁 프로젝트 구조 및 실행 경로

### 🏗️ 전체 프로젝트 구조
```
AI-VTUBER/                        # 프로젝트 루트 디렉토리
├── voice-changer/                 # 메인 프로젝트 폴더 (원본 voice-changer)
│   ├── server/                   # 🔧 백엔드 서버 (여기서 서버 실행)
│   │   ├── MMVCServerSIO.py      # 메인 서버 파일 ⭐ 실행 파일
│   │   ├── requirements.txt      # Python 의존성 목록
│   │   ├── const.py              # 서버 설정 상수
│   │   ├── downloader/           # 모델 다운로더
│   │   │   ├── WeightDownloader.py # 가중치 다운로드 (RMVPE, Hubert 등)
│   │   │   ├── SampleDownloader.py # 샘플 모델 다운로드
│   │   │   └── Downloader.py     # 통합 다운로드 관리자
│   │   ├── voice_changer/        # 음성 변환 엔진
│   │   │   ├── RVC/              # RVC 모델 처리
│   │   │   ├── Beatrice/         # Beatrice 모델 처리
│   │   │   └── VoiceChangerManager.py # 음성 변환 관리자
│   │   ├── restapi/              # REST API 라우터
│   │   │   ├── MMVC_Rest.py      # 메인 API 라우터
│   │   │   └── MMVC_Rest_VoiceChanger.py # 음성 변환 API
│   │   ├── pretrain/             # 자동 생성: 사전 훈련된 모델들
│   │   │   ├── rmvpe.onnx        # RMVPE ONNX 모델 ⭐ 주요 사용
│   │   │   ├── hubert_base.pt    # Hubert Base 모델
│   │   │   └── whisper_tiny.pt   # Whisper 모델
│   │   ├── model_dir/            # 자동 생성: 업로드된 음성 모델들
│   │   └── keys/                 # 자동 생성: SSL 인증서 (HTTPS 사용시)
│   ├── client/                   # 🎨 프론트엔드
│   │   ├── demo/                 # 웹 데모 (여기서 프론트 빌드)
│   │   │   ├── src/              # React/TypeScript 소스 코드
│   │   │   │   ├── components/   # UI 컴포넌트들
│   │   │   │   ├── css/          # 스타일시트 (핑크 테마 적용됨)
│   │   │   │   └── hooks/        # React 훅들
│   │   │   ├── dist/             # 빌드된 파일 (서버에서 서빙)
│   │   │   ├── public/           # 정적 파일들
│   │   │   └── package.json      # npm 설정
│   │   └── lib/                  # 클라이언트 라이브러리
│   │       ├── src/              # TypeScript 소스
│   │       └── dist/             # 빌드된 라이브러리
│   ├── recorder/                 # 🎙️ 오디오 레코더
│   │   ├── src/                  # 레코더 소스 코드
│   │   └── dist/                 # 빌드된 레코더
│   └── README.md                 # 원본 voice-changer 문서
├── README.md                     # 이 파일 (AI-VTUBER 가이드)
├── .gitignore                    # Git 제외 설정
├── samples_*.json               # 샘플 설정 파일들
└── stored_setting.json           # 저장된 설정
```

### 🎯 주요 사용 모델: RMVPE ONNX
**RMVPE ONNX**는 이 프로젝트에서 가장 많이 사용되는 음성 분석 모델입니다:

#### RMVPE ONNX 특징:
- **파일 위치**: `voice-changer/server/pretrain/rmvpe.onnx`
- **용도**: 음성의 피치(Pitch) 추출 및 분석
- **장점**: 
  - CPU에서도 빠른 처리 속도
  - 높은 정확도
  - 메모리 효율적
- **자동 다운로드**: 서버 첫 실행 시 자동으로 다운로드됨
- **수동 다운로드 URL**: `https://huggingface.co/wok000/weights_gpl/resolve/main/rmvpe/rmvpe_20231006.onnx`

#### RMVPE ONNX 사용 설정:
```bash
# 서버 실행 시 RMVPE ONNX 활성화
cd voice-changer/server
python MMVCServerSIO.py -p 18888 --https false \
    --rmvpe pretrain/rmvpe.pt \
    --rmvpe_onnx pretrain/rmvpe.onnx \
    --rmvpe_onnx_on true
```

### 🚀 주요 실행 파일들

#### 🔧 백엔드 서버 실행
```bash
# 서버 디렉토리로 이동
cd voice-changer/server

# 기본 실행 (RMVPE ONNX 자동 활성화)
python MMVCServerSIO.py -p 18888 --https false

# 상세 옵션과 함께 실행
python MMVCServerSIO.py -p 18888 --https false \
    --rmvpe_onnx_on true \
    --hubert_base pretrain/hubert_base.pt \
    --model_dir model_dir
```

#### 🎨 프론트엔드 빌드 및 실행
```bash
# 클라이언트 라이브러리 빌드
cd voice-changer/client/lib
npm install
npm run build

# 데모 프론트엔드 빌드 (핑크 테마 적용됨)
cd ../demo
npm install
npm run build:prod

# 개발 모드 실행 (선택사항)
npm run dev
```

#### 📁 주요 디렉토리
- **모델 저장**: `voice-changer/server/model_dir/`
- **사전 훈련 모델**: `voice-changer/server/pretrain/`
- **설정 파일**: `voice-changer/server/const.py`, `voice-changer/server/restapi/MMVC_Rest.py`
- **빌드된 프론트엔드**: `voice-changer/client/demo/dist/`

### 📥 모델 다운로드 로직 위치
- **자동 다운로드**: `voice-changer/server/downloader/WeightDownloader.py`
- **샘플 다운로드**: `voice-changer/server/downloader/SampleDownloader.py`
- **다운로드 실행**: `voice-changer/server/downloader/Downloader.py`
- **모델 관리**: `voice-changer/server/voice_changer/VoiceChangerManager.py`

### ⚠️ 중요: 올바른 실행 디렉토리
서버를 실행할 때는 반드시 `voice-changer/server` 디렉토리에서 실행해야 합니다:

```bash
# ✅ 올바른 방법
cd voice-changer/server
python MMVCServerSIO.py -p 18888 --https false

# ❌ 잘못된 방법 (프로젝트 루트에서 실행)
cd AI-VTUBER
python voice-changer/server/MMVCServerSIO.py -p 18888 --https false
```

### 📁 자동 생성되는 폴더들
서버 실행 시 다음 폴더들이 자동으로 생성됩니다:

#### `voice-changer/server/pretrain/` 폴더
- **생성 위치**: `AI-VTUBER/voice-changer/server/pretrain/`
- **내용**: 다운로드된 모델 파일들
- **파일 예시**: `hubert_base.pt`, `rmvpe.onnx`, `whisper_tiny.pt`
- **생성 조건**: 서버를 올바른 디렉토리에서 실행했을 때

#### `voice-changer/server/keys/` 폴더  
- **생성 위치**: `AI-VTUBER/voice-changer/server/keys/`
- **내용**: SSL 인증서 파일들 (`.cert`, `.key`)
- **생성 조건**: HTTPS 모드로 실행했을 때
- **파일 예시**: `20251014_132610.cert`

#### `voice-changer/server/model_dir/` 폴더
- **생성 위치**: `AI-VTUBER/voice-changer/server/model_dir/`
- **내용**: 업로드된 음성 모델들
- **생성 조건**: 모델 업로드 시

### 🔧 폴더가 잘못된 위치에 생성된 경우
만약 프로젝트 루트에 `pretrain`, `keys` 폴더가 생성되었다면:

1. **잘못된 폴더 삭제**:
```bash
# 프로젝트 루트에서 실행
rmdir /s pretrain
rmdir /s keys
```

2. **올바른 위치에서 서버 재실행**:
```bash
cd voice-changer/server
python MMVCServerSIO.py -p 18888 --https false
```

## 🤝 기여하기
1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 라이선스
이 프로젝트는 [voice-changer](https://github.com/w-okada/voice-changer) 프로젝트를 참고하여 개발되었습니다.

## ⚠️ 면책 조항
본 소프트웨어의 사용 또는 사용 불가로 인해 발생하는 모든 직접적, 간접적, 파생적, 결과적 또는 특별한 손해에 대해 일체의 책임을 지지 않습니다.

## 📞 지원
- **이슈 리포트**: GitHub Issues 사용
- **문서**: [원본 문서](https://github.com/w-okada/voice-changer) 참조
- **커뮤니티**: Discord 또는 Reddit 커뮤니티 참여

---

**AI-VTUBER** - 당신의 음성을 AI로 변환하세요! 🎤✨
