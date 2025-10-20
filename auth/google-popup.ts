import { connectFunctionsEmulator, getFunctions, httpsCallable } from 'firebase/functions';
import { initializeApp } from 'firebase/app';
import { getStorage, ref, getDownloadURL } from 'firebase/storage';
import { getFirestore, doc, getDoc } from 'firebase/firestore';
import {
  GoogleAuthProvider,
  User,
  connectAuthEmulator,
  getAuth,
  onAuthStateChanged,
  signInWithPopup,
  signOut,
} from 'firebase/auth';
import { firebaseConfig } from './config';

const app = initializeApp(firebaseConfig);
const auth = getAuth();
const functions = getFunctions(app);
const storage = getStorage(app);
const db = getFirestore(app);

const signInButton = document.getElementById(
  'quickstart-sign-in',
)! as HTMLButtonElement;
const oauthToken = document.getElementById(
  'quickstart-oauthtoken',
)! as HTMLDivElement;
const signInStatus = document.getElementById(
  'quickstart-sign-in-status',
)! as HTMLSpanElement;
const accountDetails = document.getElementById(
  'quickstart-account-details',
)! as HTMLDivElement;

const sendRequestButton = document.getElementById(
  'send-webui-request',
)! as HTMLButtonElement;

const downloadImageButton = document.getElementById(
  'download-test-image'
)! as HTMLButtonElement;

const requestTha4Button = document.getElementById(
  'request-tha4'
)! as HTMLButtonElement;

const prompt = {
  prompt: "1girl, blue eyes, long hair, brown hair, red hair, two side up, double bun, school uniform, pink jacket, long sleeves"
};

const generateImageCallable = httpsCallable(functions, 'generate_image');
const generateTha4Callable = httpsCallable(functions, 'generate_tha4_model');

/**
 * Function called when clicking the Login/Logout button.
 */
function toggleSignIn() {
  if (!auth.currentUser) {
    const provider = new GoogleAuthProvider();
    provider.addScope('https://www.googleapis.com/auth/contacts.readonly');
    signInWithPopup(auth, provider)
      .then(function (result) {
        if (!result) return;
        const credential = GoogleAuthProvider.credentialFromResult(result);
        // This gives you a Google Access Token. You can use it to access the Google API.
        const token = credential?.accessToken;
        // The signed-in user info.
        const user = result.user;
        oauthToken.textContent = token ?? '';
      })
      .catch(function (error) {
        // Handle Errors here.
        const errorCode = error.code;
        const errorMessage = error.message;
        // The email of the user's account used.
        const email = error.email;
        // The firebase.auth.AuthCredential type that was used.
        const credential = error.credential;
        if (errorCode === 'auth/account-exists-with-different-credential') {
          alert(
            'You have already signed up with a different auth provider for that email.',
          );
          // If you are using multiple auth providers on your app you should handle linking
          // the user's accounts here.
        } else {
          console.error(error);
        }
      });
  } else {
    signOut(auth);
  }
  signInButton.disabled = true;
}

// Listening for auth state changes.
onAuthStateChanged(auth, function (user) {
  if (user) {
    // User is signed in.
    const displayName = user.displayName;
    const email = user.email;
    const emailVerified = user.emailVerified;
    const photoURL = user.photoURL;
    const isAnonymous = user.isAnonymous;
    const uid = user.uid;
    const providerData = user.providerData;
    signInStatus.textContent = 'Signed in';
    signInButton.textContent = 'Sign out';
    accountDetails.textContent = JSON.stringify(user, null, '  ');
  } else {
    // User is signed out.
    signInStatus.textContent = 'Signed out';
    signInButton.textContent = 'Sign in with Google';
    accountDetails.textContent = 'null';
    oauthToken.textContent = 'null';
  }
  signInButton.disabled = false;
});

signInButton.addEventListener('click', toggleSignIn, false);

async function callGenerateTha4ModelFunction() {
  if (!auth.currentUser) {
    console.error("User is not authenticated. Please log in first.");
    return;
  }
  
  const imagePath: string = "users/C0hCtwAg70QnDVXpFVSKNjBTZR32/images/dd0212bd-5fa2-465f-a5d9-8760eada562d.png";

  try {
    const result = await generateTha4Callable(imagePath);
    console.log("Function called successfully!");
    console.log("Server response:", result.data);
  } catch (error: any) {
    console.error("Error calling the function:", error);
  }
}

requestTha4Button.addEventListener('click', callGenerateTha4ModelFunction, false);

async function callGenerateImageFunction() {
  console.log(auth.currentUser);
  if (!auth.currentUser) {
    console.error("User is not authenticated. Please log in first.");
    return;
  }
  
  try {
    const result = await generateImageCallable(prompt);

    console.log("Function called successfully!");
    console.log("Server response:", result.data);
  } catch (error: any) {
    console.error("Error calling the function:", error);
    
    if (error.code === 'unauthenticated') {
      console.log("Authentication failed. Please check your token or login state.");
    }
  }
}

sendRequestButton.addEventListener('click', callGenerateImageFunction, false);

async function getUserImagePath(user: User): Promise<string | null> {
  const userDocRef = doc(db, "users", user.uid);
  
  try {
    const userDocSnap = await getDoc(userDocRef);
    if (userDocSnap.exists()) {
      const userData = userDocSnap.data();
      const imagePath = userData.imagePath as string;
      console.log("Image Path: ", imagePath);
      return imagePath;
    } else {
      console.error("No such user document!");
      return null;
    }
  } catch (error) {
    console.error("Error getting document:", error);
    return null;
  }
}

async function downloadUserImage(): Promise<void> {
  const user = auth.currentUser;
  if (!user) {
    console.error("No user is signed in.");
    return;
  }

  const imagePath = await getUserImagePath(user);
  if (imagePath) {
    const imageRef = ref(storage, imagePath);
    const imageName = imagePath.split('/').pop();
    if (!imageName) {
      console.error("ERROR: imageName");
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
      console.error("Error retrieving image for download:", error);
    }
  } else {
    console.error("cannot find the image.");
    return;
  }
}

downloadImageButton.addEventListener('click', downloadUserImage, false);
