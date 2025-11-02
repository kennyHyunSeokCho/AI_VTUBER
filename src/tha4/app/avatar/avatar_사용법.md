# 🎨 Avatar 페이지 사용법

## 📌 개요

`avatar.html`은 **채팅 UI 형태**로 아바타 이미지를 생성하는 페이지입니다.
사용자가 프롬프트를 입력하면 Firebase Functions를 통해 Runpod에서 이미지를 생성합니다.

---

## 🎯 주요 기능

### 1. **프롬프트 입력 채팅**
- 대화형 UI로 자연스러운 프롬프트 입력
- 예시 프롬프트 자동 표시
- 실시간 메시지 표시

### 2. **Firebase 이미지 생성**
- sh 폴더의 최신 로직 연결
- 실제 Runpod API 호출
- 로딩 상태 표시

### 3. **사용자 인증 통합**
- 로그인 상태 자동 확인
- 사용자 이름 환영 메시지
- UID 기반 이미지 저장

---

## 🔄 사용 흐름

```
1. avatar.html 접속
   ↓
2. 환영 메시지 + 예시 프롬프트 표시
   ↓
3. 사용자가 프롬프트 입력
   ↓
4. "전송" 버튼 클릭 (또는 Enter)
   ↓
5. 로딩 팝업 표시
   ↓
6. Firebase Functions → Runpod → 이미지 생성
   ↓
7. 완료 메시지 표시
   ↓
8. 메인 화면(My)에서 이미지 다운로드
```

---

## 💬 채팅 메시지 예시

### **시스템 메시지** (왼쪽, 검은 배경)
```
안녕하세요, user@example.com님! 원하시는 아바타 이미지를 입력해 주세요!

ex) 귀여운 느낌의 아이돌 소녀, 금발 긴 웨이브, 크고 반짝이는 분홍색 눈동자, 밝은 피부톤, 분홍색과 흰색의 귀여운 의상, 아이돌 애니메이션 스타일
```

### **사용자 메시지** (오른쪽, 분홍 배경)
```
파란 머리카락, 노란 눈동자, 학교 교복을 입은 귀여운 소녀
```

### **결과 메시지** (왼쪽, 검은 배경)
```
✅ 이미지 생성이 완료되었습니다! 메인 화면에서 다운로드하실 수 있습니다.

💡 메인 화면(My)으로 이동하여 "이미지 다운로드" 버튼을 클릭하세요!
```

---

## 🛠️ 기술 구조

### **파일 구성**

```
avatar.html
  ↓ import
avatar-logic.js (새로 생성)
  ↓ import
├─ login-logic.js (인증)
└─ image_model.js (이미지 생성)
      ↓
  Firebase Functions
      ↓
  Runpod API
```

---

## 📝 avatar-logic.js 주요 함수

### 1. `generateAvatarImage(promptText)`
```javascript
// 아바타 이미지 생성 요청
const success = await generateAvatarImage("귀여운 소녀, 파란 머리");

// 내부 동작:
// 1. 로그인 확인
// 2. 프롬프트 검증
// 3. Firebase Functions 호출
// 4. 결과 반환 (true/false)
```

### 2. `downloadAvatarImage()`
```javascript
// 생성된 이미지 다운로드
const success = await downloadAvatarImage();

// 내부 동작:
// 1. 로그인 확인
// 2. Firestore에서 imagePath 조회
// 3. Firebase Storage에서 다운로드
```

### 3. `getCurrentUserInfo()`
```javascript
// 현재 사용자 정보 가져오기
const userInfo = getCurrentUserInfo();

// 반환값:
// {
//   uid: "abc123xyz",
//   email: "user@example.com",
//   displayName: "user@example.com"
// }
```

### 4. `getStatusMessage(status)`
```javascript
// 상태 메시지 반환
const message = getStatusMessage('success');
// → "✅ 이미지 생성이 완료되었습니다! ..."

// 지원 상태:
// - 'loading': 생성 중
// - 'success': 완료
// - 'error': 오류
// - 'unauthorized': 로그인 필요
// - 'empty': 프롬프트 비어있음
```

---

## 🎨 UI 요소

### **채팅 영역**
```html
<div id="chatHistory" class="chat-history">
  <!-- 메시지들이 여기 표시됨 -->
</div>
```

### **입력 영역**
```html
<textarea id="inputField" class="input-field" 
          placeholder="내용을 입력하세요.">
</textarea>
```

### **전송 버튼**
```html
<a class="save-button-link" onclick="sendMessage()">
  <div class="save-button-text">전 송</div>
</a>
```

### **로딩 팝업**
```html
<div id="loadingPopup" class="loading-popup-box">
  <div class="loading-text">이미지를 생성 중입니다. . .</div>
</div>
```

---

## ⚙️ 주요 이벤트 핸들러

### **sendMessage() - 메시지 전송**
```javascript
async function sendMessage() {
  const messageText = inputField.value;
  
  // 1. 빈 메시지 체크
  if (!messageText.trim()) {
    addMessage('⚠️ 프롬프트를 입력해주세요.', 'system');
    return;
  }
  
  // 2. 사용자 메시지 표시
  addMessage(messageText, 'user');
  
  // 3. 로딩 UI 표시
  showLoading();
  
  // 4. Firebase Functions 호출
  const success = await generateAvatarImage(messageText);
  
  // 5. 결과 메시지 표시
  if (success) {
    addMessage('✅ 이미지 생성 완료!', 'system');
  } else {
    addMessage('❌ 이미지 생성 실패', 'system');
  }
}
```

