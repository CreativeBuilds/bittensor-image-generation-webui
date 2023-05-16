import React from 'react';
import logo from './logo.svg';
import './App.scss';
import ImageGenerator from './ImageGenerator/index';

import styled from 'styled-components';

const Container = styled.div`
// span the whole of the screen
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
`;

function App() {
  return (
    <div className="App">
      <Container>
      <ImageGenerator />
      </Container>
    </div>
  );
}

export default App;
