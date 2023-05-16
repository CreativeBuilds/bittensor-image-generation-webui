import React, { MutableRefObject, useEffect, useRef, useState } from 'react';
import './AnimatedInput.scss'; // Import the CSS file for styling
import { ColumnFlexContainer, NoBoundaryTextarea, GoButton, LoadingText, ImageGridContainer, ImageContainer, Image } from './components';
import { AspectRatioDropdown, aspectRatioOptions } from './AspectRatioDropdown';

export interface Option {
  label: string;
  value: string;
}

const App: React.FC = () => {
  const [aspectRatio, setAspectRatio] = useState<string>('1:1');

  const handleAspectRatioSelect = (selectedOption: Option) => {
    console.log('Selected aspect ratio:', selectedOption.value);
    // Perform any necessary actions with the selected aspect ratio
    setAspectRatio(selectedOption.value);
  };

  const [prompt, setPrompt] = useState<string>('');
  const [negativePrompt, setNegativePrompt] = useState<string>('');
  const [processing, setProcessing] = useState<boolean>(false);
  const [showImages, setShowImages] = useState<boolean>(false);
  const [showPrompt, setShowPrompt] = useState<boolean>(true);
  
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const negativeInputRef = useRef<HTMLTextAreaElement>(null);
  const dropdownButtonRef = useRef<HTMLButtonElement>(null);
  const closeDropdown = useRef<() => void>(() => {});
  
  const imagesRef = useRef<string[]>([]);
  const [lastUpdateImages, setLastUpdateImages] = useState<number>(0);
  const [selectedImage, setSelectedImage] = useState<string>('');

  // ref for timeout
  const timeoutRef = useRef<number>(0);

  // auto select input on load
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  // when processing is true, set timeout to 1.5s
  useEffect(() => {
    if (processing && imagesRef.current.length > 0) {
      console.log("Setting processing to false")
      setProcessing(false);
      timeoutRef.current = window.setTimeout(() => {
        console.log("Setting show images to true")
        setShowImages(true);
      }, 1500);
    }
  }, [imagesRef.current, processing]);

  function GetAspectRatio(ratio: string) {
    const aspectRatioArr = ratio.split(':').map(Number);
    const minWidthHeight = 512;
  
    let width = minWidthHeight;
    let height = minWidthHeight;
  
    if (aspectRatioArr.length === 2) {
      const aspectRatioWidth = aspectRatioArr[0];
      const aspectRatioHeight = aspectRatioArr[1];
  
      if (aspectRatioWidth > aspectRatioHeight) {
        // Increase width while maintaining aspect ratio
        width = Math.max(minWidthHeight, Math.ceil((aspectRatioWidth / aspectRatioHeight) * minWidthHeight));
        height = Math.ceil((width / aspectRatioWidth) * aspectRatioHeight);
      } else if (aspectRatioHeight > aspectRatioWidth) {
        // Increase height while maintaining aspect ratio
        height = Math.max(minWidthHeight, Math.ceil((aspectRatioHeight / aspectRatioWidth) * minWidthHeight));
        width = Math.ceil((height / aspectRatioHeight) * aspectRatioWidth);
      }
    }
  
    // Ensure the width and height are divisible by 8
    width = Math.ceil(width / 8) * 8;
    height = Math.ceil(height / 8) * 8;
  
    return { width, height };
  }


  const SubmitPrompt = () => {
    setProcessing(true);
    console.log("Set processing to true");

    setTimeout(() => {
      console.log("Setting show prompt to false")
      setShowPrompt(false);
    }, 1000);

    const {width, height} = GetAspectRatio(aspectRatio);

    // 0.0.0.0:8091/api/prompt
    fetch('http://0.0.0.0:8093/TextToImage/Forward', {
    method: 'POST',
    headers: {
      'Accept': 'application/json',
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      text: prompt,
      image: '',
      height: height,
      width: width,
      timeout: 12,
      num_images_per_prompt: 1,
      num_inference_steps: 30,
      guidance_scale: 7.5,
      negative_prompt: negativePrompt
    })
  })
    .then(response => response.json())
    .then(({data, error}) => {
      if(error) throw new Error(error);
      console.log(data); // Handle the response data
      imagesRef.current = data;
      Reload();
    })
    .catch(error => {
      console.error(error); // Handle any errors
    });
  }

  const images = imagesRef.current;
  console.log(images, showImages);

  function Reload() {
    console.log("Reload called")
    setLastUpdateImages(Date.now());

  }

  return (
    <>
      {!showImages && showPrompt ? (<ColumnFlexContainer className={processing ? 'fadeInputOut' : ''}>
        <NoBoundaryTextarea
            cookieName="prompt"
            className="input"
            placeholder="[your prompt]"
            value={prompt}
            onChange={(value) => setPrompt(value)}
            ref={inputRef}
            style={{
              height: Math.min(5, Math.floor(Math.abs((prompt.length - 1)) / 50)*1.1 + 1) + 'em',
            }}
          />
        <NoBoundaryTextarea
          cookieName="negative_prompt"
          className="negative input"
          placeholder="[negative prompt]"
          value={negativePrompt}
          onChange={(value) => setNegativePrompt(value)}
          onFocus={() => closeDropdown.current()}
          ref={negativeInputRef}
          style={{
              height: Math.min(5, Math.floor(Math.abs((negativePrompt.length - 1)) / 50)*1.1 + 1) + 'em',
              marginTop: '1em',
              color: '#ff9999',
              borderColor: '#ff9999'
          }}
        />
        <AspectRatioDropdown cookieName="aspect_ratio" options={aspectRatioOptions} onSelect={handleAspectRatioSelect} close={closeDropdown}/>
        <GoButton onFocus={() => closeDropdown.current()} onClick={() => {
            SubmitPrompt();
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
        </ColumnFlexContainer>) : null}
        {((!showImages && processing) || images.length > 0 && !showImages ) && !showPrompt ? (
          <ColumnFlexContainer className={ processing ? 'fadeInputIn' : 'fadeInputOut'}>
            {/* waiting for images */}
            <LoadingText>One moment...</LoadingText>
          </ColumnFlexContainer>
          ) : null}
        {showImages && images.length > 0 ? (
          <ImageGridContainer className="fadeImageIn" style={{
            // base off images length
            gridTemplateColumns: `repeat(${Math.ceil(Math.sqrt(images.length))}, 1fr)`,
          }}>
            {images.map((imageBytes64, i) => {
              const ratio = GetAspectRatio(aspectRatio);
              return <ImageContainer  key={i} onClick={() => setSelectedImage(imageBytes64)} aspectRatio={`${ratio.width}/${ratio.height}`}>
              <Image src={`data:image/png;base64,${imageBytes64}`} />
            </ImageContainer>
            })}
          </ImageGridContainer>
        ) : null}
    </>
  );
};

export default App;