import React, { useEffect, useState } from 'react';
import { ImageGridContainer, ImageContainer, Image, GoButton, InvisibleButton } from './components';
import styled from 'styled-components';
import { PromptInput } from './PromptInput';
import { GetAspectRatio, isPortrait } from '../_helpers';
import { IImageData } from '../_helpers/SubmitPrompt';
// images: string[], ratio: { width: number; height: number; }, onSelectImage: (image: string) => void

const GridWrapper = styled.div`
  display: grid;
  grid-template-columns: 1fr;
  grid-template-rows: 1fr auto;
  grid-gap: 1em;

  margin: 1em;
  max-height: 100vh;
  overflow: auto;
  width: 100%;
`;


export interface IImageDisplayProps {
  images: IImageData[];
  aspectRatio: string;
  onSelectImage: (image: IImageData) => void;
}

export function ImageDisplay({
  aspectRatio,
  images,
  onSelectImage,
}: IImageDisplayProps) {

  const [ratio] = useState(GetAspectRatio(aspectRatio));

  const [selectedImageIndex, setSelectedImageIndex] = useState<number | null>(null);

  useEffect(() => {
    if (selectedImageIndex) {
      onSelectImage(images[selectedImageIndex]);
    }
  }, [selectedImageIndex]);

  useEffect(() => {
    setSelectedImageIndex(null);
  }, [images]);

  const images_to_show = isPortrait ? 3 : 5;
  return <GridWrapper>
    <ImageGridContainer className="fadeImageIn" style={{
    // base off images length
    // gridTemplateColumns: `repeat(${Math.ceil(Math.sqrt(images.length))}, 1fr)`,
    gridTemplateColumns: `repeat(${images.length > images_to_show ? images_to_show : images.length}, 1fr)`,
  }}>
    {images.slice(0, images_to_show).map(({image: imageBytes64}, i) => {
      return <ImageContainer key={i} onClick={() => setSelectedImageIndex(i)} aspectRatio={`${ratio.width}/${ratio.height}`}>
        <InvisibleButton onFocus  ={() => {console.log("Hovering", i)}}><Image src={`data:image/png;base64,${imageBytes64}`} /></InvisibleButton>
      </ImageContainer>;
    })}
  </ImageGridContainer>
  <PromptInput style={{
    fontSize: '1.5em',
  }} aspectRatio={aspectRatio} hideAspectRatio={true} onPromptSubmit={() => {}} onAspectRatioChanged={() => {}} processing={false} />
  </GridWrapper>;
}
