import React, { useEffect, useId, useMemo, useRef, useState } from 'react';
import './account.css';

const ROOT = '/panel/language-assessment-attempts';
const CONSENT = '/panel/language-assessment-consent';
const LANGUAGES = { tunisianArabic: 'Tunisian Arabic', formalArabic: 'Formal Arabic', french: 'French', arabizi: 'Arabizi' };
const date = value => value ? new Date(value).toLocaleString() : 'Not available';
const language = value => LANGUAGES[value] || 'Language not specified';
const uncertain = error => !error.status || error.status >= 500 || error.status === 408 || error.code === 'INVALID_RESPONSE';
function problem(error) {
  const messages = {
    OPT_IN_REQUIRED: 'Complete public-panel opt-in before using assessments. Assessment consent is separate from panel consent.',
    ASSESSMENT_COOLDOWN: 'The published cooldown has not ended. Check your latest start time before trying again.',
    ASSESSMENT_ATTEMPT_LIMIT: 'The rolling 30-day start limit has been reached. Abandoned starts also count.',
    ASSESSMENT_IN_PROGRESS: 'An attempt is already in progress. Open it from your history.',
    ASSESSMENT_CONSENT_REQUIRED: 'This consent grant is no longer available. A new grant cannot restore a withdrawn attempt.',
    ASSESSMENT_SUBMISSION_CLOSED: 'The submission deadline has passed or this attempt is closed. Refresh its server record.',
    ASSESSMENT_APPEAL_CLOSED: 'The appeal window has closed or its evidence is no longer retained.',
    ASSESSMENT_AUTHORITY_DISABLED: 'Assessments are not available yet. No new attempt was started.',
    CONSENT_DOCUMENT_MISMATCH: 'The consent document changed. Refresh and read it before agreeing again.',
  };
  if (messages[error.code]) return messages[error.code];
  if (error.status === 401) return 'Your session ended. Sign in again to view private assessment records.';
  if (error.status === 403) return 'This action is not permitted. Check your panel participation and consent; no approval is implied.';
  if (error.status === 404) return 'This assessment record is unavailable or access has changed.';
  if (error.status === 422) return 'Check the required answers and length limits. Your entries have been kept.';
  if (error.status === 429) return 'Too many requests. Wait a few minutes before trying again.';
  if (error.status === 409) return 'The server record changed or this request conflicts with earlier work. Refresh the record before continuing.';
  return 'The result is unknown. Keep this page open and retry the exact saved request; do not start a replacement request.';
}
function useRead(request, path, revision) {
  const [state, setState] = useState({ data: null, busy: true, error: '' });
  useEffect(() => {
    if (!path) { setState({ data: null, busy: false, error: '' }); return; }
    let active = true; const controller = new AbortController();
    setState(previous => ({ ...previous, busy: true, error: '' }));
    request(path, { signal: controller.signal }).then(data => {
      if (active) setState({ data, busy: false, error: '' });
    }).catch(error => {
      if (active) setState({ data: null, busy: false, error: problem(error) });
    });
    return () => { active = false; controller.abort(); };
  }, [request, path, revision]);
  return state;
}
const styles = `
.participant-assessments.account-app { --pa-radius:4px; --pa-target:44px; --pa-small:1rem; --pa-medium:1.25rem; --pa-large:1.563rem; margin:0; padding:0; max-width:none; }
.participant-assessments h2 { font-size:var(--pa-large); }
.participant-assessments h3 { font-size:var(--pa-medium); }
.participant-assessments h4 { font-size:var(--pa-small); }
.participant-assessments section { margin-block:var(--space-xl); }
.participant-assessments textarea { display:block; width:100%; min-height:calc(var(--pa-target) * 3); padding:var(--space-m); border:1px solid var(--color-border); border-radius:var(--pa-radius); font:inherit; color:var(--color-text); background:var(--color-surface); resize:vertical; }
.participant-assessments button, .participant-assessments select { border-radius:var(--pa-radius); }
.participant-assessments button:not(:disabled):hover { text-decoration:underline; }
.participant-assessments button:not(:disabled):active { border-color:var(--color-text); }
.participant-assessments button:disabled { opacity:1; color:var(--color-muted); background:var(--color-subtle); cursor:not-allowed; }
.participant-assessments label:has(input[type=checkbox]) { display:flex; align-items:center; gap:var(--space-m); min-height:var(--pa-target); }
.participant-assessments input[type=checkbox] { width:var(--pa-target); min-width:var(--pa-target); height:var(--pa-target); margin:0; accent-color:var(--color-action); }
.participant-assessments .pa-policy { display:flex; flex-wrap:wrap; gap:var(--space-s) var(--space-l); padding:0; list-style:none; }
.participant-assessments .pa-record { white-space:pre-wrap; overflow-wrap:anywhere; }
.participant-assessments .pa-columns { display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1fr); gap:var(--space-xl); }
@media(max-width:650px) { .participant-assessments .pa-columns { grid-template-columns:minmax(0,1fr); gap:var(--space-m); } }
`;
function Status({ resource, retry, label }) {
  return <><p role="status">{resource.busy ? `Loading ${label}…` : ''}</p><p role="alert">{resource.error}</p>{resource.error && <button className="secondary" onClick={retry}>Reload {label}</button>}</>;
}

