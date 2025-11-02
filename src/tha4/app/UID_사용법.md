# 🔑 UID 사용법 가이드

## 📌 UID란?

**UID (User ID)**는 Firebase Authentication에서 각 사용자에게 부여하는 **고유 식별자**입니다.
- 로그인 방법(이메일, 구글 등)과 무관하게 **동일한 사용자는 항상 같은 UID**를 가집니다.
- Firebase Storage, Firestore에서 사용자별 데이터를 구분할 때 사용됩니다.

---

## 🎯 UID 접근 방법 (3가지)

### 1️⃣ **Firebase Auth 객체로 직접 접근** (권장 ⭐)

```javascript
import { auth } from './login-logic.js';

// 현재 로그인한 사용자의 UID
const uid = auth.currentUser?.uid;

// 사용자 정보 전체
const user = auth.currentUser;
console.log('UID:', user.uid);
console.log('Email:', user.email);
console.log('Display Name:', user.displayName);
```

**장점**: 항상 최신 상태 반영, Firebase에서 관리

---

### 2️⃣ **헬퍼 함수 사용** (편리함 🚀)

```javascript
import { getCurrentUserId, getCurrentUser, isLoggedIn } from './login-logic.js';

// UID만 가져오기
const uid = getCurrentUserId();  // 로그아웃 시 null 반환

// 사용자 객체 전체 가져오기
const user = getCurrentUser();   // 로그아웃 시 null 반환

// 로그인 여부 확인
if (isLoggedIn()) {
  console.log('로그인 상태입니다.');
}
```

**장점**: 간결한 코드, null 체크 불필요

---

### 3️⃣ **localStorage에서 가져오기** (오프라인)

```javascript
// localStorage에 저장된 UID (로그인 시 자동 저장)
const uid = localStorage.getItem('vtuber_user_uid');
const email = localStorage.getItem('vtuber_user_email');
const userName = localStorage.getItem('vtuber_user_name');
const loginTime = localStorage.getItem('vtuber_login_time');
```

**장점**: 페이지 새로고침 후에도 접근 가능  
**단점**: 로그아웃 후에도 남아있을 수 있음 (주의!)

---

## 📦 실제 사용 예시

### 예시 1: Firebase Functions 호출 시 UID 사용

```javascript
import { auth } from './login-logic.js';
import { getFunctions, httpsCallable } from 'firebase/functions';

async function generateImage(prompt) {
  const user = auth.currentUser;
  
  if (!user) {
    alert('로그인이 필요합니다.');
    return;
  }
  
  console.log('현재 사용자 UID:', user.uid);
  
  // Firebase Functions는 자동으로 auth.currentUser를 인식
  const functions = getFunctions();
  const generateImageCallable = httpsCallable(functions, 'generate_image');
  
  const result = await generateImageCallable({ prompt });
  console.log('결과:', result.data);
}
```

### 예시 2: Firestore에서 사용자 데이터 가져오기

```javascript
import { auth } from './login-logic.js';
import { getFirestore, doc, getDoc } from 'firebase/firestore';

async function getUserProfile() {
  const user = auth.currentUser;
  
  if (!user) {
    console.error('로그인 필요');
    return null;
  }
  
  const db = getFirestore();
  const userDocRef = doc(db, "users", user.uid);  // UID로 문서 접근
  
  const userDocSnap = await getDoc(userDocRef);
  
  if (userDocSnap.exists()) {
    const userData = userDocSnap.data();
    console.log('사용자 데이터:', userData);
    return userData;
  } else {
    console.log('사용자 문서가 없습니다.');
    return null;
  }
}
```

### 예시 3: Storage 경로에 UID 사용

```javascript
import { auth } from './login-logic.js';
import { getStorage, ref, getDownloadURL } from 'firebase/storage';

async function downloadUserImage() {
  const user = auth.currentUser;
  
  if (!user) {
    alert('로그인이 필요합니다.');
    return;
  }
  
  const storage = getStorage();
  
  // UID를 경로에 포함: users/{uid}/images/
  const imagePath = `users/${user.uid}/images/profile.png`;
  const imageRef = ref(storage, imagePath);
  
  try {
    const url = await getDownloadURL(imageRef);
    console.log('이미지 URL:', url);
    
    // 다운로드
    const link = document.createElement('a');
    link.href = url;
    link.download = 'profile.png';
    link.click();
  } catch (error) {
    console.error('이미지 다운로드 실패:', error);
  }
}
```

---

## 🔄 UID가 저장/사용되는 곳

### 1. **로그인 시 자동 저장**
```javascript
// login-logic.js의 onAuthStateChanged에서 자동 실행
localStorage.setItem('vtuber_user_uid', user.uid);
localStorage.setItem('vtuber_user_email', user.email);
```

### 2. **Firestore 경로**
```
users/{uid}/
  ├─ imagePath: "users/{uid}/images/abc123.png"
  └─ tha4ModelPath: "users/{uid}/models/model.pt"
```

### 3. **Firebase Storage 경로**
```
users/{uid}/
  ├─ images/
  │   ├─ abc123.png
  │   └─ def456.png
  └─ models/
      └─ model.pt
```

---

## ⚠️ 주의사항

### ❌ 하지 말아야 할 것

```javascript
// 나쁜 예: auth.currentUser가 null일 수 있음
const uid = auth.currentUser.uid;  // ❌ 에러 발생 가능

// 좋은 예: null 체크
const uid = auth.currentUser?.uid;  // ✅ 안전
```

```javascript
// 나쁜 예: localStorage만 믿기
const uid = localStorage.getItem('vtuber_user_uid');  // ❌ 로그아웃 후에도 남아있을 수 있음

// 좋은 예: Firebase Auth 우선
const uid = auth.currentUser?.uid || localStorage.getItem('vtuber_user_uid');  // ✅
```

### ✅ 권장사항

1. **Firebase Auth 우선**: `auth.currentUser` 사용
2. **null 체크**: 옵셔널 체이닝(`?.`) 사용
3. **헬퍼 함수 활용**: `getCurrentUserId()` 사용
4. **로그인 확인**: 중요한 작업 전에 `isLoggedIn()` 확인

---

## 🎓 완전한 예시 코드

```javascript
import { auth, getCurrentUserId, isLoggedIn } from './login-logic.js';

async function myFunction() {
  // 방법 1: 직접 체크
  if (!auth.currentUser) {
    alert('로그인이 필요합니다.');
    return;
  }
  const uid1 = auth.currentUser.uid;
  
  // 방법 2: 헬퍼 함수
  if (!isLoggedIn()) {
    alert('로그인이 필요합니다.');
    return;
  }
  const uid2 = getCurrentUserId();
  
  // 방법 3: localStorage (백업용)
  const uid3 = localStorage.getItem('vtuber_user_uid');
  
  console.log('모두 같은 값:', uid1 === uid2 && uid2 === uid3);
  
  // UID 사용
  console.log('사용자 UID:', uid1);
  await processUserData(uid1);
}
```

---

## 📚 추가 리소스

- **Firebase Auth 공식 문서**: https://firebase.google.com/docs/auth
- **현재 사용자 가져오기**: `auth.currentUser`
- **인증 상태 감지**: `onAuthStateChanged(auth, callback)`

---

**작성일**: 2025-11-02  
**파일 위치**: `/src/tha4/app/login-logic.js`

