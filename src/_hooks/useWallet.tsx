import React, { createContext, useContext, useEffect, useState } from 'react';
import { BrowserProvider, ethers } from 'ethers';

interface CustomWindow extends Window {
    ethereum?: any; // Use a more specific type if available, such as `Window['ethereum']`
}

declare let window: CustomWindow;

interface Wallet {
    signIn: () => Promise<string>;
    signMessage: (message: string, _address: string) => Promise<string>;
    address: string | null;
    noMetamask: boolean;
}

const WalletContext = createContext<Wallet | null>(null as unknown as Wallet);

const useWallet = (): Wallet => {
    const wallet = useContext(WalletContext);
    if (!wallet) {
        throw new Error('useWallet must be used within a WalletProvider');
    }
    return wallet;
};
interface WalletProviderProps {
    children: React.ReactNode;
}

const WalletProvider: React.FC<WalletProviderProps> = ({ children }) => {
    const [address, setAddress] = useState<string | null>(null);
    const [noMetamask, setNoMetamask] = useState<boolean>(false);
    const [provider, setProvider] = useState<BrowserProvider | null>(window.ethereum ? new ethers.BrowserProvider(window.ethereum) : null);

    const signInConnectWallet = async () => {
        if (provider) {
            try {
                // Request access to the user's accounts
                let account = await provider.send("eth_requestAccounts", []).then((accounts: string[]) => {
                    const address = ethers.getAddress(accounts[0]);
                    setAddress(address);
                    console.log(accounts);
                    return address
                });
                console.log("Signed in successfully")
                return account;
            } catch (error) {
                console.error('Failed to connect to wallet:', error);
                throw "Failed to connect to wallet"
            }
        } else {
            console.warn('No wallet provider found');
            setNoMetamask(true);
            throw "No wallet provider found"
        }
    };

    const signMessage = async (message: string, _address: string) => {
        if (provider) {
            try {
                // Request access to the user's accounts
                console.log(_address, "address")
                let signature = await provider.send("personal_sign", [_address, message]);
                console.log("Signed message successfully")
                return signature;
            } catch (error) {
                console.error('Failed to sign message:', error);
                throw "Failed to sign message"
            }
        } else {
            console.warn('No wallet provider found');
            setNoMetamask(true);
            throw "No wallet provider found"
        }
    };

    const wallet: Wallet = {
        signIn: signInConnectWallet,
        signMessage,
        address,
        noMetamask
    };

    return (
        <WalletContext.Provider value={wallet}>
            {children}
        </WalletContext.Provider>
    );
};

export { WalletProvider, useWallet };
