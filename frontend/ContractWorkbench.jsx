import React, { useMemo, useRef, useState } from 'react';
import { createApiClient } from './apiClient.js';
import CollectionRunner from './CollectionRunner.jsx';

function Command({ title, fields = [], action, label, reload, initial = {}, render }) {
  const [values, setValues] = useState(initial), [result, setResult] = useState(null);
  const [error, setError] = useState(''), [busy, setBusy] = useState(false);
  const pending = useRef(null), locked = useRef(false);
  async function run(recover = false) {
    if (locked.current) return;
    locked.current = true; setBusy(true); setError('');
    try {
      if (!recover && !pending.current) pending.current = { values: { ...values }, key: crypto.randomUUID() };
      const data = recover ? await reload(values) : await action(pending.current.values, pending.current.key);
      setResult(data); pending.current = null;
    } catch (failure) {
      setError(failure.message);
      // Validation rejected this command before execution. Permit correction with
      // a new key; ambiguous transport/server failures must retain the old key.
      if (failure.status === 422) pending.current = null;
      if ([401, 403, 404].includes(failure.status)) setResult(null);
    }
    finally { locked.current = false; setBusy(false); }
  }
  return <section aria-label={title}><h2>{title}</h2><form onSubmit={event => { event.preventDefault(); run(); }}>
    <fieldset disabled={busy || !!pending.current}><legend>{title} details</legend>{fields.map(({ name, label: text, type = 'text', ...props }) => <label key={name} style={{ display: 'block', margin: '12px 0' }}>{text}<input name={name} type={type} value={values[name] || ''} onChange={event => setValues({ ...values, [name]: event.target.value })} required {...props} /></label>)}</fieldset>
    <button disabled={busy} type="submit">{pending.current ? 'Retry same command' : label}</button>
    {reload && <button type="button" disabled={busy} onClick={() => run(true)}>Reload server record</button>}
  </form><p role="alert">{error}</p><p role="status">{busy ? 'Request in progress…' : result ? 'Server response received.' : ''}</p>
    {error && <p>{pending.current ? 'Retries preserve the original payload and command key.' : 'Correct the rejected input and submit again.'} Reload retrieves authoritative state; it does not repeat a mutation.</p>}
    {result && (render ? render(result) : <pre>{JSON.stringify(result, null, 2)}</pre>)}
  </section>;
}
const id = (name, label) => ({ name, label, pattern: '[0-9a-fA-F-]{36}' });
export default function ContractWorkbench({ token = '', workspaceId = '', sessionId, sessionToken, initial = {} }) {
  const api = useMemo(() => createApiClient({ token }), [token]);
  const base = `/workspaces/${encodeURIComponent(workspaceId)}`;
  const [participant, setParticipant] = useState(false);
  // Keying this inner surface prevents pending commands crossing account/workspace boundaries.
  return <div key={`${workspaceId}:${token}`}>
    <header><h1>Research contract workbench</h1><p>Server-backed controls. Access, consent, metrics and eligibility are decided by the API. Registration does not sign you in.</p></header>
    <Command title="Registration" label="Register" initial={initial.registration} fields={[{ name: 'display_name', label: 'Display name', maxLength: 100 }, { name: 'email', label: 'Email', type: 'email', autoComplete: 'email', maxLength: 254 }, { name: 'password', label: 'Password', type: 'password', minLength: 12, maxLength: 256, autoComplete: 'new-password' }]} action={values => api('/auth/register', { method: 'POST', body: values })} />
    <Command title="Create study" label="Create study" initial={initial.study} fields={[{ name: 'title', label: 'Study title', maxLength: 200 }, id('retention_policy_id', 'Retention policy ID')]} action={(values, key) => api(`${base}/studies`, { method: 'POST', body: { ...values, ai_policy: 'human_only' }, idempotencyKey: key })} />
    <Command title="Review" label="Accept assignment" initial={initial.review} fields={[id('assignment_id', 'Assignment ID'), { name: 'rationale', label: 'Review rationale', maxLength: 2000 }]} action={({ assignment_id, rationale }, key) => api(`${base}/reviews/assignments/${encodeURIComponent(assignment_id)}/decision`, { method: 'POST', body: { command_key: key, verdict: 'accepted', rationale, evidence: [] } })} reload={({ assignment_id }) => api(`${base}/reviews/assignments/${encodeURIComponent(assignment_id)}`)} />
    <Command title="Report" label="Load report" initial={initial.report} fields={[id('report_id', 'Report ID')]} action={({ report_id }) => api(`${base}/analytics/reports/${encodeURIComponent(report_id)}`)} reload={({ report_id }) => api(`${base}/analytics/reports/${encodeURIComponent(report_id)}`)} />
    <AI api={api} base={base} initial={initial.ai} />
    {sessionId && <section aria-label="Participant"><h2>Participant completion</h2><p>Reopen discards local pending changes and reloads the consented session from the server.</p><button onClick={() => setParticipant(value => !value)}>{participant ? 'Close participant session' : 'Open participant session'}</button>{participant && <CollectionRunner sessionId={sessionId} token={sessionToken} />}</section>}
  </div>;
}
function AI({ api, base, initial }) {
  const [run, setRun] = useState(null), [error, setError] = useState(''), [busy, setBusy] = useState(false);
  async function refresh() {
    setBusy(true); setError('');
    try { setRun(await api(`${base}/ai/runs/${encodeURIComponent(run.id)}`)); }
    catch (failure) { setError(failure.message); if ([401, 403, 404].includes(failure.status)) setRun(null); }
    finally { setBusy(false); }
  }
  return <section aria-label="AI status"><Command title="AI request" label="Queue AI draft" initial={initial} fields={[id('study_id', 'AI study ID')]} action={async (values, key) => { const data = await api(`${base}/ai/runs`, { method: 'POST', body: { ...values, operation: 'study_helper', instruction: '', researcher_text_approved: false, command_key: key } }); setRun(data); return data; }} render={() => null} />
    <p role="alert">{error}</p><p role="status">{run ? `AI state: ${run.state}. Human review is required; this is not an approved report.` : ''}</p>{run && <><button disabled={busy} onClick={refresh}>Refresh AI status</button><pre>{JSON.stringify(run, null, 2)}</pre></>}
  </section>;
}
