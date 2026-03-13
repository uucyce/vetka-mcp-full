import React from 'react';
import ReactDOM from 'react-dom/client';
import CutStandalone from '../src/CutStandalone';
import '../src/styles/voice.css';
import '../src/styles/tokens.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <CutStandalone />
  </React.StrictMode>
);
