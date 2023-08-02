import styled, { css } from 'styled-components';
import { CookieInput, CookieTextarea } from '../CookieInput';
import { isPortrait } from '../_helpers';

export const NoBoundaryCookieInput = styled(CookieInput)`
  border: none;
  outline: none;
  background: none;
  font-size: 1.5em;
  color: #fff;
  // style so that text is centered
  text-align: center;
  height: 20px;
  // animate border underlining when input is active
    border-bottom: 0px solid #0000000;
    transition: all 0.3s ease-in-out;
    &:focus, &:active {
        border-bottom: 5px solid #fff;
    }
`;
export const NoBoundaryCookieTextarea = styled(CookieTextarea)`
  border: none;
  outline: none;
  background: none;
  font-size: 1em;
  color: #fff;
  // style so that text is centered
  text-align: center;

  // disable resizing and make it look like a normal input
  resize: none;
  overflow: hidden;
  height: 2ch;

  min-width: min(100vw, 50ch);
  // keep the text at the bottom of the input
  vertical-align: bottom;
  padding: none;
  
  // animate border underlining when input is active
    border-bottom: 0px solid #0000000;
    transition: all 0.3s ease-in-out, height 0s ease-out;
    &:focus, &:active {
        border-bottom: 5px solid #fff;
    }

  &::placeholder {
    color: ${props => props.style.color || '#ccc'};
  }
`;
const DropdownContainer = styled.div`
  position: relative;
  display: inline-block;
  * {
    transition: all 0.1s ease-in-out;
    }
`;
export const AspectRatioDropdownContainer = styled(DropdownContainer)`
&::after {
    content: 'Aspect Ratio';
    position: absolute;
    top: 50%;
    right:50%;
    // dont wrap text
    white-space: nowrap;
    text-align: center;
    transform: translateY(calc(-50% - .5em)) translateX(calc(50%));
    color: #777;
    text-align: right;
}

`;
export const DropdownButton = styled.button`
    background-color: #00000000;
  color: #ccc;
  border: none;
  cursor: pointer;
  text-align: center;
  padding: 8px 0px;
  min-width: 120px;
    font-size: 1.5em;
    outline: none;
    margin: 1.5em 0 0em 0;
`;
export const DropdownList = styled.ul`
  position: absolute;
  top: calc(50% + 2em);
  left: 0;
  background: linear-gradient(-45deg, #1a1a1a, #212121, #292929, #303030);
  list-style: none;
  padding: 0;
  margin: 0;
  border: 1px solid #fff;
  min-width: 120px;
  z-index: 1;

    &:focus {
        outline: 2px;
    }
`;
export const DropdownItem = styled.li`
  padding: 8px 0px;
  cursor: pointer;

  .selected {
    background-color: #f0f0f0;
    color: #000;
  }

  &:hover, &:focus, &:active {
    background-color: #f0f0f0;
    color: #000;
  }
`;
export const ColumnFlexContainer = styled.div`
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  opacity: 1;

  p {
    margin: 0;
    font-size: 0.75em;
  }

  ${Array.from({ length: 10 }).map((_, index) => {
  const totalElements = 10;
  const animationDuration = 0.3; // Adjust the animation duration as desired
  const maxDelay = 1.5; // Maximum delay value for the initial elements
  const minDelay = 0; // Minimum delay value for the last few elements
  const delayIncrement = maxDelay / totalElements;
  const adjustedDelay = (index * animationDuration * 0.85);
  const delay = adjustedDelay; // Add the animation duration to the delay
  return css`
    &.fadeInputOut > *:nth-child(${index + 1}) {
      animation-delay: ${delay}s;
      animation-duration: ${animationDuration}s;
      animation-name: fadeFromTop;
      animation-fill-mode: forwards;
    }
  `;
})}
    
  @keyframes fadeFromTop {
    100% {
      opacity: 0;
      transform: translateY(-100%);
    }
    0% {
      opacity: 1;
      transform: translateY(0);
    }
  }
  
  
`;

