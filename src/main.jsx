import React from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';
import './web-styles.css';

// These imports are resolved at build time: the Pages bundle never boots the
// desktop Node API and the desktop bundle never boots the WASM-only interface.
const app = import.meta.env.MODE === 'web'
  ? import('./WebApp.jsx')
  : import('./App.jsx');

app.then(({ default: App }) => {
  createRoot(document.getElementById('root')).render(
    <React.StrictMode><App /></React.StrictMode>
  );
}).catch(error => {
  console.error('Falha ao iniciar AutoEditor Studio:', error);
  document.getElementById('root').textContent = 'Não foi possível iniciar o editor. Atualize a página.';
});
