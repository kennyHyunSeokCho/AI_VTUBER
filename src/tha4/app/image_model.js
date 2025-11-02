// 이미지 및 모델 생성 관련 Firebase Functions 호출
// sh/app/image_model.js에서 이전됨

import { getFunctions, httpsCallable } from 'https://www.gstatic.com/firebasejs/12.5.0/firebase-functions.js';
import { getStorage, ref, getDownloadURL } from 'https://www.gstatic.com/firebasejs/12.5.0/firebase-storage.js';
import { getFirestore, doc, getDoc } from 'https://www.gstatic.com/firebasejs/12.5.0/firebase-firestore.js';

import { app, auth } from './login-logic.js'

const functions = getFunctions(app);
const storage = getStorage(app);
const db = getFirestore(app);

// Firebase Functions 호출 가능한 함수들
const generateImageCallable = httpsCallable(functions, 'generate_image');
const generateTha4Callable = httpsCallable(functions, 'generate_tha4_model');
const checkModelRequestCallable = httpsCallable(functions, 'check_runpod_pod');
const cancelModelRequestCallable = httpsCallable(functions, 'cancel_runpod_pod');

/**
 * 모델 생성 요청을 취소 (내부적으로는, 요청을 받아 생성된 pod을 삭제함)
 */
export async function callCancelModelRequestCallable() {
  const user = auth.currentUser;
  if (!user) {
    alert("로그인이 필요합니다.");
    console.error("User is not authenticated. Please log in first.");
    return;
  }

  try {
    const result = await cancelModelRequestCallable();
    const returnedData = result.data;

    alert("성공적으로 취소되었습니다.");
    console.log("성공적으로 취소되었습니다.");
  } catch (error) {
    alert(`ERROR, message: ${error.message}`);
  }
}

/**
 * 현재 모델 생성 작업이 실행 중인지 아닌지를 체크
 */
export async function callCheckModelRequestFunction() {
  const user = auth.currentUser;
  if (!user) {
    alert("로그인이 필요합니다.");
    console.error("User is not authenticated. Please log in first.");
    return;
  }

  try {
    const result = await checkModelRequestCallable();
    const returnedData = result.data;
    if (returnedData && typeof returnedData === 'object') {
      if (returnedData['status'] === "IN_PROGRESS") {
        alert(`상태: 진행 중, lastStartedAt: ${returnedData['lastStartedAt']}`);
      } else if (returnedData['status'] === "NONE") {
        alert("현재 진행 중인 모델 생성 프로세스가 없습니다.");
      } else {
        alert(`에러: 알 수 없는 상태 ${returnedData['status']}`);
      }
    }
  } catch (error) {
    console.error("Error occurred while calling checkModelRequestCallable: ", error);
    if (error.code) {
      console.error("Error code: ", error.code);
    }

    throw error;
  }
}

/**
 * 스토리지에 있는 이미지 중 가장 최근에 생성한 이미지를 기반으로 모델 생성 요청
 */
export async function callGenerateTha4ModelFunction() {
  const user = auth.currentUser;
  if (!user) {
    alert("로그인이 필요합니다.");
    console.error("User is not authenticated. Please log in first.");
    return;
  }
  
  const imagePath = await getFieldFromUserDoc(user, "imagePath");
  if (imagePath) {
    try {
      const result = await generateTha4Callable(imagePath);
      alert("모델 생성 요청이 성공했습니다!");
      console.log("Function called successfully!");
      console.log("Server response:", result.data);
    } catch (error) {
      alert("ERROR: " + error.message);
      console.error("Error calling the function:", error);
    }
  } else {
    alert("이미지를 먼저 생성해주세요.");
    console.error("couldn't find the imagePath");
  }
}

