import React, { useCallback, useEffect, useRef, useState } from 'react';
import CollectionRunner from './CollectionRunner.jsx';
import { authenticatedRequest } from './researchHelpers.js';
import './preview.css';
function instant(value, zone) {
  try { return new Intl.DateTimeFormat(undefined, { timeZone: zone, dateStyle: 'medium', timeStyle: 'long' }).format(new Date(value)); } catch { return value; }
}
function Slots({ slots }) { return <><option value="">Choose a published time</option>{slots.map(s => <option key={s.id} value={s.id}>{instant(s.starts_at, s.timezone)} – {instant(s.ends_at, s.timezone)} ({s.timezone})</option>)}</>; }
export default function LongitudinalRunner({ workspaceId, versionId, token, locale = 'en', request: injectedRequest }) {
  const api = useCallback((path, options) => authenticatedRequest('/api/v1/participant/longitudinal', token, path, options), [token]);
  const request = injectedRequest || api;
  const [data, setData] = useState(null), [error, setError] = useState(''), [status, setStatus] = useState('');
  const [busy, setBusy] = useState(false), [pending, setPending] = useState(null), [child, setChild] = useState(null);
  const capabilities = useRef(new Map()), lock = useRef(false);
  const query = `workspace_id=${encodeURIComponent(workspaceId)}`;
  const load = useCallback(async () => {
    const [slots, bookings, occurrences] = await Promise.all([
      request(`/slots?${query}&version_id=${encodeURIComponent(versionId)}`).then(r => r.json()),
      request(`/bookings?${query}`).then(r => r.json()), request(`/diary-occurrences?${query}`).then(r => r.json()),
    ]); setData({ slots, bookings, occurrences });
  }, [request, query, versionId]);
  useEffect(() => { load().catch(() => setError('Schedule unavailable. Check authorization and study access.')); }, [load]);
  async function act(action) {
    if (lock.current) return;
    lock.current = true; setBusy(true); setError(''); setStatus('Saving…'); setPending(action);
    try {
      const result = await (await request(action.path, { method: 'POST', body: JSON.stringify(action.body) })).json();
      setPending(null); setStatus('Saved.');
      if (action.occurrenceId) setChild({ sessionId: result.session_id, token: action.body.capability, locale });
      await load().catch(() => setError('Request saved, but schedule refresh failed. Refresh to view current state.'));
    } catch(e) {
      if (e.status >= 400 && e.status < 500) { setPending(null); setError('Request rejected. Refresh the schedule before choosing again; capacity, revisions, consent or reporting windows may have changed.'); }
      else setError('Not acknowledged. Retry the identical request; do not make another booking until server state is reconciled.');
      setStatus('');
    } finally { lock.current = false; setBusy(false); }
  }
  function start(o) {
    let capability = capabilities.current.get(o.id);
    if (!capability) {
      if (o.session_id) { setError('Original session credential required to resume.'); return; }
      capability = Array.from(crypto.getRandomValues(new Uint8Array(32)), v => v.toString(16).padStart(2, '0')).join('');
      capabilities.current.set(o.id, capability);
    }
    act({ path: `/diary-occurrences/${encodeURIComponent(o.id)}/start`, body: { capability }, occurrenceId: o.id });
  }
  if (child) return <><button type="button" onClick={() => { setChild(null); load().catch(() => setError('Could not refresh occurrences.')); }}>Return to diary schedule</button><CollectionRunner key={child.sessionId} {...child} /></>;
  return <main className="study-preview"><h1>Interviews and diary</h1><p>Times show the published IANA time zone. Server time determines availability. Booking does not record attendance or grant recording consent.</p><p role="alert">{error}</p><p role="status">{status}</p>
    <button type="button" disabled={busy} onClick={() => load().then(() => setStatus('Schedule refreshed.')).catch(() => setError('Refresh failed.'))}>Refresh schedule</button>
    {pending && <button type="button" disabled={busy} onClick={() => act(pending)}>Retry identical request</button>}
    {data && <><section><h2>Book an interview</h2><form onSubmit={e => { e.preventDefault(); const values = new FormData(e.currentTarget); act({ path: '/bookings', body: { slot_id: values.get('slot'), request_key: crypto.randomUUID() } }); }}><fieldset disabled={busy || !!pending}><legend>Published slots</legend><label>Interview time<select name="slot" required><Slots slots={data.slots} /></select></label><button>Book selected time</button></fieldset></form><p>Availability is confirmed only when the server accepts your booking.</p></section>
      <section><h2>Your bookings</h2>{!data.bookings.length && <p>No bookings.</p>}{data.bookings.map(b => <article key={b.id}><h3>{instant(b.slot.starts_at, b.slot.timezone)}</h3><p>Ends {instant(b.slot.ends_at, b.slot.timezone)} · {b.slot.timezone}</p><p>Status: {b.state}. Attendance: {b.attendance || 'unknown'}.</p>
        {b.state === 'booked' && <>{typeof b.slot.join_url === 'string' && /^https:\/\//i.test(b.slot.join_url) && <a href={b.slot.join_url} rel="noreferrer noopener" referrerPolicy="no-referrer" target="_blank">Join authorized interview (new tab)</a>}
          <form onSubmit={e => { e.preventDefault(); const values = new FormData(e.currentTarget); act({ path: `/bookings/${encodeURIComponent(b.id)}/reschedule`, body: { slot_id: values.get('slot'), expected_revision: b.revision } }); }}><fieldset disabled={busy || !!pending}><legend>Reschedule this booking</legend><label>Replacement time<select name="slot" required><Slots slots={data.slots.filter(s => s.version_id === b.slot.version_id && s.id !== b.slot.id)} /></select></label><button>Confirm reschedule</button></fieldset></form>
          <details><summary>Cancel this booking</summary><p>Cancellation releases your reserved place.</p><button type="button" disabled={busy || !!pending} onClick={() => act({ path: `/bookings/${encodeURIComponent(b.id)}/cancel`, body: { expected_revision: b.revision } })}>Confirm cancellation</button></details></>}
      </article>)}</section>
      <section><h2>Diary occurrences</h2><p>Complete initial participation before diary entries. Each occurrence opens a separate survey session; diary v1 repeats the full initial survey. Submit required prompts within the open/grace window.</p><p>Credentials stay only in this page’s memory. Returning to this schedule keeps them, but refreshing or closing loses them. Existing sessions require their original credential. Keep this page open while completing an occurrence.</p>{!data.occurrences.length && <p>No diary occurrences.</p>}
        {data.occurrences.map(o => <article key={o.id}><h3>Occurrence {o.ordinal + 1}</h3><p>Status: {o.state}</p><p>Opens: {instant(o.opens_at, o.timezone)}<br />Due: {instant(o.due_at, o.timezone)}<br />Grace ends: {instant(o.grace_at, o.timezone)} · {o.timezone}</p>{['open', 'grace'].includes(o.state) && <button type="button" disabled={busy || !!pending || (!!o.session_id && !capabilities.current.has(o.id))} onClick={() => start(o)}>{o.session_id ? 'Resume occurrence' : 'Start occurrence'}</button>}{o.session_id && !capabilities.current.has(o.id) && o.state !== 'submitted' && <p>Original session credential required to resume.</p>}</article>)}
      </section></>}
  </main>;
}
