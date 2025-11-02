// Firebase 인증 로직
// sh/app/login.js에서 이전됨

import { firebaseConfig } from './config.js';

// Firebase CDN import
import { initializeApp } from 'https://www.gstatic.com/firebasejs/12.5.0/firebase-app.js'
import {
  getAuth,
  signOut,
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  onAuthStateChanged,
  GoogleAuthProvider,
  signInWithPopup
} from 'https://www.gstatic.com/firebasejs/12.5.0/firebase-auth.js';

// Firebase 초기화
export const app = initializeApp(firebaseConfig);
export const auth = getAuth();

// DOM 요소 (기존 login.html의 id 사용) - 페이지 로드 후 초기화
let emailInput = null;
let passwordInput = null;
let signInButton = null;
let signUpButton = null;
let googleSignInButton = null;  // Google 로그인 버튼

// DOM이 로드된 후 요소들을 초기화
function initializeElements() {
  emailInput = document.getElementById('loginIdInput');  // 이메일 입력
  passwordInput = document.getElementById('loginPwInput');  // 비밀번호 입력
  signInButton = document.querySelector('.image-login-button-link');  // 로그인 버튼
  signUpButton = document.querySelector('.text-signup');  // 회원가입 버튼
  googleSignInButton = document.getElementById('googleSignInBtn');  // Google 로그인 버튼
  
  console.log('DOM 요소 초기화:', {
    emailInput: !!emailInput,
    passwordInput: !!passwordInput,
    signInButton: !!signInButton,
    signUpButton: !!signUpButton,
    googleSignInButton: !!googleSignInButton
  });
}

/**
 * 로그인/로그아웃 토글 처리
 */
export function toggleSignIn(event) {
  // a 태그 기본 동작 방지
  if (event) {
    event.preventDefault();
  }
  
  if (auth.currentUser) {
    // 로그아웃
    signOut(auth);
    alert('로그아웃 되었습니다.');
  } else {
    // 로그인
    const email = emailInput.value;
    const password = passwordInput.value;
    
    if (email.length < 4) {
      alert('이메일을 입력해주세요.');
      return;
    }
    if (password.length < 4) {
      alert('비밀번호를 입력해주세요.');
      return;
    }
    
    // Firebase 로그인
    signInWithEmailAndPassword(auth, email, password)
      .then(() => {
        alert('로그인 성공!');
        // 로그인 성공 시 index.html로 이동
        window.location.href = 'index.html';
      })
      .catch(function (error) {
        const errorCode = error.code;
        const errorMessage = error.message;
        
        if (errorCode === 'auth/wrong-password') {
          alert('비밀번호가 틀렸습니다.');
        } else if (errorCode === 'auth/user-not-found') {
          alert('존재하지 않는 사용자입니다.');
        } else if (errorCode === 'auth/invalid-email') {
          alert('유효하지 않은 이메일 형식입니다.');
        } else {
          alert('로그인 실패: ' + errorMessage);
        }
        console.error('로그인 에러:', error);
      });
  }
}

/**
 * 회원가입 처리
 */
export function handleSignUp(event) {
  console.log('🔥 handleSignUp 함수 호출됨!');
  
  if (event) {
    event.preventDefault();
    console.log('이벤트 기본 동작 방지됨');
  }
  
  const email = emailInput?.value;
  const password = passwordInput?.value;
  
  console.log('입력된 이메일:', email);
  console.log('입력된 비밀번호 길이:', password?.length);
  
  if (!emailInput || !passwordInput) {
    alert('입력 필드를 찾을 수 없습니다. 페이지를 새로고침해주세요.');
    console.error('입력 필드 없음:', { emailInput, passwordInput });
    return;
  }
  
  if (email.length < 4) {
    alert('이메일을 입력해주세요.');
    return;
  }
  if (password.length < 4) {
    alert('비밀번호는 최소 4자 이상이어야 합니다.');
    return;
  }
  
  console.log('✅ 유효성 검사 통과, Firebase 회원가입 시작...');
  
  // Firebase 회원가입
  createUserWithEmailAndPassword(auth, email, password)
    .then(() => {
      console.log('✅ 회원가입 성공!');
      alert('회원가입이 완료되었습니다!');
    })
    .catch(function (error) {
      const errorCode = error.code;
      const errorMessage = error.message;
      
      console.error('❌ 회원가입 실패:', errorCode, errorMessage);
      
      if (errorCode === 'auth/weak-password') {
        alert('비밀번호가 너무 약합니다.');
      } else if (errorCode === 'auth/email-already-in-use') {
        alert('이미 사용 중인 이메일입니다.');
      } else if (errorCode === 'auth/invalid-email') {
        alert('유효하지 않은 이메일 형식입니다.');
      } else {
        alert('회원가입 실패: ' + errorMessage);
      }
      console.error('회원가입 에러:', error);
    });
}

/**
 * Google 계정으로 로그인
 */
