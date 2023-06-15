import React, { useEffect } from 'react';
import { auth, decodeOneTimeCode, getOneTimeCode } from './_helpers/firebaseConfig';
import { TwitterAuthProvider, signInWithCustomToken, signInWithPopup } from 'firebase/auth';
import styled from 'styled-components';
import { useWallet } from './_hooks/useWallet';

const CenterDiv = styled.div`
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  overflow: hidden;
  flex-direction: column;
  `;
const StylizedButton = styled.button`
  background-color: ${props => props.theme.colors.primary};
  color: ${props => props.theme.colors.text};
  border: none;
  border-radius: 5px;
  padding: 10px 20px;
  font-size: 1.2rem;
  font-weight: bold;
  transition: all 0.2s ease-in-out;
  &:hover {
    background-color: ${props => props.theme.colors.primary};
    cursor: pointer;
    box-shadow: 0px 0px 10px 0px ${props => props.theme.colors.primary};
  }
`;
const StylizedA = styled.a`
  background-color: ${props => props.theme.colors.primary || 'unset'};
  color: ${props => props.theme.colors.text};
  border: none;
  line-style: none;
  border: none;
  // unset color when hovering/active
  &:hover {
    color: ${props => props.theme.colors.text};
    font-weight: bold;
  }
  &:active {
    color: ${props => props.theme.colors.text};
    font-weight: bold;
  }
  &:visited {
    color: ${props => props.theme.colors.text};
  }
  `;

const REQUIRES_METAMASK = true;

export const RequireSignIn: React.FC<{ OnceSignedIn: React.FC; }> = ({ OnceSignedIn }) => {
  // get firebase auth state and store in variable
  const [user, setUser] = React.useState<any>(null);
  const [isAuthorized, setIsAuthorized] = React.useState<boolean>(false);
  const [showTwitterButton, setShowTwitterButton] = React.useState<boolean>(false);
  const [showMetamaskButton, setShowMetamaskButton] = React.useState<boolean>(false);
  const [metamaskOpen, setMetamaskOpen] = React.useState<boolean>(false);
  const [hasSetAddress, setHasSetAddress] = React.useState<boolean>(false);

  const { signIn, signMessage, address, noMetamask } = useWallet();

  // listen for auth state changes
  useEffect(() => {
    const unsubscribe = auth.onAuthStateChanged((user) => {
      if (user) {
        setUser(user);

        // check claims if user is authorized
        user.getIdTokenResult().then((idTokenResult) => {
          // TODO: instead of authorized, this should be if the user has provided a metamask address
          if (idTokenResult.claims.address) {
            setHasSetAddress(true);
            setShowMetamaskButton(false);
          } else {
            setShowMetamaskButton(true);
          }
        });
      } else {
        setUser(null);
      }
    });

    // unsubscribe to the listener when unmounting
    return () => unsubscribe();
  }, []);

  // after one second of loading, show the sign-in button
  useEffect(() => {
    setTimeout(() => {
      setShowTwitterButton(true);
    }, 1000);
  }, []);

  const IS_VALID_USER = REQUIRES_METAMASK ? user && hasSetAddress : user;

  return IS_VALID_USER ? <OnceSignedIn /> : (
    <CenterDiv className="App">

      {showTwitterButton && !user && (
        <>
          <h1 style={{
            marginBottom: '1.25em'
          }}>TAO Image Generator</h1>
          <StylizedButton onClick={twitterSignIn} theme={{
            colors: {
              primary: '#1DA1F2',
              text: '#ffffff'
            }
          }}>login with Twitter</StylizedButton>
        </>
      )}
      {user && showMetamaskButton && !hasSetAddress ? noMetamask ? (
        <>
          <h2 style={{
            marginBottom: '1.25em'
          }}>Step 2 - Install Metamask</h2>
          <p style={{
            color: '#ffffffcc'
          }}>You must have a web3 wallet installed like <StylizedA href="https://chrome.google.com/webstore/detail/metamask/ nkbihfbeogaeaoehlefnkodbefgpgknn" target="_blank" theme={{
            colors: {
              text: '#ffffff'
            }
          }}>MetaMask</StylizedA>.</p>
        </>

      ) : (
        <>
          <h2 style={{
            marginBottom: '1.25em'
          }}>Step 2 - Link Metamask</h2>
          <StylizedButton theme={{
            colors: {
              primary: '#E8831D',
              text: '#ffffff'
            }
          }} onClick={() => {
            // #TODO trigger function to create one time code to sign
            setMetamaskOpen(true);
            signIn().then((address) => {
              return getOneTimeCode({ address }).then((async (response) => {
                const code = response.data.code;
                const message = `${address} your one time code is: ${code}`;

                // request user to sign message with metamask
                let signedMessage = await signMessage(message, address);
                let verifyResponse = await decodeOneTimeCode({ signedMessage, originalMessage: message, address });
                if (verifyResponse.data.message) {
                  const token = verifyResponse.data.token;
                  // firebase sign in with token
                  return signInWithCustomToken(auth, token).then((userCredential) => {
                    console.log("Signed in with custom token!", userCredential);
                    window.location.reload();
                  });
                }
              }));
            }).finally(() => setMetamaskOpen(false));
          }}>Link Metamask</StylizedButton>
          <p style={{
            color: '#ffffffcc'
          }}>To prevent server overload, only <StylizedA href='https://dexscreener.com/ethereum/0x433a00819c771b33fa7223a5b3499b24fbcd1bbc' target='_blank' theme={{
            colors: {
              text: '#ffffff'
            }
          }}>$wTAO</StylizedA> holders are authorized to generate.</p>
        </>
      ) : null}
    </CenterDiv>
  );
};
// Twitter sign-in function
const twitterSignIn = () => {
  const provider = new TwitterAuthProvider();
  signInWithPopup(auth, provider)
    .then((result) => {
      // Handle successful sign-in here
      console.log('Signed in with Twitter');
      console.log(result.user);
    })
    .catch((error) => {
      // Handle error here
      console.error('Error signing in with Twitter:', error);
    });
};
