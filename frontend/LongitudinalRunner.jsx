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
  const [loading, setLoading] = useState(false), [needsRefresh, setNeedsRefresh] = useState(true);
  const capabilities = useRef(new Map()), lock = useRef(false), generation = useRef(0), scope = useRef(0);
  const query = `workspace_id=${encodeURIComponent(workspaceId)}`;
  const json = useCallback(async (path, options) => {
    const response = await request(path, options);
    if (!response.ok) { const failure = new Error('Request rejected.'); failure.status = response.status; throw failure; }
    return response.json();
  }, [request]);
  const load = useCallback(async () => {
    const current = ++generation.current;
    setLoading(true); setError('');
    try {
      const [slots, bookings, occurrences] = await Promise.all([
        json(`/slots?${query}&version_id=${encodeURIComponent(versionId)}`),
        json(`/bookings?${query}`), json(`/diary-occurrences?${query}`),
      ]);
      if (current !== generation.current) return false;
      setData({ slots, bookings, occurrences }); setNeedsRefresh(false);
      return true;
    } catch (e) {
      if (current !== generation.current) return false;
      setNeedsRefresh(true); setError('Schedule unavailable. Refresh after checking authorization and study access.');
      if ([401, 403, 404].includes(e.status)) { setData(null); setChild(null); setPending(null); capabilities.current.clear(); }
      return false;
    } finally { if (current === generation.current) setLoading(false); }
  }, [json, query, versionId]);
  useEffect(() => {
    scope.current++; capabilities.current.clear(); lock.current = false;
    setData(null); setChild(null); setPending(null); setBusy(false); setNeedsRefresh(true); setStatus('');
    load();
    return () => { scope.current++; generation.current++; };
  }, [load]);
  async function act(action) {
    if (lock.current) return;
    const current = scope.current;
    lock.current = true; setBusy(true); setError(''); setStatus('Saving…'); setPending(action);
    try {
      const result = await json(action.path, { method: 'POST', body: JSON.stringify(action.body) });
      if (current !== scope.current) return;
      setPending(null); setStatus('Saved.');
      if (action.occurrenceId) {
        capabilities.current.set(action.occurrenceId, action.body.capability);
        setChild({ sessionId: result.session_id, token: action.body.capability, locale: result.locale || locale });
      }
      await load();
    } catch(e) {
      if (current !== scope.current) return;
      if (e.status >= 400 && e.status < 500) {
        setPending(null); setNeedsRefresh(true);
        if (action.occurrenceId) capabilities.current.delete(action.occurrenceId);
        if ([401, 403, 404].includes(e.status)) { setData(null); capabilities.current.clear(); }
        setError('Request rejected. Successfully refresh the schedule before choosing again; capacity, revisions, consent or reporting windows may have changed.');
      } else setError('Not acknowledged. Retry the identical request; do not start another action until server state is reconciled.');
      setStatus('');
    } finally { if (current === scope.current) { lock.current = false; setBusy(false); } }
  }
  function start(o, recover = false) {
    const capability = !recover && capabilities.current.get(o.id) || Array.from(crypto.getRandomValues(new Uint8Array(32)), v => v.toString(16).padStart(2, '0')).join('');
    act({ path: `/diary-occurrences/${encodeURIComponent(o.id)}/${recover ? 'recover' : 'start'}`, body: { capability, ...(recover ? { expected_revision: o.session_revision } : {}) }, occurrenceId: o.id });
  }
  const disabled = busy || loading || needsRefresh || !!pending;
  if (child) return <><button type="button" onClick={() => { setChild(null); load(); }}>Return to diary schedule</button><CollectionRunner key={child.sessionId} {...child} /></>;
  return <main className="study-preview"><h1>Interviews and diary</h1><p>Times show the published IANA time zone. Server time determines availability. Booking does not record attendance or grant recording consent.</p><p role="alert">{error}</p><p role="status">{loading ? 'Loading schedule…' : status}</p>
    <button type="button" disabled={busy || loading} onClick={() => load().then(ok => { if (ok) setStatus('Schedule refreshed.'); })}>Refresh schedule</button>
    {pending && <button type="button" disabled={busy || loading} onClick={() => act(pending)}>Retry identical request</button>}
    {data && <><section><h2>Book an interview</h2><form onSubmit={e => { e.preventDefault(); const values = new FormData(e.currentTarget); act({ path: '/bookings', body: { slot_id: values.get('slot'), request_key: crypto.randomUUID() } }); }}><fieldset disabled={disabled}><legend>Published slots</legend><label>Interview time<select name="slot" required><Slots slots={data.slots} /></select></label><button>Book selected time</button></fieldset></form><p>Availability is confirmed only when the server accepts your booking.</p></section>
      <section><h2>Your bookings</h2>{!data.bookings.length && <p>No bookings.</p>}{data.bookings.map(b => <article key={b.id}><h3>{instant(b.slot.starts_at, b.slot.timezone)}</h3><p>Ends {instant(b.slot.ends_at, b.slot.timezone)} · {b.slot.timezone}</p><p>Status: {b.state}. Attendance: {b.attendance || 'unknown'}.</p>
        {b.state === 'booked' && <>{typeof b.slot.join_url === 'string' && /^https:\/\//i.test(b.slot.join_url) && <a href={b.slot.join_url} rel="noreferrer noopener" referrerPolicy="no-referrer" target="_blank">Join authorized interview (new tab)</a>}
          <form onSubmit={e => { e.preventDefault(); const values = new FormData(e.currentTarget); act({ path: `/bookings/${encodeURIComponent(b.id)}/reschedule`, body: { slot_id: values.get('slot'), expected_revision: b.revision } }); }}><fieldset disabled={disabled}><legend>Reschedule this booking</legend><label>Replacement time<select name="slot" required><Slots slots={data.slots.filter(s => s.version_id === b.slot.version_id && s.id !== b.slot.id)} /></select></label><button>Confirm reschedule</button></fieldset></form>
          <details><summary>Cancel this booking</summary><p>Cancellation releases your reserved place.</p><button type="button" disabled={disabled} onClick={() => act({ path: `/bookings/${encodeURIComponent(b.id)}/cancel`, body: { expected_revision: b.revision } })}>Confirm cancellation</button></details></>}
      </article>)}</section>
      <section><h2>Diary occurrences</h2><p>Complete initial participation before diary entries. Each occurrence opens a separate survey session; diary v1 repeats the full initial survey. Submit required prompts within the open/grace window.</p><p>Credentials stay only in this page’s memory. After returning or signing in again, recover an active occurrence to continue its saved answers. Recovery ends that occurrence’s access in other pages; its original response language is preserved.</p>{!data.occurrences.length && <p>No diary occurrences.</p>}
        {data.occurrences.map(o => <article key={o.id}><h3>Occurrence {o.ordinal + 1}</h3><p>Status: {o.state}</p><p>Opens: {instant(o.opens_at, o.timezone)}<br />Due: {instant(o.due_at, o.timezone)}<br />Grace ends: {instant(o.grace_at, o.timezone)} · {o.timezone}</p>{['open', 'grace'].includes(o.state) && <>
          {(!o.session_id || capabilities.current.has(o.id)) && <button type="button" disabled={disabled} onClick={() => start(o)}>{o.session_id ? 'Resume occurrence' : 'Start occurrence'}</button>}
          {o.session_id && <button type="button" disabled={disabled || !Number.isInteger(o.session_revision)} onClick={() => start(o, true)}>Recover occurrence</button>}
        </>}</article>)}
      </section></>}
  </main>;
}