export function signInWithGoogle(event) {
  console.log('🔥 Google 로그인 시작!');
  
  if (event) {
    event.preventDefault();
  }
  
  // 이미 로그인되어 있는 경우
  if (auth.currentUser) {
    console.log('이미 로그인되어 있습니다:', auth.currentUser.email);
    alert('이미 로그인되어 있습니다.');
    return;
  }
  
  // Google OAuth Provider 생성
  const provider = new GoogleAuthProvider();
  // Google 연락처 읽기 권한 추가 (선택사항)
  provider.addScope('https://www.googleapis.com/auth/contacts.readonly');
  
  console.log('Google 팝업 로그인 시도...');
  
  // 팝업으로 Google 로그인
  signInWithPopup(auth, provider)
    .then((result) => {
      if (!result) {
        console.error('로그인 결과가 없습니다.');
        return;
      }
      
      // Google Access Token 가져오기
      const credential = GoogleAuthProvider.credentialFromResult(result);
      const token = credential?.accessToken;
      const user = result.user;
      
      console.log('✅ Google 로그인 성공!');
      console.log('사용자:', user.email);
      console.log('UID:', user.uid);
      console.log('Access Token:', token ? '발급됨' : '없음');
      
      alert(`환영합니다, ${user.displayName || user.email}님!`);
      
      // 로그인 성공 후 메인 페이지로 이동
      window.location.href = 'index.html';
    })
    .catch((error) => {
      const errorCode = error.code;
      const errorMessage = error.message;
      const email = error.email;
      
      console.error('❌ Google 로그인 실패:', errorCode, errorMessage);
      
      if (errorCode === 'auth/account-exists-with-different-credential') {
        alert('이 이메일은 이미 다른 로그인 방식으로 가입되어 있습니다.\n이메일/비밀번호 로그인을 시도해주세요.');
      } else if (errorCode === 'auth/popup-closed-by-user') {
        console.log('사용자가 팝업을 닫았습니다.');
      } else if (errorCode === 'auth/cancelled-popup-request') {
        console.log('팝업 요청이 취소되었습니다.');
      } else if (errorCode === 'auth/popup-blocked') {
        alert('팝업이 차단되었습니다. 브라우저 설정에서 팝업을 허용해주세요.');
      } else {
        alert('Google 로그인 실패: ' + errorMessage);
      }
    });
}

/**
 * 현재 로그인한 사용자의 UID를 가져오는 헬퍼 함수
 * @returns {string|null} 로그인된 사용자의 UID, 로그아웃 상태면 null
 */
export function getCurrentUserId() {
  return auth.currentUser ? auth.currentUser.uid : null;
}

/**
 * 현재 로그인한 사용자 정보를 가져오는 헬퍼 함수
 * @returns {Object|null} 사용자 객체 또는 null
 */
export function getCurrentUser() {
  return auth.currentUser;
}

/**
 * 로그인 여부 확인 헬퍼 함수
 * @returns {boolean} 로그인 상태
 */
export function isLoggedIn() {
  return !!auth.currentUser;
}

// 인증 상태 변경 감지
onAuthStateChanged(auth, function (user) {
  if (user) {
    // 로그인 상태
    console.log('로그인됨:', user.email);
    console.log('사용자 UID:', user.uid);
    
    // localStorage에 사용자 정보 저장
    localStorage.setItem('vtuber_user_name', user.email);
    localStorage.setItem('vtuber_user_uid', user.uid);
    localStorage.setItem('vtuber_user_email', user.email);
    
    // 로그인 시간 기록
    localStorage.setItem('vtuber_login_time', new Date().toISOString());
    
    console.log('✅ 사용자 정보가 localStorage에 저장되었습니다.');
  } else {
    // 로그아웃 상태
    console.log('로그아웃 상태');
    
    // localStorage에서 사용자 정보 제거
    localStorage.removeItem('vtuber_user_name');
    localStorage.removeItem('vtuber_user_uid');
    localStorage.removeItem('vtuber_user_email');
    localStorage.removeItem('vtuber_login_time');
    
    console.log('✅ 사용자 정보가 localStorage에서 제거되었습니다.');
  }
});

// DOM이 로드된 후 이벤트 리스너 등록
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', setupEventListeners);
} else {
  // 이미 로드된 경우 즉시 실행
  setupEventListeners();
}

function setupEventListeners() {
  console.log('📝 setupEventListeners 시작...');
  
  // DOM 요소 초기화
  initializeElements();
  
  // 이벤트 리스너 등록
  if (signInButton) {
    console.log('✅ 로그인 버튼 찾음:', signInButton);
    signInButton.addEventListener('click', toggleSignIn);
  } else {
    console.error('❌ 로그인 버튼을 찾을 수 없습니다.');
  }

  if (signUpButton) {
    console.log('✅ 회원가입 버튼 찾음:', signUpButton);
    signUpButton.style.cursor = 'pointer';
    signUpButton.addEventListener('click', handleSignUp);
  } else {
    console.error('❌ 회원가입 버튼을 찾을 수 없습니다.');
  }
  
  // Google 로그인 버튼
  if (googleSignInButton) {
    console.log('✅ Google 로그인 버튼 찾음:', googleSignInButton);
    googleSignInButton.addEventListener('click', signInWithGoogle);
  } else {
    console.error('❌ Google 로그인 버튼을 찾을 수 없습니다.');
  }

  // Enter 키로 로그인
  if (passwordInput) {
    passwordInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') {
        toggleSignIn();
      }
    });
  }

  // 이메일과 비밀번호 입력 필드 확인
  console.log('이메일 입력 필드:', emailInput);
  console.log('비밀번호 입력 필드:', passwordInput);
  console.log('Firebase 로그인 로직 로드 완료');
}

