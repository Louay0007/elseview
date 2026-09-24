import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import StudyPreview from './StudyPreview.jsx';
import CollectionRunner from './CollectionRunner.jsx';
import EvaluationRunner from './EvaluationRunner.jsx';
import LongitudinalRunner from './LongitudinalRunner.jsx';

const previewToken = new URLSearchParams(location.hash.slice(1)).get('preview');
const sessionParams = new URLSearchParams(location.hash.slice(1));
const sessionId = sessionParams.get('session');
const sessionToken = sessionParams.get('session_token');
if (previewToken || sessionToken) history.replaceState(null, '', location.pathname + location.search);

function App() {
  const [status, setStatus] = useState('Checking backend…');
  const [evaluation, setEvaluation] = useState(null);
  const [longitudinal, setLongitudinal] = useState(null);
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
  if (evaluation) return <><button onClick={() => setEvaluation(null)}>Close review and clear credentials</button><EvaluationRunner {...evaluation} /></>;
  if (longitudinal) return <><button onClick={() => setLongitudinal(null)}>Close schedule and clear credentials</button><LongitudinalRunner {...longitudinal} /></>;
  return <main style={{ maxWidth: 720, margin: '4rem auto', padding: '1rem', fontFamily: 'system-ui' }}>
    <h1>Elseview</h1>
    <p>See what you’re missing.</p>
    <p>Development diagnostic</p>
    <p role="status" aria-live="polite">{status}</p>
    <p>Identity, workspaces, privacy controls, private assets and versioned study APIs are available. Open an authorized preview link to try the core research methods.</p>
    <p>Authorized preview links and existing consented participant sessions can open research methods. This page is a development diagnostic, not the researcher dashboard. Runtime availability depends on backend readiness and published method gates.</p>
    <section><h2>Open assigned human review</h2><p>Use your authorized workspace assignment and access token. Credentials stay in memory and are cleared on closing or refreshing. Do not paste tokens into URLs.</p><form onSubmit={event => { event.preventDefault(); const data = new FormData(event.currentTarget); setEvaluation({ workspaceId: data.get('workspace'), assignmentId: data.get('assignment'), token: data.get('token') }); event.currentTarget.reset(); }}>
      <label>Workspace ID<input name="workspace" required autoComplete="off" /></label><label>Assignment ID<input name="assignment" required autoComplete="off" /></label><label>Access token<input name="token" type="password" required autoComplete="off" /></label><button>Open assignment</button>
    </form></section>
    <section><h2>Open participant schedule</h2><p>Use your authenticated participant account. Credentials stay in memory, not in URLs or storage.</p><form onSubmit={e => { e.preventDefault(); const values = new FormData(e.currentTarget); setLongitudinal({ workspaceId: values.get('workspace'), versionId: values.get('version'), token: values.get('token'), locale: values.get('locale') }); e.currentTarget.reset(); }}><label>Workspace ID<input required name="workspace" autoComplete="off" /></label><label>Published study version ID<input required name="version" autoComplete="off" /></label><label>Participant access token<input required name="token" type="password" autoComplete="off" /></label><label>Session language<input required name="locale" defaultValue="en" /></label><button>Open schedule</button></form></section>
  </main>;
}
createRoot(document.getElementById('root')).render(previewToken ? <StudyPreview token={previewToken} /> : sessionId && sessionToken ? <CollectionRunner sessionId={sessionId} token={sessionToken} locale={sessionParams.get('locale') || 'en'} /> : <App />);