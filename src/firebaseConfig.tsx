import { initializeApp } from "firebase/app";
import { getAnalytics } from "firebase/analytics";
import { getAuth } from "firebase/auth";
import { getFunctions, httpsCallable } from "firebase/functions";

// TODO: Add SDKs for Firebase products that you want to use
// https://firebase.google.com/docs/web/setup#available-libraries
// Your web app's Firebase configuration
// For Firebase JS SDK v7.20.0 and later, measurementId is optional
const firebaseConfig = {
  apiKey: "AIzaSyDKN3Ahr30QplpyCXC8cME07JfBIHIGduY",
  authDomain: "image-gen-webui.firebaseapp.com",
  projectId: "image-gen-webui",
  storageBucket: "image-gen-webui.appspot.com",
  messagingSenderId: "516202383101",
  appId: "1:516202383101:web:336d614cb49b65197ae094",
  measurementId: "G-033RPYKJ8J"
};
// Initialize Firebase
const app = initializeApp(firebaseConfig);
const analytics = getAnalytics(app);
const auth = getAuth(app);

// add to window object, logout()
// @ts-ignore
window.logout = () => {
  auth.signOut();
}
const functions = getFunctions(app);

const getOneTimeCode = httpsCallable<unknown, GetOneTimeCodeResponse>(functions, "getOneTimeCode")

interface GetOneTimeCodeResponse {
  code: number;
}

const decodeOneTimeCode = httpsCallable<unknown, DecodeOneTimeCodeResponse>(functions, "decodeOneTimeCode")

interface DecodeOneTimeCodeResponse {
  message?: "Success";
  error?: string;
  token?: string;
}


export {auth, app, analytics, functions, getOneTimeCode, GetOneTimeCodeResponse, decodeOneTimeCode, DecodeOneTimeCodeResponse};