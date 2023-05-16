import React, { useState, useEffect, ChangeEvent, FocusEvent, RefObject, CSSProperties } from 'react';
import Cookies from 'js-cookie';

interface CookieInputProps {
  cookieName: string;
  placeholder: string;
  value: string;
  onChange: (value: any) => void;
  className?: string;
  onFocus?: (event: FocusEvent<HTMLInputElement>) => void;
  ref?: RefObject<HTMLInputElement>;
  style?: CSSProperties;
}

const CookieInput: React.FC<CookieInputProps> = ({
  cookieName,
  placeholder,
  value,
  onChange,
  className,
  onFocus,
  ref,
  style,
}) => {
  useEffect(() => {
    const savedValue = Cookies.get(cookieName);
    if (savedValue) {
      onChange(savedValue);
    }
  }, [cookieName, onChange]);

  const handleChange = (event: ChangeEvent<HTMLInputElement>) => {
    console.log('CookieInput handleChange', event.target.value, event);
    const newValue = event.target.value;
    onChange(newValue);
    Cookies.set(cookieName, newValue, { expires: 365 }); // Cookie expires in 1 year
  };

  return (
    <input
      type="text"
      className={className}
      placeholder={placeholder}
      value={value}
      onFocus={onFocus}
      ref={ref}
      style={style}
      onChange={handleChange}
    />
  );
};

interface CookieTextareaProps {
  cookieName: string;
  placeholder: string;
  value: string;
  onChange: (value: string) => void;
  className?: string;
  onFocus?: (event: FocusEvent<HTMLTextAreaElement>) => void;
  ref?: RefObject<HTMLTextAreaElement>;
  style?: CSSProperties;
}

const CookieTextarea: React.FC<CookieTextareaProps> = ({
  cookieName,
  placeholder,
  value,
  onChange,
  className,
  onFocus,
  ref,
  style,
}) => {
  useEffect(() => {
    const savedValue = Cookies.get(cookieName);
    if (savedValue) {
      onChange(savedValue);
    }
  }, [cookieName, onChange]);

  const handleChange = (event: ChangeEvent<HTMLTextAreaElement>) => {
    const newValue = event.target.value;
    onChange(newValue);
    Cookies.set(cookieName, newValue, { expires: 365 }); // Cookie expires in 1 year
  };

  return (
    <textarea
      className={className}
      placeholder={placeholder}
      value={value}
      onFocus={onFocus}
      ref={ref}
      style={style}
      onChange={handleChange}
    />
  );
};


export {CookieInput, CookieTextarea};
