import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';

function App() {
  const [status, setStatus] = useState('Checking backend…');
  useEffect(() => {
    const controller = new AbortController();
    fetch('/api/v1/health/ready', { signal: controller.signal })
      .then(async response => {
        await response.json();
        setStatus(response.ok ? 'Backend ready' : 'Backend not ready — run the documented migration.');
      })
      .catch(error => { if (error.name !== 'AbortError') setStatus('Backend unavailable'); });
    return () => controller.abort();
  }, []);
  return <main style={{ maxWidth: 720, margin: '4rem auto', padding: '1rem', fontFamily: 'system-ui' }}>
    <h1>Elseview</h1>
    <p>See what you’re missing.</p>
    <p>P01 development foundation</p>
    <p role="status" aria-live="polite">{status}</p>
    <p>Research, authentication and AI features are not enabled yet. No cloud calls are made.</p>
  </main>;
}
createRoot(document.getElementById('root')).render(<App />);