import React, { useEffect, useRef, useState } from 'react';
import { ColumnFlexContainer, NoBoundaryCookieTextarea, GoButton } from './components';
import { AspectRatioDropdown, aspectRatioOptions } from './AspectRatioDropdown';
import { Option } from '.';
import { GetAspectRatio } from '../_helpers/GetAspectRatio';
import { on } from 'events';

interface IPromptInputProps {
  aspectRatio?: string;
  hideAspectRatio?: boolean;
  processing: boolean;
  style?: React.CSSProperties;
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

export function PromptInput({ aspectRatio: _ar, hideAspectRatio: _har, processing, style, onPromptSubmit, onAspectRatioChanged }: IPromptInputProps) {

  const [prompt, setPrompt] = useState<string>('');
  const [negativePrompt, setNegativePrompt] = useState<string>('');
  const [aspectRatio, setAspectRatio] = useState<string>(_ar || "1:1");
  const [showMore, setShowMore] = useState<boolean>(false);

  
  useEffect(() => {
    setAspectRatio(_ar || "1:1");
    onAspectRatioChanged(_ar || "1:1");
  }, [_ar]);
  
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const negativeInputRef = useRef<HTMLTextAreaElement>(null);

  const closeDropdown = useRef<() => void>(() => {});

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  function handleAspectRatioSelect(selectedOption: Option) {
    setAspectRatio(selectedOption.value);
    onAspectRatioChanged(selectedOption.value);
  }

  return <ColumnFlexContainer className={processing ? 'fadeInputOut' : ''} style={style}>
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
    { 
      !_har ?
        <AspectRatioDropdown cookieName="aspect_ratio" options={aspectRatioOptions} onSelect={handleAspectRatioSelect} close={closeDropdown} />
      : null
    }
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
          if(!_har)
            document.getElementById('aspect-ratio')?.focus();
          else
            negativeInputRef.current?.focus();
        } else {
          inputRef.current?.focus();
        }
      }
    }}>[ generate ]</GoButton>
    {/* <br/>
    <GoButton onClick={
      () => setShowMore(!showMore)
    }>{showMore ? "[ hide ]" : "[ show more ]"}</GoButton>
    {showMore ? <>
      <p style={{marginBottom:"0.5em"}}><b>LoRAs</b><br/> {"add_detail detailed_eye"}</p>
    <p><b>prompt example usage</b><br/> {"<lora:add_detail:0.8> <lora:detailed_eye:1.0>"}</p>
    <br/>
    <p style={{marginBottom:"0.5em"}}><b>Inversions</b><br/> bad_prompt_version2 emb_params NG_DeepNegative_V1_T75 veryBadImageNegative_V1.3</p>
    <p><b>negative prompt example usage</b><br/> {"<bad_prompt_version2:0.8> <emb_params:0.5>"}</p></> : null} */}
    
  </ColumnFlexContainer>;
}
