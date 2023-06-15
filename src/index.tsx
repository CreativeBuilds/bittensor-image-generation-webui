import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.scss';
import App from './App';
import reportWebVitals from './reportWebVitals';
import { app } from './_helpers/firebaseConfig';
import { WalletProvider } from './_hooks/useWallet';
import { RequireSignIn } from './RequireSignIn';

// Import the functions you need from the SDKs you need
const firebaseApp = app;

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);

root.render(
  <React.StrictMode>
    <WalletProvider>
      <RequireSignIn OnceSignedIn={App} />
    </WalletProvider>
  </React.StrictMode>
);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals(console.log);


