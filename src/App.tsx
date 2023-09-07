import React from 'react';
import logo from './logo.svg';
import './App.scss';
import ImageGenerator from './ImageGenerator/index';
// router
import { BrowserRouter as Router, Route, Link, Routes } from 'react-router-dom';

import styled from 'styled-components';

const Container = styled.div`
// span the whole of the screen
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
`;
// react component that when loaded, redirects to given url
const Redirect = () => {
  window.location.href = 'https://1eetm7h7dmz.typeform.com/to/ZVXLaZPK';
  return null;
}

function BaseApp() {
  return (
    <div className="App">
      <Container>
      <ImageGenerator />
      </Container>
    </div>
  );
}

function App() {
  return (
    // <div className="App">
    //   <Container>
    //   <ImageGenerator />
    //   </Container>
    // </div>
    <Router>
      <Routes>
        {/* redirect /apply to https://1eetm7h7dmz.typeform.com/to/ZVXLaZPK */}
        <Route path="/apply" Component={Redirect} />
        {/* base url / loads container / image generator */}
        <Route path="/" Component={BaseApp} />
      </Routes>
    </Router>
            
  );
}

export default App;
