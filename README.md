
# 로그인 및 이미지 생성 요청, 생성된 이미지 다운로드

https://github.com/firebase/quickstart-js/tree/master/auth 참고:
1. 필요한 의존성 다운로드 받고 (`npm install`)
2. 첨부한 파일로 덮어씌우고
3. `npm run dev`로 로컬에 서버 연 다음 google popup 로그인 문서로 들어가면 됩니다.

일단 로그인은 구글로만 가능하게 설정했고, google-popup.ts에 요청을 보내고 이미지를 받는 함수를 추가했습니다.

요청은 클라이언트 -> Firebase 백엔드 -> Runpod으로 전달되며, 최종적으로 생성된 이미지는 Firebase 백엔드와 연결된 스토리지에 저장됩니다.

사용자는 기본적으로 "prompt", "negative_prompt" 두 가지 프롬프트를 작성해 보낼 수 있으며, google-popup.ts 파일 내부에 있는 prompt 변수를 수정해주시면 됩니다.

이미지 생성은 cold start 기준으로 3분 정도 걸리므로 넉넉하게 시간 잡은 후에 '이미지 다운로드 테스트' 눌러주시면 될 것 같습니다.

또한 테스트 해주실 때 꼭 F12로 DevTools 켜서 콘솔 로그를 보시면서 해주세요. 가끔 '테스트 요청 보내기' 하면 500이 리턴되는데, 왜 그러는지는 저도 모르겠습니다... 한 번 더 '테스트 요청 보내기'를 눌러 요청을 보내면 잘 되긴 합니다.

한편, config.ts 파일이 Firebase 서버와 연동하는 역할을 합니다. 따라서 이 파일이 제대로 import되지 않으면 로그인부터 되지 않습니다.

---

# DB

생성된 이미지는 Storage 상에서 `users/{uid}/images/` 에 저장됩니다. 일단 이미지 이름은 uuid4로 만든 값을 사용합니다.

또한 제일 최근에 생성된 이미지의 경로는 Firestore DB의 `users/{uid}`의 `imagePath` 필드에 저장됩니다. 위의 google-popup.ts 파일에서는 먼저 이 필드에 접근하여 이미지의 경로를 획득, 이어서 Storage에 접근해 이미지를 가져오도록 하였습니다.

만약 더 좋은 아이디어가 있다면 알려주세요.
