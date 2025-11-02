// 아바타 이미지 생성 로직
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
    alert('로그인이 필요합니다. 메인 화면에서 로그인해주세요.');
    console.error('User not authenticated');
    return false;
  }

  // 프롬프트 검증
  if (!promptText || promptText.trim().length === 0) {
    alert('프롬프트를 입력해주세요.');
    return false;
  }

  try {
    console.log('아바타 이미지 생성 시작:', promptText);
    
    // 프롬프트 객체 생성
    const prompt = {
      prompt: promptText.trim()
    };

    // Firebase Functions 호출 (image_model.js의 함수 사용)
    await callGenerateImageFunction(prompt);
    
    console.log('✅ 아바타 이미지 생성 요청 완료');
    return true;

  } catch (error) {
    console.error('❌ 아바타 이미지 생성 실패:', error);
    alert('이미지 생성 중 오류가 발생했습니다: ' + error.message);
    return false;
  }
}

/**
 * 생성된 아바타 이미지 다운로드
 * @returns {Promise<boolean>} 성공 여부
 */
export async function downloadAvatarImage() {
  if (!isLoggedIn()) {
    alert('로그인이 필요합니다.');
    return false;
  }

  try {
    console.log('아바타 이미지 다운로드 시작');
    
    // image_model.js의 다운로드 함수 사용
    await downloadUserImage();
    
    console.log('✅ 아바타 이미지 다운로드 완료');
    return true;

  } catch (error) {
    console.error('❌ 아바타 이미지 다운로드 실패:', error);
    alert('이미지 다운로드 중 오류가 발생했습니다: ' + error.message);
    return false;
  }
}

/**
 * 현재 로그인한 사용자 정보 가져오기
 * @returns {Object|null} 사용자 정보
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

/**
 * 채팅 형태로 이미지 생성 상태 메시지 반환
 * @param {string} status - 상태 ('loading', 'success', 'error')
 * @returns {string} 상태 메시지
 */
export function getStatusMessage(status) {
  const messages = {
    loading: '이미지를 생성 중입니다. 잠시만 기다려주세요... (약 3분 소요)',
    success: '✅ 이미지 생성이 완료되었습니다! 메인 화면에서 다운로드하실 수 있습니다.',
    error: '❌ 이미지 생성 중 오류가 발생했습니다. 다시 시도해주세요.',
    unauthorized: '⚠️ 로그인이 필요합니다. 메인 화면에서 로그인해주세요.',
    empty: '⚠️ 프롬프트를 입력해주세요.'
  };
  
  return messages[status] || '알 수 없는 상태입니다.';
}

console.log('Avatar 로직 로드 완료');