// Pass the stable memory-session request function. Changing it or sessionKey clears all private state.
export default function ParticipantAssessments({ request, sessionKey = '' }) {
  const identity = useMemo(() => crypto.randomUUID(), [request, sessionKey]);
  return <AssessmentPanel key={identity} request={request} />;
}
function AssessmentPanel({ request }) {
  const id = useId(), heading = useRef(null), consentForm = useRef(null), alive = useRef(true), lock = useRef(false);
  const [revision, setRevision] = useState(0), [catalogueOffset, setCatalogueOffset] = useState(0), [historyOffset, setHistoryOffset] = useState(0);
  const [grant, setGrant] = useState(null), [consentOffset, setConsentOffset] = useState(0), [revoked, setRevoked] = useState([]), [selected, setSelected] = useState(null);
  const [attempt, setAttempt] = useState(null), [answers, setAnswers] = useState({}), [reason, setReason] = useState('');
  const [pending, setPending] = useState(null), [busy, setBusy] = useState(false), [slow, setSlow] = useState(false);
  const [error, setError] = useState(''), [message, setMessage] = useState(''), [blocked, setBlocked] = useState(false), [now, setNow] = useState(Date.now());
  const [answerError, setAnswerError] = useState('');
  const document = useRead(request, CONSENT, revision);
  const consents = useRead(request, `/panel/language-assessment-consents?limit=25&offset=${consentOffset}`, revision);
  const catalogue = useRead(request, `/panel/language-assessments?limit=25&offset=${catalogueOffset}`, revision);
  const history = useRead(request, `/panel/language-qualifications?limit=25&offset=${historyOffset}`, revision);
  const detail = useRead(request, selected ? `${ROOT}/${selected}` : null, revision);
  useEffect(() => { alive.current = true; return () => { alive.current = false; }; }, []);
  useEffect(() => { const timer = setInterval(() => setNow(Date.now()), 1000); return () => clearInterval(timer); }, []);
  useEffect(() => { if (!busy) { setSlow(false); return; } const timer = setTimeout(() => setSlow(true), 10000); return () => clearTimeout(timer); }, [busy]);
  useEffect(() => {
    if (!detail.data || detail.data.id !== selected) return;
    setAttempt(detail.data);
    setAnswers(previous => detail.data.responses || previous);
  }, [detail.data, selected]);
  const refresh = () => { if (!lock.current && !pending) setRevision(value => value + 1); };
  const disabled = busy || !!pending || blocked;
  const visibleAttempt = attempt?.id === selected && !detail.error ? attempt : null;
  const expired = visibleAttempt && new Date(visibleAttempt.deadline_at).getTime() <= now;
  const evidence = visibleAttempt?.evidence_available && new Date(visibleAttempt.retention_until).getTime() > now;
  const decisions = visibleAttempt?.decisions || [];
  const canAppeal = evidence && visibleAttempt?.state === 'adjudicated' && decisions.length === 1 && !visibleAttempt.appeal_requested_at && new Date(decisions[0].decided_at).getTime() + 30 * 86400000 > now;
  const records = history.data?.attempts || [];
  const grants = (consents.data?.items || [])
    .filter(receipt => !receipt.withdrawn_at && !revoked.includes(receipt.id))
    .map(receipt => [receipt.id, `Document ${receipt.document_version} · ${date(receipt.created_at)} · ${receipt.id.slice(0, 8)}`]);
  function command(kind, path, body, label, method = 'POST') {
    if (lock.current || pending) return;
    execute({ kind, path, serialized: JSON.stringify(body), label, method });
  }
  async function execute(operation) {
    if (lock.current) return;
    lock.current = true; setPending(operation); setBusy(true); setError(''); setMessage('');
    try {
      const result = await request(operation.path, { method: operation.method, body: JSON.parse(operation.serialized) });
      if (!alive.current) return;
      const body = JSON.parse(operation.serialized);
      if (operation.kind === 'grant') { setGrant(result); setConsentOffset(0); consentForm.current?.reset(); setMessage('Separate assessment consent recorded. You can now choose an assessment.'); }
      else if (operation.kind === 'withdraw') {
        setRevoked(previous => [...previous, body.grant_id]);
        if (grant?.id === body.grant_id) setGrant(null);
        if (attempt?.consent_grant_id === body.grant_id) setAttempt(previous => ({ ...previous, state: 'withdrawn' }));
        setMessage('This exact consent grant was withdrawn. A new grant will not restore its attempts or qualifications.');
      } else {
        setAttempt(result); setSelected(result.id); setAnswers(result.responses || {}); setReason('');
        setMessage(operation.kind === 'start' ? 'Attempt started. Its server deadline is fixed.' : operation.kind === 'submit' ? 'Answers submitted. A human decision is still required; no automatic pass was issued.' : 'Appeal requested. A different authorized reviewer must decide it.');
        setTimeout(() => { if (alive.current) heading.current?.focus(); }, 0);
      }
      setPending(null); setRevision(value => value + 1);
    } catch (failure) {
      if (!alive.current) return;
      setError(problem(failure));
      if (!uncertain(failure)) setPending(null);
      if ([401, 403].includes(failure.status)) { setAttempt(null); setAnswers({}); if (failure.status === 401) setBlocked(true); }
    } finally { lock.current = false; if (alive.current) setBusy(false); }
  }
  function open(row) { if (disabled) return; setAttempt(null); setAnswers({}); setReason(''); setAnswerError(''); setSelected(row.id); setRevision(value => value + 1); }
  function sendAnswers(event) {
    event.preventDefault(); if (disabled) return;
    const tasks = visibleAttempt.tasks || [];
    const missing = tasks.find(task => !answers[task.id]?.trim());
    if (missing) { setAnswerError('Answer every task before submitting.'); event.currentTarget.querySelector(`[name="answer-${missing.id}"]`)?.focus(); return; }
    const responses = Object.fromEntries(tasks.map(task => [task.id, answers[task.id]]));
    // Python JSON uses ASCII escapes and default separators when checking this bound.
    const encoded = JSON.stringify(responses).replace(/[^\x00-\x7F]/g, char => `\\u${char.charCodeAt(0).toString(16).padStart(4, '0')}`);
    if (encoded.length + tasks.length * 2 > 64000) { setAnswerError('These answers exceed the combined 64 KB limit. Shorten the text responses.'); return; }
    setAnswerError(''); command('submit', `${ROOT}/${visibleAttempt.id}/submit`, { command_key: crypto.randomUUID(), responses }, 'Submit answers');
  }
  if (blocked) return <section className="participant-assessments account-app"><h2>Language assessments</h2><p role="alert">Your session ended. Sign in again to view private assessment records.</p></section>;
  return <section className="participant-assessments account-app" aria-labelledby={`${id}-title`}>
    <style>{styles}</style><h2 id={`${id}-title`}>Language assessments</h2>
    <p className="notice"><strong>Text tasks, not professional credentials.</strong> These assessments do not establish speech, accent or certified translation skills. Synthetic practice and legacy development results never establish reviewed recruitment eligibility.</p>
    <p>Private responses and pending requests stay only in this page’s memory. Leaving or reloading loses unsent answers and the exact retry request. Reopen server history before starting replacement work.</p>
    <p role="status">{busy ? slow ? 'Still waiting for the server. Keep this page open; do not start a duplicate request.' : `${pending?.label} — waiting for the server…` : message}</p>
    <p role="alert">{error}</p>
    {pending && !busy && <div className="notice"><p>The outcome is unconfirmed. Other changes are locked until this exact request is resolved.</p><button onClick={() => execute(pending)}>Retry exact request</button></div>}
    <div className="pa-columns">
      <section aria-labelledby={`${id}-consent`}><h3 id={`${id}-consent`}>1. Separate assessment consent</h3>
        <Status resource={document} label="consent document" retry={refresh} />
        {document.data && <><details><summary>Read assessment consent · version {document.data.version}</summary><p className="pa-record">{document.data.body}</p></details>
          <form key={document.data.digest} ref={consentForm} onSubmit={event => { event.preventDefault(); command('grant', CONSENT, { decision: 'granted', document_version: document.data.version, presented_digest: document.data.digest, receipt_key: crypto.randomUUID() }, 'Record consent', 'PUT'); }}>
            <fieldset disabled={disabled || document.busy}><legend>Optional consent for a new attempt</legend><label><input name="assessment-consent" type="checkbox" required />I have read and agree to this separate assessment consent.</label><button>Grant assessment consent</button></fieldset>
          </form>
          {grant && !revoked.includes(grant.id) && <p>Consent recorded at {date(grant.created_at)}. Server checks apply at every step.</p>}
        </>}
        <h4>Own retained consent grants</h4>
        <p>These grants cover the assessment consent document, not a particular version. Unused grants remain listed even when assessments are retired or unavailable. Browse every page to manage older grants.</p>
        <button className="secondary" disabled={disabled || consents.busy} onClick={refresh}>Refresh consent grants</button>
        <Status resource={consents} label="consent grants" retry={refresh} />
        {consents.data && !consents.data.items.length && <p>No retained consent grants on this page.{consentOffset ? ' Return to the previous page.' : ''}</p>}
        <ul className="item-list">{consents.data?.items.map(receipt => <li key={receipt.id}>Document {receipt.document_version} · Granted {date(receipt.created_at)} · Reference {receipt.id.slice(0, 8)}<p>{receipt.withdrawn_at ? `Withdrawn ${date(receipt.withdrawn_at)}` : revoked.includes(receipt.id) ? 'Withdrawal confirmed; refreshing the server record.' : 'Not withdrawn. This alone does not establish current assessment eligibility.'}</p></li>)}</ul>
        <nav aria-label="Own consent grant pages"><button className="secondary" disabled={disabled || consents.busy || !consentOffset} onClick={() => setConsentOffset(Math.max(0, consentOffset - 25))}>Previous consent grants</button><button className="secondary" disabled={disabled || consents.busy || consents.data?.next_offset == null} onClick={() => setConsentOffset(consents.data.next_offset)}>Next consent grants</button></nav>
        {document.data && !!grants.length && <details><summary>Withdraw an exact assessment consent grant</summary><p>Withdrawal blocks new use of the linked attempts and qualifications. It does not immediately erase retained history, and cannot be undone by a new grant.</p><form key={`${consentOffset}-${document.data.digest}-${grants.map(([key]) => key).join(',')}`} onSubmit={event => { event.preventDefault(); const values = new FormData(event.currentTarget); command('withdraw', CONSENT, { decision: 'withdrawn', grant_id: values.get('grant'), document_version: document.data.version, presented_digest: document.data.digest, receipt_key: crypto.randomUUID() }, 'Withdraw consent', 'PUT'); }}><fieldset disabled={disabled || document.busy || consents.busy}><legend>Choose a grant on this page to withdraw</legend><label>Consent grant<select name="grant" required onChange={event => { event.currentTarget.form.querySelector('input[type=checkbox]').checked = false; }}>{grants.map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label><label><input type="checkbox" required />I understand this blocks future use of its linked evidence.</label><button className="secondary">Confirm withdrawal</button></fieldset></form></details>}
      </section>
      <section aria-labelledby={`${id}-available`}><h3 id={`${id}-available`}>2. Available assessments</h3><Status resource={catalogue} label="available assessments" retry={refresh} />
        {!grant && <p>Grant separate assessment consent before starting. Previously granted consent is not inferred from browser history.</p>}
        {catalogue.data && !catalogue.data.items.length && <p>No approved assessments are available on this page. This does not mean you failed an assessment.</p>}
        <ul className="item-list">{catalogue.data?.items.map(version => <li key={version.id}><h4>{language(version.language)} · version {version.version}</h4><p><strong>{version.synthetic ? 'Synthetic practice — not recruitment eligibility' : 'Human-reviewed text assessment'}</strong></p><p>{version.limitations}</p><ul className="pa-policy"><li>{version.policy.duration_minutes} minute deadline</li><li>{version.policy.max_starts_30_days} starts / 30 days</li><li>{version.policy.cooldown_hours} hour cooldown</li><li>{version.policy.validity_days} day qualification validity</li><li>{version.policy.retention_days} day evidence retention</li></ul><p>Starting counts even if you abandon the attempt. Server time and eligibility checks are authoritative.</p><button disabled={disabled || !grant || catalogue.busy} onClick={() => command('start', ROOT, { version_id: version.id, consent_grant_id: grant.id, command_key: crypto.randomUUID() }, 'Start assessment')}>Start {language(version.language)} version {version.version}</button></li>)}</ul>
        <nav aria-label="Available assessment pages"><button className="secondary" disabled={disabled || catalogue.busy || !catalogueOffset} onClick={() => setCatalogueOffset(Math.max(0, catalogueOffset - 25))}>Previous assessments</button><button className="secondary" disabled={disabled || catalogue.busy || catalogue.data?.next_offset == null} onClick={() => setCatalogueOffset(catalogue.data.next_offset)}>Next assessments</button></nav>
      </section>
    </div>
    {selected && <section aria-labelledby={`${id}-attempt`}><h3 tabIndex={-1} ref={heading} id={`${id}-attempt`}>Your selected attempt</h3><Status resource={detail} label="selected attempt" retry={refresh} />
      <button className="secondary" disabled={disabled || detail.busy} onClick={refresh}>Refresh selected attempt</button>
      {visibleAttempt && <><p>{language(visibleAttempt.language)} · attempt {visibleAttempt.sequence} · {expired && visibleAttempt.state === 'started' ? 'deadline passed' : visibleAttempt.state}</p><p>Deadline: {date(visibleAttempt.deadline_at)}. Evidence retained until: {date(visibleAttempt.retention_until)}.</p>
        {!evidence && <p className="notice">Raw evidence is no longer available. Identifier-only decision history may remain.</p>}
        {visibleAttempt.state === 'submitted' && <p className="notice">Awaiting a manual human decision. Correct-looking answers do not automatically qualify you. Refresh to check; no review completion time is promised.</p>}
        {visibleAttempt.state === 'withdrawn' && <p className="notice">The linked consent was withdrawn. This attempt cannot be resumed or revived with a new grant.</p>}
        {evidence && visibleAttempt.state === 'started' && !expired && <form onSubmit={sendAnswers} aria-describedby={`${id}-answer-error`}><p>Every task is required. Text answers allow 1–4,000 characters, within a combined 64 KB limit.</p><fieldset disabled={disabled || detail.busy}><legend>Assessment responses</legend>{visibleAttempt.tasks?.map((task, index) => <fieldset key={task.id}><legend dir="auto">Task {index + 1}: {task.prompt}</legend><ul>{Object.values(task.criteria).map((criterion, i) => <li key={i} dir="auto">{criterion}</li>)}</ul>{task.kind === 'single_choice' ? task.choices.map(choice => <label key={choice.id} dir="auto"><input type="radio" name={`answer-${task.id}`} value={choice.id} checked={answers[task.id] === choice.id} required onChange={() => setAnswers(previous => ({ ...previous, [task.id]: choice.id }))} />{choice.label}</label>) : <label>Response to task {index + 1}<textarea dir="auto" name={`answer-${task.id}`} required maxLength={4000} value={answers[task.id] || ''} onChange={event => setAnswers(previous => ({ ...previous, [task.id]: event.target.value }))} /></label>}</fieldset>)}<button>Submit answers for human review</button></fieldset><p id={`${id}-answer-error`} role="alert">{answerError}</p></form>}
        {evidence && visibleAttempt.responses && <details><summary>Your submitted responses</summary>{Object.entries(visibleAttempt.responses).map(([task, response]) => <div key={task}><h4>{visibleAttempt.tasks?.find(t => t.id === task)?.prompt || task}</h4><p dir="auto" className="pa-record">{response}</p></div>)}</details>}
        {decisions.map(decision => <article key={decision.id}><h4>Human decision · round {decision.round}: {decision.verdict.replaceAll('_', ' ')}</h4><p>Decided {date(decision.decided_at)}{decision.expires_at ? ` · Qualification expires ${date(decision.expires_at)}` : ''}</p><p>This decision alone does not establish current recruitment eligibility. See the server’s current reviewed qualifications below.</p>{evidence && <><p dir="auto" className="pa-record">{decision.rationale}</p>{decision.findings && <ul>{Object.entries(decision.findings).flatMap(([task, criteria]) => Object.entries(criteria).map(([criterion, result]) => <li key={`${task}-${criterion}`}>{task} · {criterion}: {result.replaceAll('_', ' ')}</li>))}</ul>}</>}</article>)}
        {visibleAttempt.appeal_requested_at && <p>Appeal requested {date(visibleAttempt.appeal_requested_at)}. {decisions.length < 2 ? 'Awaiting a different reviewer.' : 'The appeal decision is recorded above.'}</p>}
        {canAppeal && <form onSubmit={event => { event.preventDefault(); if (!reason.trim()) { setError('Explain your appeal using more than spaces.'); return; } command('appeal', `${ROOT}/${visibleAttempt.id}/appeal`, { command_key: crypto.randomUUID(), reason }, 'Request appeal'); }}><fieldset disabled={disabled || detail.busy}><legend>Request your one appeal</legend><p>Available within 30 days of the first decision while evidence remains retained. A different authorized reviewer must decide.</p><label>Appeal reason (required; up to 2,000 characters)<textarea name="appeal-reason" required maxLength={2000} value={reason} onChange={event => setReason(event.target.value)} /></label><button>Request independent appeal</button></fieldset></form>}
      </>}
    </section>}
    <section aria-labelledby={`${id}-history`}><h3 id={`${id}-history`}>Your private assessment history</h3><button className="secondary" disabled={disabled || history.busy} onClick={refresh}>Refresh history and eligibility</button><Status resource={history} label="assessment history" retry={refresh} />
      {history.data && <><h4>Current reviewed qualifications</h4>{!history.data.current.length && <p>No current reviewed qualifications. Synthetic practice, legacy results, withdrawn consent and expired qualifications cannot satisfy this list.</p>}<ul>{history.data.current.map(item => <li key={item.decision_id}>{language(item.language)} · version {item.assessment_version} · {new Date(item.expires_at).getTime() <= now ? 'Expired — refresh eligibility' : 'Expires'} {date(item.expires_at)}</li>)}</ul><p>Expiry blocks new recruitment, not automatic rejection of already-earned participation or payment.</p>
        {!records.length && <p>No attempts on this page. Read the separate consent and available policies before starting.</p>}<ul className="item-list">{records.map(row => <li key={row.id}><strong>{language(row.language)} · attempt {row.sequence}</strong><p>{row.state} · Started {date(row.started_at)}</p><button className="secondary" disabled={disabled} onClick={() => open(row)}>Open {language(row.language)} attempt {row.sequence}</button></li>)}</ul>
        {!!history.data.legacy.length && <details><summary>Legacy development results — not reviewed qualifications</summary><p>These old development checks cannot establish reviewed language eligibility.</p><ul>{history.data.legacy.map((row, i) => <li key={i}>{row.language} · Legacy expiry {date(row.expires_at)}</li>)}</ul></details>}
      </>}
      <nav aria-label="Private history pages"><button className="secondary" disabled={disabled || history.busy || !historyOffset} onClick={() => setHistoryOffset(Math.max(0, historyOffset - 25))}>Previous history</button><button className="secondary" disabled={disabled || history.busy || history.data?.next_offset == null} onClick={() => setHistoryOffset(history.data.next_offset)}>Next history</button></nav>
    </section>
  </section>;
}
