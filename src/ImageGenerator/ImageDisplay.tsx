import React, { useEffect, useState } from 'react';
import { ImageGridContainer, ImageContainer, Image } from './components';
// images: string[], ratio: { width: number; height: number; }, onSelectImage: (image: string) => void
export interface IImageDisplayProps {
  images: string[];
  ratio: { width: number; height: number; };
  onSelectImage: (image: string) => void;
}

export function ImageDisplay({
  images,
  ratio,
  onSelectImage,
}: IImageDisplayProps) {

  const [selectedImageIndex, setSelectedImageIndex] = useState<number | null>(null);

  useEffect(() => {
    if (selectedImageIndex) {
      onSelectImage(images[selectedImageIndex]);
    }
  }, [selectedImageIndex]);

  useEffect(() => {
    setSelectedImageIndex(null);
  }, [images]);

  return <ImageGridContainer className="fadeImageIn" style={{
    // base off images length
    gridTemplateColumns: `repeat(${Math.ceil(Math.sqrt(images.length))}, 1fr)`,
  }}>
    {images.map((imageBytes64, i) => {
      return <ImageContainer key={i} onClick={() => setSelectedImageIndex(i)} aspectRatio={`${ratio.width}/${ratio.height}`}>
        <Image src={`data:image/png;base64,${imageBytes64}`} />
      </ImageContainer>;
    })}
  </ImageGridContainer>;
}
