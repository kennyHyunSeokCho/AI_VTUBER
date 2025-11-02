# VoiceChanger UI 커스터마이징

이 폴더에는 VoiceChanger의 UI를 커스터마이징한 파일들이 포함되어 있습니다.

## 📁 폴더 구조

```
voice_changer_UI/
├── README.md              # 이 파일
├── index.html             # 커스텀 테마가 적용된 HTML
└── gui_settings/
    ├── GUI.json          # 일반 UI 설정
    └── RVC.json          # RVC 전용 UI 설정
```

## 🎨 커스터마이징 내용

### 1. **index.html** - 핑크/블랙 테마

- **색상 테마**: #FF019B (핑크) + 블랙
- **폰트**: 시스템 폰트 (macOS, Windows 호환)
- **버튼**: 핑크 배경 + 호버 효과
- **입력 필드**: 다크 테마 + 핑크 포커스
- **스크롤바**: 핑크 색상
- **데코레이션**: 반투명 원형 배경 요소

### 2. **GUI.json** - UI 레이아웃 설정

```json
{
  "mainTitle": "Realtime VoiceChanger",
  "subTitle": "도전! 버튜버"
}
```

- **Pitch Detectors**: dio, harvest, crepe, crepe_full, crepe_tiny, rmvpe, rmvpe_onnx
- **Input Chunk 크기**: 1 ~ 16384

### 3. **RVC.json** - RVC 모드 설정

RVC 전용 UI 설정 (GUI.json과 동일한 커스터마이징)

## 🔧 적용 방법

### 원본 파일 위치
```
voice_changer/MMVCServerSIO.app/Contents/MacOS/dist/
├── index.html
└── assets/gui_settings/
    ├── GUI.json
    └── RVC.json
```

### 적용하기

1. **VoiceChanger 서버가 실행 중이면 종료**
2. **파일 백업 (선택사항)**
   ```bash
   cd voice_changer/MMVCServerSIO.app/Contents/MacOS/dist/
   cp index.html index.html.backup
   cp -r assets/gui_settings assets/gui_settings.backup
   ```

3. **커스텀 파일 적용**
   ```bash
   # index.html 교체
   cp voice_changer_UI/index.html voice_changer/MMVCServerSIO.app/Contents/MacOS/dist/index.html
   
   # GUI 설정 파일 교체
   cp voice_changer_UI/gui_settings/*.json voice_changer/MMVCServerSIO.app/Contents/MacOS/dist/assets/gui_settings/
   ```

4. **VoiceChanger 재시작**
   - Electron 앱에서 VoiceChanger 메뉴 클릭
   - 또는 `./startHttp.command` 직접 실행

## 🎨 테마 수정하기

### 색상 변경

`index.html`의 CSS 변수를 수정:

```css
:root {
    --primary-pink: #FF019B;      /* 메인 핑크 색상 */
    --primary-black: #000000;     /* 블랙 */
    --bg-dark: #151515;           /* 다크 배경 */
    --bg-darker: #0a0a0a;         /* 더 어두운 배경 */
    --text-light: #e5e5e5;        /* 텍스트 색상 */
}
```

### 타이틀 변경

`gui_settings/GUI.json` 또는 `RVC.json` 수정:

```json
{
  "mainTitle": "원하는 타이틀",
  "subTitle": "원하는 서브타이틀"
}
```

### 폰트 변경

`index.html`의 `font-family` 수정:

```css
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Malgun Gothic', sans-serif !important;
}
```

## 📋 주요 스타일 컴포넌트

### 버튼
```css
#app button {
    background: var(--primary-pink) !important;
    color: white !important;
    border: 2px solid var(--primary-black) !important;
    border-radius: 8px !important;
}
```

### 입력 필드
```css
#app input, #app select, #app textarea {
    background: var(--bg-dark) !important;
    border: 2px solid #2a2a2a !important;
    color: var(--text-light) !important;
}
```

### 헤더
```css
#app [class*="Header"] {
    background: linear-gradient(135deg, var(--primary-pink) 0%, #d4017e 100%) !important;
    border-bottom: 3px solid var(--primary-black) !important;
}
```

## ⚠️ 주의사항

1. **index.js는 수정하지 마세요**
   - 3.1MB의 minified React 번들 파일
   - 수정 시 VoiceChanger 작동 불가

2. **백업 필수**
   - 적용 전 항상 원본 파일 백업

3. **VoiceChanger 업데이트 시**
   - 새 버전 설치 후 다시 적용 필요

## 🔄 원본으로 되돌리기

```bash
cd voice_changer/MMVCServerSIO.app/Contents/MacOS/dist/
mv index.html.backup index.html
mv assets/gui_settings.backup assets/gui_settings
```

## 📝 파일 설명

### index.html
- VoiceChanger 웹 UI의 메인 HTML
- 커스텀 CSS 스타일 포함
- React 앱(`index.js`)을 로드

### gui_settings/GUI.json
- UI 구성 요소 정의
- 헤더, 메뉴, 설정 옵션 구성

### gui_settings/RVC.json
- RVC(Retrieval-based Voice Conversion) 전용 설정
- GUI.json과 구조 동일

## 🎯 결과

- ✅ 통일된 핑크/블랙 테마
- ✅ 깔끔한 시스템 폰트
- ✅ 부드러운 애니메이션
- ✅ 한글 타이틀 지원
- ✅ 반응형 디자인

## 📚 참고

- VoiceChanger 원본: [w-okada/voice-changer](https://github.com/w-okada/voice-changer)
- 테마 컨셉: "도전! 버튜버" 메인 앱과 통일

