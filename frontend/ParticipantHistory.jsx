import React, { useCallback, useEffect, useRef, useState } from 'react';

const ROOT = '/participant/history';
const kinds = { responses: 'Responses', rewards: 'Rewards and payments', attendance: 'Interview attendance' };
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const date = value => value ? new Date(value).toLocaleString() : 'Not recorded';
function errorText(error) {
  if (error.status === 401) return 'Sign in again to view your private history.';
  if (error.status === 403 || error.status === 404) return 'This history is unavailable or its consent or access has changed. Retained financial records may still be available under Rewards and payments.';
  if (error.status === 409) return 'The review changed. Refresh its status before continuing.';
  if (error.status === 422) return 'Check your entries and try again.';
  if (error.status === 429) return 'Too many requests. Wait a few minutes before trying again.';
  return 'The server response was not confirmed. Check your connection and try again.';
}
function pageData(data) {
  if (!data || !Array.isArray(data.items) || data.items.some(item => !uuid.test(item?.id || item?.session_id || item?.workspace_id || '')) || !(data.next_offset === null || Number.isInteger(data.next_offset) && data.next_offset >= 0)) throw new Error('Invalid history response');
  return data;
}
function usePage(request, path) {
  const [state, setState] = useState({ items: [], next_offset: null, busy: true, error: '', loaded: false });
  const sequence = useRef(0), controller = useRef(null);
  const load = useCallback(async (offset = 0) => {
    const current = ++sequence.current;
    controller.current?.abort(); controller.current = new AbortController();
    setState(previous => ({ ...previous, ...(offset === 0 ? { items: [], next_offset: null, loaded: false } : {}), busy: true, error: '' }));
    try {
      const data = pageData(await request(`${path}?offset=${offset}&limit=25`, { signal: controller.current.signal }));
      if (sequence.current !== current) return;
      setState(previous => {
        const items = new Map((offset ? previous.items : []).map(item => [item.id || item.session_id || item.workspace_id, item]));
        data.items.forEach(item => items.set(item.id || item.session_id || item.workspace_id, item));
        return { items: [...items.values()], next_offset: data.next_offset, busy: false, error: '', loaded: true };
      });
    } catch (error) {
      if (sequence.current === current) setState({ items: [], next_offset: null, busy: false, error: errorText(error), loaded: false });
    }
  }, [request, path]);
  useEffect(() => { load(); return () => { sequence.current++; controller.current?.abort(); }; }, [load]);
  return { ...state, load };
}
function PageState({ page, label }) {
  return <><p role="status">{page.busy ? `Loading ${label}…` : page.loaded ? `${page.items.length} ${label} records loaded.` : ''}</p><p role="alert">{page.error}</p><div className="actions"><button className="secondary" disabled={page.busy} onClick={() => page.load()}>Refresh {label}</button>{page.next_offset !== null && <button className="secondary" disabled={page.busy} onClick={() => page.load(page.next_offset)}>Load more {label}</button>}</div></>;
}
function ReviewDetails({ request, workspaceId, sessionId, onRecorded }) {
  const path = `/workspaces/${encodeURIComponent(workspaceId)}/reviews/sessions/${encodeURIComponent(sessionId)}`;
  const [revision, setRevision] = useState(0), [data, setData] = useState(null), [busy, setBusy] = useState(true);
  const [error, setError] = useState(''), [reason, setReason] = useState(''), [sending, setSending] = useState(false), [uncertain, setUncertain] = useState(false);
  const sequence = useRef(0), command = useRef(null), locked = useRef(false), alive = useRef(false);
  useEffect(() => { alive.current = true; return () => { alive.current = false; }; }, []);
  useEffect(() => {
    const current = ++sequence.current, controller = new AbortController();
    setData(null); setBusy(true); setError('');
    request(path + '/status', { signal: controller.signal }).then(result => {
      if (sequence.current !== current) return;
      if (!result || !Array.isArray(result.decisions)) throw new Error('Invalid review status');
      setData(result); setBusy(false);
    }).catch(failure => { if (sequence.current === current) { setError(errorText(failure)); setBusy(false); } });
    return () => { sequence.current++; controller.abort(); };
  }, [request, path, revision]);
  async function appeal(event) {
    event?.preventDefault();
    if (locked.current || busy || !data) return;
    if (!command.current) {
      const text = reason.trim();
      if (!text) { setError('Explain why you would like this decision reconsidered.'); return; }
      if (data.state !== 'rejected' || data.appeal) return;
      command.current = Object.freeze({ command_key: crypto.randomUUID(), reason: text });
    }
    locked.current = true; setSending(true); setError('');
    try {
      await request(path + '/appeal', { method: 'POST', body: command.current });
      if (!alive.current) return;
      command.current = null; setUncertain(false); setReason(''); onRecorded();
    } catch (failure) {
      if (!alive.current) return;
      setError(errorText(failure));
      if (!failure.status || failure.status >= 500) setUncertain(true);
      else { command.current = null; setUncertain(false); setRevision(value => value + 1); }
    } finally { locked.current = false; if (alive.current) setSending(false); }
  }
  return <section aria-label="Review details"><p role="status">{busy ? 'Loading review status…' : sending ? 'Recording your appeal…' : ''}</p><p role="alert">{error}</p><button className="secondary" disabled={busy || sending} onClick={() => setRevision(value => value + 1)}>Refresh review status</button>{data && <><p>Human review: <strong>{data.state}</strong></p><ul>{data.decisions.map((decision, index) => <li key={index}><strong>{decision.verdict}</strong><p dir="auto">{decision.rationale}</p><ul>{Array.isArray(decision.evidence) && decision.evidence.filter(value => typeof value === 'string').map((value, item) => <li key={item} dir="auto">{value}</li>)}</ul></li>)}</ul>{data.appeal && <p>Appeal: {data.appeal.state} · <span dir="auto">{data.appeal.reason}</span></p>}{data.state === 'rejected' && !data.appeal && !uncertain && <form onSubmit={appeal}><label>Why should this decision be reconsidered?<textarea required maxLength={2000} rows={4} value={reason} onChange={event => setReason(event.target.value)} disabled={sending} dir="auto" /></label><button disabled={sending || busy}>{sending ? 'Recording appeal…' : 'Request a human appeal'}</button></form>}</>}{uncertain && <div className="notice"><p>Your appeal may already have been recorded. Its exact request is kept only on this page and will not be repeated automatically. Refresh the status or retry the identical request before leaving.</p><button disabled={sending || busy || !data} onClick={() => appeal()}>Retry identical appeal</button></div>}</section>;
}
function ResponseRecord({ item, request, workspaceId, onRecorded }) {
  const [inspected, setInspected] = useState(false);
  return <li><strong>Submitted {date(item.submitted_at)}</strong><div>Language: {item.locale} · Human review: {item.review_state}{item.appeal_state ? ` · Appeal: ${item.appeal_state}` : ''}</div><p className="muted">Response reference: {item.session_id}{item.occurrence_id ? ' · Diary entry' : ''}</p><details onToggle={event => { if (event.currentTarget.open) setInspected(true); }}><summary>Review decision and appeal</summary>{inspected && <ReviewDetails request={request} workspaceId={workspaceId} sessionId={item.session_id} onRecorded={onRecorded} />}</details></li>;
}
function PaymentDetails({ request, workspaceId, rewardId }) {
  const page = usePage(request, `${ROOT}/${encodeURIComponent(workspaceId)}/rewards/${encodeURIComponent(rewardId)}/payments`);
  return <section aria-label="Payment record history"><PageState page={page} label="payment" />{page.loaded && !page.items.length && <p>No manual payment records have been entered for this reward.</p>}<ul>{page.items.map(item => <li key={item.id}>{date(item.created_at)} · {item.state} · Record {item.id}</li>)}</ul></section>;
}
function RewardRecord({ item, request, workspaceId }) {
  const [inspected, setInspected] = useState(false);
  return <li><strong>{new Intl.NumberFormat(undefined, { style: 'currency', currency: 'TND' }).format(item.amount_millimes / 1000)}</strong><div>{item.state === 'paid' ? 'Recorded as paid' : 'Earned obligation'} · Earned {date(item.created_at)}</div>{item.settled_at && <p>Settlement recorded {date(item.settled_at)}</p>}<p className="muted">Reward reference: {item.id}</p><details onToggle={event => { if (event.currentTarget.open) setInspected(true); }}><summary>View manual payment records</summary>{inspected && <PaymentDetails request={request} workspaceId={workspaceId} rewardId={item.id} />}</details></li>;
}
function Records({ request, workspaceId, kind }) {
  const page = usePage(request, `${ROOT}/${encodeURIComponent(workspaceId)}/${kind}`);
  const [message, setMessage] = useState('');
  function recorded() { setMessage('Your appeal was recorded. A human reviewer will consider it.'); page.load(); }
  return <section aria-label={kinds[kind]}><h3>{kinds[kind]}</h3><p role="status">{message}</p>{kind === 'responses' && <p>Only submitted responses with current source and study consent are available. Decisions are specific to this workspace, not a score shared across clients.</p>}{kind === 'rewards' && <p className="notice">These are manual accounting records, not proof of an automatic bank transfer. Failed or reversed records do not erase an earned obligation. Retained financial records remain available after research consent is withdrawn.</p>}{kind === 'attendance' && <p>Attendance reflects an attributed staff record. “Unknown” does not mean you were absent. Private meeting links and staff notes are not included.</p>}<PageState page={page} label={kind} />{page.loaded && !page.items.length && <p className="notice">No currently available {kinds[kind].toLowerCase()} records on this page.</p>}{kind === 'responses' && page.items.length > 0 && <p className="muted">Of the {page.items.length} responses loaded for this workspace: {page.items.filter(item => item.review_state === 'accepted').length} accepted, {page.items.filter(item => item.review_state === 'rejected').length} rejected, and {page.items.filter(item => !['accepted', 'rejected'].includes(item.review_state)).length} in other review states. This denominator covers loaded records only, not your complete participation history.</p>}<ul className="item-list">{page.items.map(item => kind === 'responses' ? <ResponseRecord key={item.session_id} item={item} request={request} workspaceId={workspaceId} onRecorded={recorded} /> : kind === 'rewards' ? <RewardRecord key={item.id} item={item} request={request} workspaceId={workspaceId} /> : <li key={item.id}><strong>{date(item.starts_at)} – {date(item.ends_at)}</strong><div>Scheduled timezone: {item.timezone} · Booking: {item.state}</div><p>Attendance: {item.attendance}{item.attendance_at ? ` · Recorded ${date(item.attendance_at)}` : ''}</p><p className="muted">Booking reference: {item.id}</p></li>)}</ul></section>;
}
function HistorySession({ request }) {
  const scopes = usePage(request, ROOT);
  const [workspaceId, setWorkspaceId] = useState(''), [kind, setKind] = useState('responses');
  useEffect(() => { if (!workspaceId && scopes.items.length === 1) setWorkspaceId(scopes.items[0].workspace_id); }, [scopes.items, workspaceId]);
  const available = scopes.items.some(item => item.workspace_id === workspaceId);
  return <section aria-label="Your participation history"><h2>Your participation history</h2><p>View your own responses, reviews, rewards and attendance. Choose one research workspace at a time. Workspace references are shown without exposing private team names.</p><PageState page={scopes} label="participation scopes" />{scopes.loaded && !scopes.items.length && <p className="notice">No participation records yet. Taking part in a study is separate from joining a research team.</p>}{scopes.items.length > 0 && <><label>Research workspace<select value={available ? workspaceId : ''} onChange={event => setWorkspaceId(event.target.value)}><option value="">Choose a workspace reference</option>{scopes.items.map(item => <option key={item.workspace_id} value={item.workspace_id}>{item.workspace_id}</option>)}</select></label><fieldset><legend>History to view</legend>{Object.entries(kinds).map(([value, label]) => <label key={value}><input type="radio" name="history-kind" value={value} checked={kind === value} onChange={() => setKind(value)} />{label}</label>)}</fieldset></>}{available && <Records key={`${workspaceId}:${kind}`} request={request} workspaceId={workspaceId} kind={kind} />}</section>;
}
export default function ParticipantHistory({ request, sessionKey }) {
  return <HistorySession key={sessionKey} request={request} />;
}
