import React, { useEffect, useRef, useState } from 'react';
import Cookies from 'js-cookie';
import { AspectRatioDropdownContainer, DropdownButton, DropdownList, DropdownItem } from './components';
import { Option } from '.';

interface AspectRatioDropdownProps {
  options: Option[];
  onSelect: (option: Option) => void;
  close: React.MutableRefObject<() => void>;
  cookieName: string;
}
export const AspectRatioDropdown: React.FC<AspectRatioDropdownProps> = ({ options, onSelect, close, cookieName }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [lastOpened, setLastOpened] = useState<number>(0);
  const [selectedOption, setSelectedOption] = useState<Option | null>(null);
  const [optionIndex, setOptionIndex] = useState<number>(0);
  const firstOptionref = useRef<HTMLLIElement>(null);

  useEffect(() => {
    const savedValue = Cookies.get(cookieName);
    const value = options.find((option) => option.value === savedValue);
    console.log("use effect", value, savedValue, cookieName);
    if (value) {
      setSelectedOption(value);
    } else {
      setSelectedOption(options[0]);
    }
  }, [cookieName]);


  const toggleDropdown = () => {
    if (Date.now() - lastOpened < 350) {
      return;
    }
    console.log("toggle dropdown", lastOpened);
    setIsOpen(!isOpen);
    setLastOpened(Date.now());
  };

  const handleSelect = (option: Option) => {
    setSelectedOption(option);
    onSelect(option);
    console.log("handle select");
    setIsOpen(false);
    setLastOpened(Date.now());
  };

  useEffect(() => {
    if (selectedOption !== null) {
      onSelect(selectedOption);
      Cookies.set(cookieName, selectedOption.value);
    }
  }, [selectedOption]);

  close.current = () => {
    setIsOpen(false);
    setLastOpened(Date.now());
    console.log("close current");
  };

  const HandleArrowSelect = (key: React.KeyboardEvent<HTMLButtonElement>) => {
    if (key.keyCode === 40) {
      // down arrow
      // itterate through next option
      if (optionIndex < options.length - 1) {
        setOptionIndex(optionIndex + 1);
        setSelectedOption(options[optionIndex + 1]);
      } else {
        setOptionIndex(0);
        setSelectedOption(options[0]);
      }
    } else if (key.keyCode === 38) {
      // up arrow
      // itterate through previous option
      if (optionIndex > 0) {
        setOptionIndex(optionIndex - 1);
        setSelectedOption(options[optionIndex - 1]);
      } else {
        setOptionIndex(options.length - 1);
        setSelectedOption(options[options.length - 1]);
      }
    }
  };

  return (
    <AspectRatioDropdownContainer>
      <DropdownButton onClick={toggleDropdown} onFocus={toggleDropdown} onKeyDown={HandleArrowSelect} id="aspect-ratio">
        {selectedOption ? selectedOption.label : '1:1'}
      </DropdownButton>
      {isOpen && (
        <>
          {/* create div which spans full screen and when click closes menu */}
          <div style={{
            position: 'fixed',
            top: 0,
            left: 0,
            width: '100vw',
            height: '100vh'
          }} onClick={() => {
            setIsOpen(false);
            setLastOpened(Date.now());
            console.log("close current");
          }}></div>
          <DropdownList>
            {options.map((option, i) => (
              <DropdownItem key={option.value} style={i == optionIndex ? {
                backgroundColor: '#f0f0f0',
                color: '#000'
              } : {}} ref={i == 0 ? firstOptionref : null} onClick={() => handleSelect(option)} onKeyDown={key => {
                // if enter key is pressed
                if (key.keyCode === 13) {
                  handleSelect(option);
                  setIsOpen(false);
                }
              }}>
                {option.label}
              </DropdownItem>
            ))}
          </DropdownList>
        </>
      )}
    </AspectRatioDropdownContainer>
  );
};
export const aspectRatioOptions: Option[] = [
  { label: '1:1', value: '1:1' },
  { label: '3:4', value: '3:4' },
  { label: '4:3', value: '4:3' },
  { label: '16:9', value: '16:9' },
  { label: '9:16', value: '9:16' },
];
