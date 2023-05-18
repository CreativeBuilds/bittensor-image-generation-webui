import React, { useEffect, useRef, useState } from 'react';
import { ColumnFlexContainer, NoBoundaryCookieTextarea, GoButton } from './components';
import { AspectRatioDropdown, aspectRatioOptions } from './AspectRatioDropdown';
import { Option } from '.';
import { GetAspectRatio } from '../_helpers/GetAspectRatio';

interface IPromptInputProps {
  aspectRatio?: string;
  processing: boolean;
  onPromptSubmit: ({
    prompt,
    negativePrompt,
    ratio
  }: {
    prompt: string;
    negativePrompt: string;
    ratio: {
      width: number;
      height: number;
    };
  }) => void;
  onAspectRatioChanged: (aspectRatio: string) => void;
}

export function PromptInput({ aspectRatio: _ar, processing, onPromptSubmit, onAspectRatioChanged }: IPromptInputProps) {

  const [prompt, setPrompt] = useState<string>('');
  const [negativePrompt, setNegativePrompt] = useState<string>('');
  const [aspectRatio, setAspectRatio] = useState<string>(_ar || "1:1");
  
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const negativeInputRef = useRef<HTMLTextAreaElement>(null);

  const closeDropdown = useRef<() => void>(() => {});

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  function handleAspectRatioSelect(selectedOption: Option) {
    console.log('Selected aspect ratio:', selectedOption.value);
    // Perform any necessary actions with the selected aspect ratio
    setAspectRatio(selectedOption.value);
  }



  return <ColumnFlexContainer className={processing ? 'fadeInputOut' : ''}>
    <NoBoundaryCookieTextarea
      cookieName="prompt"
      className="input"
      placeholder="[your prompt]"
      value={prompt}
      onChange={(value) => setPrompt(value)}
      ref={inputRef}
      style={{
        height: Math.min(5, Math.floor(Math.abs((prompt.length - 1)) / 50) * 1.1 + 1) + 'em',
      }} />
    <NoBoundaryCookieTextarea
      cookieName="negative_prompt"
      className="negative input"
      placeholder="[negative prompt]"
      value={negativePrompt}
      onChange={(value) => setNegativePrompt(value)}
      onFocus={() => closeDropdown.current()}
      ref={negativeInputRef}
      style={{
        height: Math.min(5, Math.floor(Math.abs((negativePrompt.length - 1)) / 50) * 1.1 + 1) + 'em',
        marginTop: '1em',
        color: '#ff9999',
        borderColor: '#ff9999'
      }} />
    <AspectRatioDropdown cookieName="aspect_ratio" options={aspectRatioOptions} onSelect={handleAspectRatioSelect} close={closeDropdown} />
    <GoButton onFocus={() => closeDropdown.current()} onClick={() => {
      onPromptSubmit({
        prompt,
        negativePrompt,
        ratio: GetAspectRatio(aspectRatio)
      });
    }} onKeyDown={e => {
      // if tab key is pressed select first input
      if (e.keyCode === 9) {
        e.preventDefault();
        // if shift is also pressed, focus the dropdown instead
        if (e.shiftKey) {
          document.getElementById('aspect-ratio')?.focus();
        } else {
          inputRef.current?.focus();
        }
      }
    }}>[ generate ]</GoButton>
  </ColumnFlexContainer>;
}
