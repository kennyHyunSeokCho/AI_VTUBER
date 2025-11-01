// https://github.com/firebase/quickstart-js/blob/master/auth/email-password.ts

// import { initializeApp } from 'firebase/app';
// import {
//   getAuth,
//   signOut,
//   createUserWithEmailAndPassword,
//   signInWithEmailAndPassword
// } from 'firebase/auth';
import { firebaseConfig } from './config.js';

import { initializeApp } from 'https://www.gstatic.com/firebasejs/12.5.0/firebase-app.js'
import {
  getAuth,
  signOut,
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  onAuthStateChanged
} from 'https://www.gstatic.com/firebasejs/12.5.0/firebase-auth.js';

export const app = initializeApp(firebaseConfig);
export const auth = getAuth();

const emailInput = document.getElementById('email');
const passwordInput = document.getElementById('password');

const signInButton = document.getElementById('loginBtn');
const loginInput = document.getElementById('loginInput');
const loggedInUserInfo = document.getElementById('loggedInUserInfo');
const signUpBtn = document.getElementById('signUpBtn');

/**
 * Handles the sign in button press.
 */
export function toggleSignIn() {
  if (auth.currentUser) {
    signOut(auth);
  } else {
    const email = emailInput.value;
    const password = passwordInput.value;
    if (email.length < 4) {
      alert('Please enter an email address.');
      return;
    }
    if (password.length < 4) {
      alert('Please enter a password.');
      return;
    }
    // Sign in with email and pass.
    signInWithEmailAndPassword(auth, email, password)
    .then(() => {
      alert("로그인 성공");
    })
    .catch(function (error) {
      // Handle Errors here.
      const errorCode = error.code;
      const errorMessage = error.message;
      if (errorCode === 'auth/wrong-password') {
        alert('Wrong password.');
      } else {
        alert(errorMessage);
      }
      console.log(error);
      signInButton.disabled = false;
    });
  }
  signInButton.disabled = true;
}

/**
 * Handles the sign up button press.
 */
export function handleSignUp() {
  const email = emailInput.value;
  const password = passwordInput.value;
  if (email.length < 4) {
    alert('Please enter an email address.');
    return;
  }
  if (password.length < 4) {
    alert('Please enter a password.');
    return;
  }
  // Create user with email and pass.
  createUserWithEmailAndPassword(auth, email, password)
  .then(() => {
    alert("등록이 완료되었습니다.");
  })
  .catch(function (error) {
    // Handle Errors here.
    const errorCode = error.code;
    const errorMessage = error.message;
    if (errorCode == 'auth/weak-password') {
      alert('The password is too weak.');
    } else {
      alert(errorMessage);
    }
    console.log(error);
  });
}

// Listening for auth state changes.
onAuthStateChanged(auth, function (user) {
  if (user) {
    // User is signed in.
    loginInput.style.display = 'none';
    loggedInUserInfo.style.display = 'block';
    loggedInUserInfo.textContent = `환영합니다. ${user.email}`;
    signUpBtn.style.display = 'none';
    signInButton.textContent = 'Sign out';
  } else {
    // User is signed out.
    loginInput.style.display = 'block';
    loggedInUserInfo.style.display = 'none';
    loggedInUserInfo.textContent = '';
    signUpBtn.style.display = 'block';
    signInButton.textContent = 'Sign in';
  }
  signInButton.disabled = false;
});