const minSize = isPortrait ? '44vw' : '44vh';

export const ImageGridContainer = styled.div`
  display: grid;
  // either 1x1 or 2x2 and use aspect ratio to size images correctly
  grid-auto-rows: 1fr;
  grid-gap: 1em;
  justify-items: center;
  align-items: center;
  padding: 1em;
  margin: 0 auto;
  max-width: ${isPortrait ? '95vw' : '80vw'};
  &.fadeImageIn > * {
    opacity: 0;
  }

  ${Array.from({ length: 10 }).map((_, index) => {
  const totalElements = 10;
  const animationDuration = 0.5; // Adjust the animation duration as desired
  const maxDelay = 4.5; // Maximum delay value for the initial elements
  const minDelay = 0; // Minimum delay value for the last few elements
  const delayIncrement = maxDelay / totalElements;
  const adjustedDelay = (index * delayIncrement * 0.85);
  const delay = adjustedDelay; // Add the animation duration to the delay
  return css`
      &.fadeImageIn > *:nth-child(${index + 1}) {
        animation-delay: ${0}s;
        animation-duration: ${(animationDuration * index) + 0.5}s;
        animation-name: fadeImagesIn;
        animation-fill-mode: forwards;
      }
    &.fadeImageOut > *:nth-child(${index + 1}) {
      animation-delay: ${delay}s;
      animation-duration: ${animationDuration}s;
      animation-name: fadeImagesOut;
      animation-fill-mode: forwards;
    }
    `;
})}

  @keyframes fadeImagesIn {
    0% {
      opacity: 0;
      transform: translateY(-1em);
    }
    80% {
      transform: translateY(0);
    }
    100% {
      opacity: 1;
      
    }
  }
  @keyframes fadeImagesOut {
    100% {
      opacity: 0;
      transform: translateY(-1em);
    }
    0% {
      opacity: 1;
      transform: translateY(0);
    }
`;
interface ImageContainerProps {
  aspectRatio: string;
}
export const ImageContainer = styled.div<ImageContainerProps> `
  position: relative;
  overflow: hidden;
  border-radius: 0.5em;
  transition: all 0.3s ease-in-out, border 0.1s ease-out;
  max-width: ${minSize};
  max-height: ${minSize};
  aspect-ratio: ${(props) => props.aspectRatio};
  box-shadow: 0 0 0.5em #000000cc;
  border: 0.1em solid #00000000;

  &:hover {
    box-shadow: 0 0 1em #000000ff;
    border: 0.1em solid #ccddeeff;
    cursor: pointer;
  }

  &.selected {
    border: 0.2em solid #fff;
    
  }


`;
export const Image = styled.img`
  display: block;
  max-width: 100%;
  max-height: 100%;
  width: auto;
  height: auto;
  margin: auto;
  object-fit: contain;
`;
export const GoButton = styled.button`
    background-color: #00000000;
    color: #ccc;
    border: none;
    text-align: center;
    padding: 8px 0px;
    min-width: 120px;
    font-size: 1em;
    outline: none;
    margin: 0.5em 0;
    &:hover, &:focus{
        color: #fff;
        cursor: pointer;
    }
    // when pressed down make darker
    &:active {
        color: #777;
    }
    &:disabled {
        color: #777;
        cursor: not-allowed;
    }
    `;
export const LoadingText = styled.div`
    color: #ccc;
    font-size: 1.5rem;
    margin: 0.5em 0;
    text-align: center;

    &.fadeInputIn > * {
      animation: fadeInputIn 1s ease-in-out;
    }
    &.fadeInputOut > * {
      animation: fadeInputOut 1s ease-in-out;
    }
`;

export const InvisibleButton = styled.button`
    background-color: #00000000;
    border: none;
    text-align: center;
    padding: 0px;
    margin: 0px;
    `;