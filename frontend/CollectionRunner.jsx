import React, { useEffect, useRef, useState } from 'react';
import { Question } from './StudyPreview.jsx';
import { ADVANCED_METHOD_TYPES } from './AdvancedMethods.jsx';

// Resume an already consented session. Credentials remain in memory, not local storage.
export default function CollectionRunner({ sessionId, token, locale = 'en' }) {
  const [state, setState] = useState(null), [busy, setBusy] = useState(false), [error, setError] = useState('');
  const sequence = useRef(-1), eventQueue = useRef(Promise.resolve()), pendingEvent = useRef(null), pendingAnswer = useRef(null);
  const runnable = [...ADVANCED_METHOD_TYPES, 'survey.single', 'survey.multi', 'survey.rating', 'survey.text', 'preference', 'prototype.task'];
  const base = `/api/v1/collection/sessions/${encodeURIComponent(sessionId)}`;
  async function request(path = '', options = {}) {
    const response = await fetch(base + path, { ...options, cache: 'no-store', headers: { 'Content-Type': 'application/json', 'X-Session-Token': token } });
    if (!response.ok) { const data = await response.json().catch(() => ({})); throw new Error(data.error?.message || `Collection request failed (${response.status}).`); }
    return response;
  }
  async function load() { const result = await (await request()).json(); sequence.current = result.last_sequence; setState(result); }
  useEffect(() => { load().catch(e => setError(e.message)); }, [sessionId, token]);
  function event(kind, metadata, elapsed_ms = 0) {
    const block_key = state.block.block_key;
    const run = async () => {
      const signature = JSON.stringify({ block_key, kind, metadata, elapsed_ms });
      if (pendingEvent.current && pendingEvent.current.signature !== signature) throw new Error('An earlier interaction has not been acknowledged. Retry that action or reload the session.');
      const body = pendingEvent.current?.body || { version_id: state.version_id, events: [{ block_key, event: { kind, metadata, elapsed_ms, sequence: sequence.current + 1, client_event_id: crypto.randomUUID() } }] };
      pendingEvent.current = { signature, body };
      const result = await (await request('/events', { method: 'POST', body: JSON.stringify(body) })).json();
      sequence.current = result.last_sequence; pendingEvent.current = null;
    };
    const task = eventQueue.current.then(run); eventQueue.current = task.catch(() => {}); return task;
  }
  async function answer(value) {
    setBusy(true); setError('');
    try {
      await eventQueue.current;
      if (pendingEvent.current) throw new Error('Save the pending interaction before continuing.');
      if (pendingAnswer.current && JSON.stringify({ status: pendingAnswer.current.status, value: pendingAnswer.current.value, reason_code: pendingAnswer.current.reason_code }) !== JSON.stringify({ status: value.status, value: value.value, reason_code: value.reason_code })) throw new Error('An earlier answer is awaiting acknowledgement. Restore that answer and retry, or reopen the session to recover the server state.');
      const body = pendingAnswer.current || { ...value, version_id: state.version_id, schema_version: 1, expected_revision: state.answers[state.block.block_key]?.revision || 0, client_event_id: crypto.randomUUID(), occurrence: 0 };
      pendingAnswer.current = body;
      await request(`/answers/${encodeURIComponent(state.block.block_key)}`, { method: 'PUT', body: JSON.stringify(body) });
      pendingAnswer.current = null; await load();
    } catch(e) { setError(e.message); } finally { setBusy(false); }
  }
  async function lifecycle(action) {
    setBusy(true); setError('');
    try { await request(`/${action}`, { method: 'POST', ...(action === 'submit' ? { body: JSON.stringify({ version_id: state.version_id, expected_revision: state.revision }) } : {}) }); if (action === 'withdraw') setState({ state: 'withdrawn' }); else await load(); }
    catch(e) { setError(e.message); } finally { setBusy(false); }
  }
  return <main className="study-preview" lang={locale} dir={locale.startsWith('ar') ? 'rtl' : 'ltr'}><header><p>Elseview · Participant session</p><h1>Study</h1><p>Your responses are saved to this consented study session. Timed five-second exposures require another collection client; other core and advanced methods are supported.</p></header><p role="alert">{error}</p>
    {!state && <button type="button" onClick={() => load().catch(e => setError(e.message))}>Load session</button>}
    {state?.block && runnable.includes(state.block.type) && <Question key={state.block.block_key} block={state.block} locale={locale} busy={busy} onSubmit={answer} onEvent={event} loadAsset={ref => request(`/assets/${encodeURIComponent(ref.asset_id)}`).then(r => r.blob())} />}
    {state?.block && !runnable.includes(state.block.type) && <p role="alert">This method is not supported by this collection runner. No answer has been fabricated.</p>}
    {state?.complete && !state.submitted_at && <button disabled={busy} onClick={() => lifecycle('submit')}>Submit completed study</button>}
    {state?.submitted_at && <p role="status">Study submitted.</p>}
    {state?.state === 'withdrawn' ? <p role="status">Participation withdrawn.</p> : state && <details><summary>Withdraw participation</summary><p>This ends participation. You do not need to provide a reason.</p><button disabled={busy} onClick={() => lifecycle('withdraw')}>Confirm withdrawal</button></details>}
  </main>;
}
