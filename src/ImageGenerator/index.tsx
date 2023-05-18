import React, { MutableRefObject, useEffect, useRef, useState } from 'react';
import './AnimatedInput.scss'; // Import the CSS file for styling
import { ColumnFlexContainer, LoadingText } from './components';
import { ImageDisplay } from './ImageDisplay';
import { PromptInput } from './PromptInput';
import { GetAspectRatio, SubmitPrompt } from '../_helpers';

export interface Option {
  label: string;
  value: string;
}

const App: React.FC = () => {
  
  const [processing, setProcessing] = useState<boolean>(false);
  const [showImages, setShowImages] = useState<boolean>(false);
  const [showPrompt, setShowPrompt] = useState<boolean>(true);
  const [aspectRatio, setAspectRatio] = useState<string>('1:1');
  
  
  const imagesRef = useRef<string[]>([]);
  const [lastUpdateImages, setLastUpdateImages] = useState<number>(0);

  // ref for timeout
  const timeoutRef = useRef<number>(0);

  useEffect(() => {
    if (processing && imagesRef.current.length > 0) {

      // Trigger fade out of "One moment" text
      setProcessing(false);
      timeoutRef.current = window.setTimeout(() => {
        setShowImages(true);
      }, 1500);

    }
  }, [imagesRef.current, processing]);

  
  function Reload() {
    console.log("Reload called")
    setLastUpdateImages(Date.now());
  }
  
  const images = imagesRef.current;

  const should_show_prompt_input = !showImages && showPrompt;
  const should_show_waiting = ((!showImages && processing) || images.length > 0 && !showImages) && !showPrompt;
  const should_show_images = showImages && images.length > 0;

  const onAspectRatioChanged = (aspectRatio: string) => {
    setAspectRatio(aspectRatio);
  }

  const onPromptSubmit = ({
    prompt,
    negativePrompt,
    ratio,
  }) => {
    TriggerPromptInputFadeOut(setProcessing, setShowPrompt);
    SubmitPrompt({ prompt, negativePrompt, ratio }, (data) => {
      imagesRef.current = data;
      Reload();
    })
  }

  return (
    <>
      {
        should_show_prompt_input ? (
          <PromptInput 
            aspectRatio={aspectRatio}
            processing={processing} 
            onPromptSubmit={onPromptSubmit} 
            onAspectRatioChanged={onAspectRatioChanged}
          />
        )
        : null}
      {
        should_show_waiting ? (
          <ColumnFlexContainer className={ processing ? 'fadeInputIn' : 'fadeInputOut'}>
            <LoadingText>One moment...</LoadingText>
          </ColumnFlexContainer>
        ) : null
      }
      {
        should_show_images ? (
          <ImageDisplay images={images} ratio={GetAspectRatio(aspectRatio)} onSelectImage={()=>{}}/>
        ) : null
      }
    </>
  );
};

export default App;

function TriggerPromptInputFadeOut(setProcessing: React.Dispatch<React.SetStateAction<boolean>>, setShowPrompt: React.Dispatch<React.SetStateAction<boolean>>) {
  setProcessing(true);

  setTimeout(() => {
    setShowPrompt(false);
  }, 1000);
}