/**
 * 이미지 생성 요청을 보내는 함수
 * prompt는 prompt 멤버를 가지는 객체이어야 하고, 이 prompt 멤버에는 사용자가 입력한 프롬프트가 들어감
 * 최종적으로 생성된 이미지는 스토리지에 저장되며, 또한 그 이미지의 스토리지 상 경로가 Firestore의 해당 사용자 문서에(정확히는 imagePath 필드에) 저장됨
 * imagePath는 제일 마지막으로 생성된 이미지의 경로 하나만을 저장함
 * 일단은 이미지 다운로드 및 모델 생성 시 이 imagePath가 가리키는 이미지, 즉 사용자가 제일 마지막으로 생성한 이미지를 대상으로 함
 */
export async function callGenerateImageFunction(prompt) {
  console.log(auth.currentUser);
  if (!auth.currentUser) {
    alert("로그인이 필요합니다.");
    console.error("User is not authenticated. Please log in first.");
    return;
  }
  
  try {
    const result = await generateImageCallable(prompt);

    alert("이미지 생성 요청 성공!");
    console.log("Function called successfully!");
    console.log("Server response:", result.data);
  } catch (error) {
    alert("ERROR: " + error.message);
    console.error("Error calling the function:", error);
    
    if (error.code === 'unauthenticated') {
      console.log("Authentication failed. Please check your token or login state.");
    }
  }
}

/**
 * Firestore에서 사용자 문서의 특정 필드 값을 가져오는 헬퍼 함수
 */
async function getFieldFromUserDoc(user, key) {
  const userDocRef = doc(db, "users", user.uid);

  try {
    const userDocSnap = await getDoc(userDocRef);
    if (userDocSnap.exists()) {
      const field = userDocSnap.get(key)
      if (!field) {
        console.error("No such field: ", key);
        return null;
      }

      console.log(`${key}: ${field}`);
      return field;
    } else {
      console.error("No such user document!");
      return null;
    }
  } catch (error) {
    console.error("Error while getting document: ", error);
    return null;
  }
}

/**
 * 가장 최근에 생성한 이미지 다운로드
 */
export async function downloadUserImage() {
  const user = auth.currentUser;
  if (!user) {
    alert("로그인이 필요합니다.");
    console.error("No user is signed in.");
    return;
  }

  const imagePath = await getFieldFromUserDoc(user, "imagePath");
  if (imagePath) {
    const imageRef = ref(storage, imagePath);
    const imageName = imagePath.split('/').pop();
    if (!imageName) {
      alert(`ERROR: invalid imagePath value: ${imagePath}`);
      console.error(`ERROR: invalid imagePath value: ${imagePath}`);
      return;
    }

    try {
      const url = await getDownloadURL(imageRef);
      
      const link = document.createElement('a');
      link.href = url;
      link.download = imageName;
      document.body.appendChild(link);
      link.click();

      document.body.removeChild(link);
    } catch (error) {
      alert("이미지 다운로드 실패: " + error.message);
      console.error("Error retrieving image for download:", error);
    }
  } else {
    console.error(`ERROR: cannot find the image: ${imagePath}`);
    return;
  }
}

/**
 * 생성된 THA4 모델 다운로드
 */
export async function downloadModel() {
  const user = auth.currentUser;
  if (!user) {
    alert("로그인이 필요합니다.");
    console.error("No user is signed in.");
    return;
  }

  const path = await getFieldFromUserDoc(user, "tha4ModelPath");
  if (path) {
    const modelRef = ref(storage, path);
    const modelName = path.split('/').pop();
    if (!modelName) {
      alert(`ERROR: invalid model path value: ${path}`);
      console.error(`ERROR: invalid model path value: ${path}`);
      return;
    }
    
    try {
      const url = await getDownloadURL(modelRef);

      const link = document.createElement('a');
      link.href = url;
      link.download = modelName;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (error) {
      alert("모델 다운로드 실패: " + error.message);
      console.error("Error while retrieving model for download: ", error);
    }
  }
}

console.log('Image & Model 로직 로드 완료');