### **Enter 키 전송**
```javascript
inputField.addEventListener('keypress', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

// Shift + Enter: 줄바꿈
// Enter: 전송
```

---

## 🔐 인증 처리

### **로그인 상태 확인**
```javascript
import { isLoggedIn, getCurrentUserInfo } from './avatar-logic.js';

if (!isLoggedIn()) {
  alert('로그인이 필요합니다.');
  // 또는 login.html로 리다이렉트
  window.location.href = 'login.html';
}
```

### **사용자 환영 메시지**
```javascript
function initializeChat() {
  const userInfo = getCurrentUserInfo();
  let greeting = "안녕하세요!";
  
  if (userInfo) {
    greeting = `안녕하세요, ${userInfo.displayName}님!`;
  }
  
  addMessage(greeting + " 원하시는 아바타 이미지를 입력해 주세요!", 'system');
}
```

---

## 📊 데이터 흐름

### **이미지 생성 플로우**
```
[avatar.html]
사용자 입력: "귀여운 소녀, 파란 머리"
    ↓
[avatar-logic.js]
generateAvatarImage(prompt)
    ↓
[image_model.js]
callGenerateImageFunction({ prompt: "..." })
    ↓
[Firebase Functions]
generate_image 호출
    ↓
[Runpod API]
이미지 생성 (3분 소요)
    ↓
[Firebase Storage]
users/{uid}/images/abc123.png 저장
    ↓
[Firestore]
users/{uid}/imagePath 업데이트
    ↓
[avatar.html]
"✅ 완료!" 메시지 표시
```

---

## 🎯 사용 예시

### **예시 1: 기본 사용**
```
1. avatar.html 열기
2. 프롬프트 입력: "파란 머리카락, 노란 눈동자의 소녀"
3. "전송" 클릭
4. 로딩 (3분)
5. "완료!" 메시지
6. index.html로 이동 → "이미지 다운로드" 클릭
```

### **예시 2: 상세 프롬프트**
```
프롬프트 입력:
"1girl, blue hair, yellow eyes, school uniform, 
cute smile, anime style, high quality, 
soft lighting, detailed face"

결과: 상세한 묘사로 더 정확한 이미지 생성
```

### **예시 3: 로그인 없이 접속**
```
1. avatar.html 열기
2. 프롬프트 입력
3. "전송" 클릭
4. 알림: "로그인이 필요합니다."
5. login.html로 이동 권장
```

---

## ⚠️ 주의사항

### 1. **로그인 필수**
- 이미지 생성은 로그인 후에만 가능
- UID가 없으면 이미지 저장 불가

### 2. **생성 시간**
- Cold start: 약 3분
- Warm start: 약 1분
- 로딩 팝업이 표시되는 동안 기다려야 함

### 3. **프롬프트 작성 팁**
```
좋은 예:
"1girl, long blue hair, yellow eyes, school uniform, 
cute smile, anime style, high quality"

나쁜 예:
"예쁜 여자"
```

### 4. **에러 처리**
- 네트워크 오류: 다시 시도
- 인증 오류: 로그인 확인
- 타임아웃: Firebase Functions 상태 확인

---

## 🔧 커스터마이징

### **메시지 스타일 변경**
```css
.chat-message.user {
  background: #FF019B;  /* 사용자 메시지 색상 */
  color: #1B1B1B;
}

.chat-message.system {
  background: #1B1B1B;  /* 시스템 메시지 색상 */
  color: white;
}
```

### **로딩 메시지 변경**
```javascript
// avatar-logic.js
export function getStatusMessage(status) {
  const messages = {
    loading: '🎨 마법을 부리는 중...',
    success: '✨ 완성되었습니다!',
    // ...
  };
  return messages[status];
}
```

---

## 📈 향후 개선 사항

### **계획 중인 기능**
- [ ] 이미지 미리보기
- [ ] 생성 진행률 표시
- [ ] 프롬프트 자동완성
- [ ] 히스토리 저장
- [ ] 즐겨찾기 프롬프트

---

## 🐛 문제 해결

### **Q: 전송 버튼을 눌러도 반응이 없어요**
```
A: 콘솔(F12)을 열어 에러 확인
   → "User not authenticated" 
   → login.html에서 로그인 필요
```

### **Q: 로딩이 끝나지 않아요**
```
A: Firebase Functions 타임아웃 가능성
   1. 네트워크 연결 확인
   2. Firebase 콘솔에서 로그 확인
   3. 페이지 새로고침 후 재시도
```

### **Q: "이미지 생성 완료" 후 다운로드 안 돼요**
```
A: Firestore에 경로가 저장되는 데 시간 소요
   1. 1~2분 대기
   2. index.html에서 "이미지 다운로드" 클릭
   3. 안 되면 "모델 생성 상태 확인" 버튼 클릭
```

---

**작성일**: 2025-11-02  
**파일 위치**: `/src/tha4/app/avatar.html`, `/src/tha4/app/avatar-logic.js`

