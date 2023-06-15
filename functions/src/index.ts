/**
 * Import function triggers from their respective submodules:
 *
 * import {onCall} from "firebase-functions/v2/https";
 * import {onDocumentWritten} from "firebase-functions/v2/firestore";
 *
 * See a full list of supported triggers at https://firebase.google.com/docs/functions
 */

import {onCall} from "firebase-functions/v2/https";
// import * as logger from "firebase-functions/logger";
// import firestore
import * as admin from "firebase-admin";
import * as ethers from "ethers";

admin.initializeApp();

// Start writing functions
// https://firebase.google.com/docs/functions/typescript

// export const helloWorld = onRequest((request, response) => {
//   logger.info("Hello logs!", {structuredData: true});
//   response.send("Hello from Firebase!");
// });

// callable function to generate one time code to sign in
export const getOneTimeCode = onCall(async (request) => {
    // call firestore to see if user code exists
    const address = ethers.getAddress(request.data.address);
    const uid = request.auth?.uid;
    if (!uid) {
        throw new Error("Not signed in");
    }
    const code = await admin.firestore().collection("codes").doc(uid).get();
    if (code.exists) {
        // check time on code is within 5m
        const data = code.data();
        if(!data) throw new Error("No data found");
        const time = data.time;
        const now = Date.now();
        if (now - time < 300000) {
            return {code: data.code}
        } else {
            // replace code
            const newCode = GenerateNewCode();
            await admin.firestore().collection("codes").doc(uid).set({
                code: newCode,
                time: Date.now(),
                uid: uid,
                address: address
            });
            return {code: newCode};
        }
    } else {
        // create code
        const newCode = GenerateNewCode();
        await admin.firestore().collection("codes").doc(uid).set({
            code: newCode,
            time: Date.now(),
            uid: uid,
            address: address
        });
        return {code: newCode};
    }
});

export const decodeOneTimeCode = onCall(async (request) => {
    const signedMessage = request.data.signedMessage;
    const originalMessage = request.data.originalMessage;
    const address = ethers.getAddress(request.data.address);
    const uid = request.auth?.uid;

    if (!uid) {
        throw new Error("Not signed in");
    }

    // get code from firestore
    const code = await admin.firestore().collection("codes").doc(uid).get();
    if (!code.exists) {
        throw new Error("No code found")
    }

    const code_address = code.data()?.address;
    if (code_address !== address) {
        throw new Error("Invalid address")
    }

    const seperatedMessage = originalMessage.split(" ");
    // check that address is the same in firestore as originalMessage
    const ogAddress = seperatedMessage[0];
    if (ogAddress !== address) {
        console.log(ogAddress, address, "these aren't the same", ogAddress == address);
        throw new Error("Invalid address")
    }

    const ogCode = seperatedMessage[seperatedMessage.length - 1];

    // check time on code is within 5m
    const data = code.data();
    if(!data) throw new Error("No data found");

    if(String(ogCode) != String(data.code)) {
        console.log(ogCode, data.code, "these aren't the same", ogCode == data.code)
        throw new Error("Invalid code")
    }
    
    const time = data.time;
    const now = Date.now();
    if (now - time > 300000) {
        throw new Error("Code expired")
    }

    const recoveredAddress = ethers.verifyMessage(originalMessage, signedMessage)
    if (recoveredAddress !== address) {
        throw new Error("Invalid signature")
    }

    // delete code
    await admin.firestore().collection("codes").doc(uid).delete();

    // get token balance from ethereum
    return GetUserBalanceAndUpdateClaims(address, uid, true).then((result) => {
        if(result.error) {
            throw new Error(result.error)
        }
        return result;
    });
});

// callable function to update token balance and generate token
export const updateTokenBalance = onCall(async (request) => {
    const caller = request.auth;
    if (!caller) {
        throw new Error("Not signed in");
    }
    const uid = caller.uid;

    // get address from firestore
    const address = await admin.firestore().collection("users").doc(uid).get().then((doc) => {
        if (!doc.exists) {
            throw new Error("No address found");
        }
        const data = doc.data();
        if(!data) throw new Error("No data found");
        return data.address;
    }).catch((error) => {
        throw new Error(error.message);
    });

    // get token balance from ethereum
    return GetUserBalanceAndUpdateClaims(address, uid, false).then((response) => {
        if(response.error) {
            throw new Error(response.error);
        }
        return response
    });
});

export const generateImages = onCall(async (request) => {

    const prompt = request.data.prompt;
    const negativePrompt = request.data.negativePrompt;
    const image = request.data.image;
    const height = request.data.height;
    const width = request.data.width;
    const strength = request.data.strength;
    
    const body = {
        text: prompt,
        image: image || '',
        height: height,
        width: width,
        timeout: 12,
        num_images_per_prompt: 1,
        num_inference_steps: 30,
        guidance_scale: 7.5,
        strength: strength || 0.75,
        negative_prompt: negativePrompt
    };

    return fetch('http://0.0.0.0:8093/TextToImage/Forward', {
      method: 'POST',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(body)
    })
      .then(response => response.json());

});


function GenerateNewCode() {
    return Math.floor(Math.random() * 1000000) + 1000000;
}

async function GetUserBalanceAndUpdateClaims(address: string, uid: string, isSignIn: boolean): Promise<{ message?: string, token?: string, error?: string }> {
    const provider = new ethers.JsonRpcProvider("https://eth.llamarpc.com");
    // get balance from contract address
    const contractAddress = "0x77E06c9eCCf2E797fd462A92B6D7642EF85b0A44";
    const contract = new ethers.Contract(contractAddress, ["function balanceOf(address) view returns (uint256)"], provider);
    const balance = await contract.balanceOf(address).catch((error) => {
        console.error(error);
        return { error: "RPC error" };
    });

    // convert balance to number
    const balanceNumber = ethers.formatUnits(balance, 9);

    const currentClaims = await admin.auth().getUser(uid).then((userRecord) => {
        return userRecord.customClaims || {};
    }).catch((error) => {
        console.error(error);
        return { error: "User not found" };
    });
    if(!currentClaims) return { error: "User not found" };

    // update user auth record
    return admin.auth().setCustomUserClaims(uid, {
        ...currentClaims,
        address: address,
        lastUpdated: Date.now(),
        balance: balanceNumber
    })
        .then(async () => {
            // The new custom claims will propagate to the user's ID token the
            // next time a new one is issued.
            // issue token
            // update firestore
            await admin.firestore().collection("users").doc(uid).set({
                address: address,
                lastUpdated: Date.now(),
                balance: balanceNumber
            }, { merge: true }).catch((error) => {
                console.error(error);
                return { error: "Firestore error" };
            })

            return { message: "Success", token: await admin.auth().createCustomToken(uid) }
        })
        .catch((error) => {
            return { error: error.message }
        });
}

