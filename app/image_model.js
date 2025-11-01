// import { getFunctions, httpsCallable } from 'firebase/functions';
// import { getStorage, ref, getDownloadURL } from 'firebase/storage';
// import { getFirestore, doc, getDoc } from 'firebase/firestore';

import { getFunctions, httpsCallable } from 'https://www.gstatic.com/firebasejs/12.5.0/firebase-functions.js';
import { getStorage, ref, getDownloadURL } from 'https://www.gstatic.com/firebasejs/12.5.0/firebase-storage.js';
import { getFirestore, doc, getDoc } from 'https://www.gstatic.com/firebasejs/12.5.0/firebase-firestore.js';

import { app, auth } from './login.js'

const functions = getFunctions(app);
const storage = getStorage(app);
const db = getFirestore(app);

const generateImageCallable = httpsCallable(functions, 'generate_image');
const generateTha4Callable = httpsCallable(functions, 'generate_tha4_model');

export async function callGenerateTha4ModelFunction() {
  const user = auth.currentUser;
  if (!user) {
    alert("User is not authenticated. Please log in first.");
    console.error("User is not authenticated. Please log in first.");
    return;
  }
  
  const imagePath = await getFieldFromUserDoc(user, "imagePath");
  if (imagePath) {
    try {
      const result = await generateTha4Callable(imagePath);
      alert("Function called successfully!");
      console.log("Function called successfully!");
      console.log("Server response:", result.data);
    } catch (error) {
      alert("ERROR: ", error);
      console.error("Error calling the function:", error);
    }
  } else {
    alert("couldn't find the imagePath");
    console.error("couldn't find the imagePath");
  }
}

export async function callGenerateImageFunction(prompt) {
  console.log(auth.currentUser);
  if (!auth.currentUser) {
    alert("User is not authenticated. Please log in first.");
    console.error("User is not authenticated. Please log in first.");
    return;
  }
  
  try {
    const result = await generateImageCallable(prompt);

    alert("Function called successfully!");
    console.log("Function called successfully!");
    console.log("Server response:", result.data);
  } catch (error) {
    alert("ERROR: ", error);
    console.error("Error calling the function:", error);
    
    if (error.code === 'unauthenticated') {
      console.log("Authentication failed. Please check your token or login state.");
    }
  }
}

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

export async function downloadUserImage() {
  const user = auth.currentUser;
  if (!user) {
    alert("User is not authenticated. Please log in first.");
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
      alert("Error retrieving image for download:", error);
      console.error("Error retrieving image for download:", error);
    }
  } else {
    console.error(`ERROR: cannot find the image: ${imagePath}`);
    return;
  }
}

export async function downloadModel() {
  const user = auth.currentUser;
  if (!user) {
    alert("User is not authenticated. Please log in first.");
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
      alert("Error while retrieving model for download: ", error);
      console.error("Error while retrieving model for download: ", error);
    }
  }
}
