// 아바타 이미지 생성 및 다운로드 로직
// avatar.html 전용

import { auth, isLoggedIn } from './login-logic.js';
import { callGenerateImageFunction, downloadUserImage } from './image_model.js';

/**
 * 아바타 이미지 생성 요청
 * @param {string} promptText - 사용자가 입력한 프롬프트
 * @returns {Promise<boolean>} 성공 여부
 */
export async function generateAvatarImage(promptText) {
  // 로그인 확인
  if (!isLoggedIn()) {
    console.error('User not authenticated');
    return false;
  }

  // 프롬프트 검증
  if (!promptText || promptText.trim().length === 0) {
    return false;
  }

  try {
    console.log('🎨 아바타 이미지 생성 시작:', promptText);
    
    // 프롬프트 객체 생성
    const prompt = {
      prompt: promptText.trim()
    };

    // Firebase Functions 호출
    await callGenerateImageFunction(prompt);
    
    console.log('✅ 아바타 이미지 생성 요청 완료');
    return true;

  } catch (error) {
    console.error('❌ 아바타 이미지 생성 실패:', error);
    return false;
  }
}

/**
 * 생성된 아바타 이미지 다운로드
 * @returns {Promise<boolean>} 성공 여부
 */
export async function downloadAvatarImage() {
  if (!isLoggedIn()) {
    return false;
  }

  try {
    console.log('📥 아바타 이미지 다운로드 시작');
    
    // image_model.js의 다운로드 함수 사용
    await downloadUserImage();
    
    console.log('✅ 아바타 이미지 다운로드 완료');
    return true;

  } catch (error) {
    console.error('❌ 아바타 이미지 다운로드 실패:', error);
    return false;
  }
}

/**
 * 현재 로그인한 사용자 정보 가져오기
 */
export function getCurrentUserInfo() {
  const user = auth.currentUser;
  if (user) {
    return {
      uid: user.uid,
      email: user.email,
      displayName: user.displayName || user.email
    };
  }
  return null;
}

console.log('✅ Avatar 로직 로드 완료');

