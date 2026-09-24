import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { createApiClient } from './apiClient.js';
import { accountError, accountRoute, createAccountSession } from './accountSession.js';
import EvaluationRunner from './EvaluationRunner.jsx';
import LongitudinalRunner from './LongitudinalRunner.jsx';
import ParticipantAssessments from './ParticipantAssessments.jsx';
import ParticipantHistory from './ParticipantHistory.jsx';
import ParticipantProfile from './ParticipantProfile.jsx';
import ResearchReports from './ResearchReports.jsx';
import './account.css';

const PAGE_SIZE = 25;
const authPages = new Set(['sign-in', 'register', 'recover', 'verify', 'reset']);
const titles = { 'sign-in': 'Sign in', register: 'Create your account', recover: 'Recover your account', verify: 'Verify your email', reset: 'Set a new password' };
const paths = { 'sign-in': '/auth/login', register: '/auth/register', recover: '/auth/password-reset/request', verify: '/auth/verify-email', reset: '/auth/password-reset/confirm' };
const href = (workspace, study) => `#/workspaces/${workspace}${study ? `/studies/${study}` : ''}`;

function useResource(api, path) {
  const [state, setState] = useState({ data: null, error: '', busy: true });
  const [revision, setRevision] = useState(0);
  const reload = useCallback(() => setRevision(value => value + 1), []);
  useEffect(() => {
    const controller = new AbortController(); let active = true;
    setState(previous => ({ ...previous, error: '', busy: true }));
    api(path, { signal: controller.signal }).then(data => {
      if (active) setState({ data, error: '', busy: false });
    }).catch(error => {
      if (active && error.name !== 'AbortError') setState(previous => ({ data: [401, 403, 404].includes(error.status) ? null : previous.data, error: accountError(error), busy: false }));
    });
    return () => { active = false; controller.abort(); };
  }, [api, path, revision]);
  return { ...state, reload };
}
function ResourceStatus({ resource }) {
  return <><p role="status">{resource.busy ? resource.data ? 'Updating the server record…' : 'Loading the server record…' : ''}</p><p role="alert">{resource.error}</p>{resource.error && <button className="secondary" disabled={resource.busy} onClick={resource.reload}>Reload server record</button>}</>;
}
function Pager({ offset, setOffset, count, busy }) {
  return <nav aria-label="Pagination"><button className="secondary" disabled={busy || offset === 0} onClick={() => setOffset(value => Math.max(0, value - PAGE_SIZE))}>Previous page</button><span>Page {offset / PAGE_SIZE + 1}</span><button className="secondary" disabled={busy || count < PAGE_SIZE || offset >= 10000} onClick={() => setOffset(value => value + PAGE_SIZE)}>Next page</button></nav>;
}

function AccountForm({ page, api, onLogin }) {
  const [busy, setBusy] = useState(false), [error, setError] = useState(''), [message, setMessage] = useState('');
  const [slow, setSlow] = useState(false);
  const locked = useRef(false), mounted = useRef(true), formRef = useRef(null);
  useEffect(() => () => { mounted.current = false; }, []);
  useEffect(() => { if (!busy) { setSlow(false); return; } const timer = setTimeout(() => setSlow(true), 10000); return () => clearTimeout(timer); }, [busy]);
  async function send(event, resend = false) {
    event?.preventDefault();
    const form = formRef.current;
    if (locked.current || !form.reportValidity()) return;
    locked.current = true; setBusy(true); setError(''); setMessage('');
    const values = Object.fromEntries(new FormData(form));
    try {
      const result = await api(resend ? '/auth/verification/request' : paths[page], { method: 'POST', body: resend ? { email: values.email } : values });
      if (!mounted.current) return;
      form.reset();
      if (page === 'sign-in' && !resend) onLogin(result);
      else setMessage(resend || ['register', 'recover'].includes(page) ? 'If this request is eligible, instructions will be delivered. Check your inbox and spam folder. Delivery may take a few minutes.' : page === 'verify' ? 'Your email is verified. You can now sign in.' : 'Your password was changed. Sign in with your new password.');
    } catch (failure) {
      if (mounted.current) { setError(accountError(failure)); form.querySelector('input')?.focus(); }
    } finally { locked.current = false; if (mounted.current) setBusy(false); }
  }
  const password = ['sign-in', 'register', 'reset'].includes(page);
  return <section aria-label={titles[page]} className="account-form"><h2>{titles[page]}</h2>
    <p>{page === 'verify' || page === 'reset' ? 'Enter the one-time code from your email. It is not saved in this browser.' : 'Use your account email. Your credentials are not saved in browser storage.'}</p>
    <form ref={formRef} onSubmit={send} aria-describedby="account-error account-status">
      {page === 'register' && <label>Display name (optional)<input name="display_name" maxLength={100} autoComplete="nickname" /></label>}
      {['sign-in', 'register', 'recover'].includes(page) && <label>Email address<input name="email" type="email" inputMode="email" maxLength={254} autoComplete="email" required /></label>}
      {['verify', 'reset'].includes(page) && <label>One-time email code<input name="token" type="password" minLength={20} maxLength={256} autoComplete="one-time-code" required /></label>}
      {password && <label>{page === 'sign-in' ? 'Password' : 'New password'}<input name="password" type="password" minLength={page === 'sign-in' ? 1 : 12} maxLength={256} autoComplete={page === 'sign-in' ? 'current-password' : 'new-password'} aria-describedby="password-hint" required /></label>}
      {password && <p id="password-hint" className="muted">{page === 'sign-in' ? 'Use your current password. Paste and password managers are supported.' : 'Use 12–256 characters. Paste and password managers are supported.'}</p>}
      <div className="actions"><button disabled={busy}>{busy ? 'Please wait…' : titles[page]}</button></div>
    </form>
    <p id="account-error" role="alert">{error}</p><p id="account-status" role="status">{busy ? slow ? 'This is taking longer than expected. Do not submit the request again while it is pending.' : 'Sending your request…' : message}</p>
    {page === 'recover' && <form onSubmit={event => { event.preventDefault(); send(null, true); }}><button className="secondary" disabled={busy}>Send verification instructions instead</button></form>}
  </section>;
}
function NewWorkspace({ api, onCreated }) {
  const [busy, setBusy] = useState(false), [error, setError] = useState(''), [uncertain, setUncertain] = useState(false);
  const locked = useRef(false), mounted = useRef(true);
  useEffect(() => () => { mounted.current = false; }, []);
  async function create(event) {
    event.preventDefault(); if (locked.current || uncertain) return;
    const name = new FormData(event.currentTarget).get('name').trim();
    if (!name) { setError('Enter a workspace name, not only spaces.'); return; }
    locked.current = true; setBusy(true); setError('');
    try { const result = await api('/workspaces', { method: 'POST', body: { name } }); if (mounted.current) onCreated(result); }
    catch (failure) { if (mounted.current) { setError(accountError(failure)); if (!failure.status || failure.status >= 500) setUncertain(true); } }
    finally { locked.current = false; if (mounted.current) setBusy(false); }
  }
  return <section aria-label="Create workspace"><h2>Create a workspace</h2><p>A workspace keeps your team's research separate from other teams.</p><form onSubmit={create} aria-describedby="workspace-create-error"><label>Workspace name<input name="name" required maxLength={100} autoComplete="organization" disabled={busy || uncertain} /></label><button disabled={busy || uncertain}>{busy ? 'Creating workspace…' : 'Create workspace'}</button></form><p id="workspace-create-error" role="alert">{error}</p>{uncertain && <p className="notice">The workspace may have been created. Reload the workspace list and check before creating another. This request will not be repeated automatically.</p>}</section>;
}
function Workspaces({ api }) {
  const [offset, setOffset] = useState(0);
  const resource = useResource(api, `/workspaces?limit=${PAGE_SIZE}&offset=${offset}`);
  const items = resource.data?.items || [];
  return <div className="account-layout"><NewWorkspace api={api} onCreated={workspace => { location.hash = href(workspace.id); }} /><section aria-label="Your workspaces"><h2>Your workspaces</h2><p>Only workspaces available to your account are listed.</p><button className="secondary" disabled={resource.busy} onClick={resource.reload}>Refresh workspaces</button><ResourceStatus resource={resource} />{resource.data && !items.length && <p className="notice">{offset ? 'There are no more workspaces on this page. Return to the previous page.' : 'No workspaces yet. Create one, or ask your team to invite you.'}</p>}<ul className="item-list">{items.map(workspace => <li key={workspace.id}><a href={href(workspace.id)}>{workspace.name}</a></li>)}</ul><Pager offset={offset} setOffset={setOffset} count={items.length} busy={resource.busy} /></section></div>;
}
function Workspace({ api, workspaceId }) {
  const [offset, setOffset] = useState(0);
  const workspace = useResource(api, `/workspaces/${workspaceId}`);
  const studies = useResource(api, `/workspaces/${workspaceId}/studies?limit=${PAGE_SIZE}&offset=${offset}`);
  const items = studies.data?.items || [];
  return <><nav aria-label="Breadcrumb"><a href="#/workspaces">Your workspaces</a></nav><h2>{workspace.data?.name || 'Workspace'}</h2><ResourceStatus resource={workspace} /><nav aria-label="Workspace"><a href={`#/workspaces/${workspaceId}/assignments`}>Your human-review assignments</a><a href={`#/workspaces/${workspaceId}/reports`}>Research reports and exports</a></nav>
    <section aria-label="Studies"><h3>Studies</h3><p>Your account's accessible studies, with status supplied by the server.</p><button className="secondary" disabled={studies.busy} onClick={studies.reload}>Refresh studies</button><ResourceStatus resource={studies} />{studies.data && !items.length && <p className="notice">{offset ? 'No more studies on this page. Return to the previous page.' : 'No studies are available to your account in this workspace. Ask its owner to grant access to an existing study.'}</p>}<ul className="item-list">{items.map(study => <li key={study.id}><a href={href(workspaceId, study.id)}>{study.title}</a><div>Status: {study.status} · {study.ai_policy === 'human_only' ? 'Human-only processing' : 'AI-assisted processing'}</div></li>)}</ul><Pager offset={offset} setOffset={setOffset} count={items.length} busy={studies.busy} /></section>
  </>;
}
function Study({ api, workspaceId, studyId }) {
  const [offset, setOffset] = useState(0);
  const study = useResource(api, `/workspaces/${workspaceId}/studies/${studyId}`);
  const versions = useResource(api, `/workspaces/${workspaceId}/studies/${studyId}/versions?limit=${PAGE_SIZE}&offset=${offset}`);
  const items = versions.data?.items || [];
  return <><nav aria-label="Breadcrumb"><a href="#/workspaces">Your workspaces</a><a href={href(workspaceId)}>Workspace studies</a></nav><h2>{study.data?.title || 'Study'}</h2><ResourceStatus resource={study} />{study.data && <p>Status: {study.data.status} · {study.data.ai_policy === 'human_only' ? 'Human-only processing' : 'AI-assisted processing'}</p>}<section aria-label="Version history"><h3>Version history</h3><ResourceStatus resource={versions} /><button className="secondary" onClick={versions.reload} disabled={versions.busy}>Refresh versions</button><ul className="item-list">{items.map(version => <li key={version.id}><strong>Version {version.number}</strong><div>{version.state} · Revision {version.revision} · Languages: {version.locales.join(', ')}</div>{version.state === 'published' && <a href={`#/workspaces/${workspaceId}/schedule/${version.id}`}>Open your participant schedule for version {version.number}</a>}</li>)}</ul>{versions.data && !items.length && <p>No versions on this page. Return to your workspace or the previous page.</p>}<Pager offset={offset} setOffset={setOffset} count={items.length} busy={versions.busy} /></section></>;
}
function LoginSessions({ session, onLogout }) {
  const resource = useResource(session.request, '/me/login-sessions');
  const [selected, setSelected] = useState(''), [busy, setBusy] = useState(false), [message, setMessage] = useState(''), [error, setError] = useState('');
  const locked = useRef(false), mounted = useRef(true);
  useEffect(() => () => { mounted.current = false; }, []);
  async function revoke(event) {
    event.preventDefault(); if (locked.current || !selected) return;
    const family = selected; locked.current = true; setBusy(true); setError(''); setMessage('');
    try {
      await session.request(`/me/login-sessions/${family}`, { method: 'DELETE' });
      if (!mounted.current) return;
      if (family === session.familyId) { onLogout('This login session was ended. Sign in to continue.'); return; }
      setSelected(''); setMessage('The selected login session was ended.'); resource.reload();
    } catch (failure) { if (mounted.current) { setError(accountError(failure)); resource.reload(); } }
    finally { locked.current = false; if (mounted.current) setBusy(false); }
  }
  return <section aria-label="Login sessions"><nav aria-label="Breadcrumb"><a href="#/workspaces">Your workspaces</a></nav><h2>Login sessions</h2><p>End a session you no longer use. Its access is revoked by the server. Ending this session signs you out of this page.</p><ResourceStatus resource={resource} /><button className="secondary" disabled={busy || resource.busy} onClick={resource.reload}>Refresh login sessions</button><form onSubmit={revoke}><fieldset disabled={busy || resource.busy}><legend>Select a session to end</legend>{resource.data?.items.map((item, index) => <label key={item.id}><input type="radio" name="session" value={item.id} checked={selected === item.id} onChange={() => setSelected(item.id)} required />{item.id === session.familyId ? 'This session' : `Other session ${index + 1}`} · Expires {new Date(item.expires_at).toLocaleString()}</label>)}{resource.data && !resource.data.items.length && <p>No active login sessions were returned.</p>}</fieldset>{selected && <p className="notice">Confirm: ending the selected session cannot be undone. That browser will need to sign in again.</p>}<button disabled={busy || resource.busy || !resource.data?.items.some(item => item.id === selected)}>{busy ? 'Ending session…' : 'Confirm end selected session'}</button></form><p role="status">{message}</p><p role="alert">{error}</p></section>;
}
function Assignments({ api, workspaceId }) {
  const [offset, setOffset] = useState(0);
  const resource = useResource(api, `/workspaces/${workspaceId}/evaluation/assignments?limit=${PAGE_SIZE}&offset=${offset}`);
  const items = resource.data?.items || [];
  return <><nav aria-label="Breadcrumb"><a href={href(workspaceId)}>Workspace studies</a></nav><h2>Your human-review assignments</h2><p>Only assignments the server permits you to review are shown.</p><ResourceStatus resource={resource} /><button className="secondary" disabled={resource.busy} onClick={resource.reload}>Refresh assignments</button><ul className="item-list">{items.map((item, index) => <li key={item.id}><a href={`#/workspaces/${workspaceId}/assignments/${item.id}`}>{item.task.replaceAll('_', ' ')} · Assignment {offset + index + 1}</a><div>{item.submitted ? 'Submitted' : 'Awaiting your review'} · {item.kind}</div></li>)}</ul>{resource.data && !items.length && <p className="notice">No available assignments on this page. Ask your research lead if you expected an assignment.</p>}<nav aria-label="Assignment pages"><button className="secondary" disabled={resource.busy || offset === 0} onClick={() => setOffset(value => Math.max(0, value - PAGE_SIZE))}>Previous page</button><span>Page {offset / PAGE_SIZE + 1}</span><button className="secondary" disabled={resource.busy || offset >= 10000 || resource.data?.has_more === false} onClick={() => setOffset(value => value + PAGE_SIZE)}>Next page</button></nav></>;
}
function PrivateRunner({ session, route }) {
  const container = useRef(null);
  const base = route.page === 'evaluation' ? `/workspaces/${route.workspaceId}/evaluation/assignments/${route.assignmentId}` : '/participant/longitudinal';
  const request = useCallback((path = '', options = {}) => session.request(base + path, { ...options, ...(typeof options.body === 'string' ? { body: JSON.parse(options.body) } : {}), rawResponse: true }), [session, base]);
  useEffect(() => { const heading = container.current?.querySelector('h1'); if (heading) { heading.tabIndex = -1; heading.focus(); } }, [route]);
  return <div ref={container}><header className="account-app"><p>Elseview · Authenticated {route.page === 'evaluation' ? 'human review' : 'participant schedule'}</p><details><summary>Return to your workspace</summary><p>Unsaved answers will be lost when you leave this page. Submit or reconcile pending work first.</p><a className="action-link secondary" href={href(route.workspaceId)}>Leave this page and return to workspace</a></details></header>{route.page === 'evaluation' ? <EvaluationRunner {...route} request={request} /> : <LongitudinalRunner {...route} request={request} />}</div>;
}
function SignedIn({ session, route, onLogout }) {
  const user = useResource(session.request, '/me');
  const [busy, setBusy] = useState(false); const locked = useRef(false);
  async function logout() {
    if (locked.current) return; locked.current = true; setBusy(true);
    try { await session.logout(); onLogout('You are signed out.'); }
    catch { onLogout('Credentials were cleared from this page, but server sign-out was not confirmed. Sign in again, open Login sessions, and end the earlier session.'); }
  }
  return <><div className="actions"><p>{user.data ? `Signed in as ${user.data.display_name || user.data.email}` : 'Signed-in account'}</p><a href="#/workspaces">Workspaces</a><a href="#/participant/profile" aria-current={route.page === 'participant-profile' ? 'page' : undefined}>Panel profile</a><a href="#/participant/assessments">Language assessments</a><a href="#/participant/history">Participation history</a><a href="#/login-sessions">Login sessions</a><button className="secondary" disabled={busy} onClick={logout}>{busy ? 'Signing out…' : 'Sign out'}</button></div><ResourceStatus resource={user} /><p className="muted">Refreshing this page requires you to sign in again. Credentials are kept in memory, not browser storage.</p>{!busy && (route.page === 'participant-profile' ? <ParticipantProfile request={session.request} sessionKey={session.familyId} /> : route.page === 'participant-history' ? <ParticipantHistory request={session.request} sessionKey={session.familyId} /> : route.page === 'assessments' ? <ParticipantAssessments request={session.request} sessionKey={session.familyId} /> : route.page === 'login-sessions' ? <LoginSessions session={session} onLogout={onLogout} /> : route.page === 'reports' ? <ResearchReports request={session.request} sessionKey={session.familyId} workspaceId={route.workspaceId} /> : route.page === 'assignments' ? <Assignments key={route.workspaceId} api={session.request} workspaceId={route.workspaceId} /> : route.page === 'workspace' ? <Workspace key={route.workspaceId} api={session.request} workspaceId={route.workspaceId} /> : route.page === 'study' ? <Study key={`${route.workspaceId}:${route.studyId}`} api={session.request} {...route} /> : <Workspaces api={session.request} />)}</>;
}
export default function AccountApp({ fetchImpl }) {
  const [route, setRoute] = useState(() => accountRoute(location.hash));
  const [session, setSession] = useState(null), [notice, setNotice] = useState('');
  const sessionRef = useRef(null), main = useRef(null);
  const anonymous = useMemo(() => createApiClient({ fetchImpl }), [fetchImpl]);
  useEffect(() => { const change = () => setRoute(accountRoute(location.hash)); window.addEventListener('hashchange', change); return () => window.removeEventListener('hashchange', change); }, []);
  useEffect(() => { main.current?.focus(); document.title = `${session ? 'Your research' : titles[authPages.has(route.page) ? route.page : 'sign-in']} — Elseview`; }, [route, session]);
  useEffect(() => () => { sessionRef.current?.close(); sessionRef.current = null; }, []);
  function signedIn(result) {
    sessionRef.current?.close();
    const next = createAccountSession(result, { fetchImpl, onExpired: () => { if (sessionRef.current === next) { sessionRef.current = null; setSession(null); setNotice('Your session could not be renewed. Sign in again to continue. No pending action was automatically repeated.'); } } });
    sessionRef.current = next; setSession(next); setNotice('');
    if (authPages.has(route.page)) location.hash = '/workspaces';
  }
  function signedOut(message) { sessionRef.current?.close(); sessionRef.current = null; setSession(null); setNotice(message); location.hash = '/sign-in'; }
  const page = authPages.has(route.page) ? route.page : 'sign-in';
  if (session && ['evaluation', 'schedule'].includes(route.page)) return <PrivateRunner key={`${route.page}:${route.workspaceId}:${route.assignmentId || route.versionId}`} session={session} route={route} />;
  return <div className="account-app"><a className="skip-link" href="#account-main" onClick={event => { event.preventDefault(); main.current?.focus(); }}>Skip to content</a><header><p className="eyebrow">Elseview · See what you're missing.</p><h1>{session ? 'Your research' : 'Welcome to Elseview'}</h1><p>Private workspaces. Clear consent. Research you can review.</p></header><main id="account-main" tabIndex={-1} ref={main}><p role="status">{notice}</p>{session ? <SignedIn key="signed-in" session={session} route={route} onLogout={signedOut} /> : <><nav aria-label="Account"><a href="#/sign-in" aria-current={page === 'sign-in' ? 'page' : undefined}>Sign in</a><a href="#/register" aria-current={page === 'register' ? 'page' : undefined}>Create account</a><a href="#/recover" aria-current={page === 'recover' ? 'page' : undefined}>Recover account</a><a href="#/verify" aria-current={page === 'verify' ? 'page' : undefined}>Verify email</a><a href="#/reset" aria-current={page === 'reset' ? 'page' : undefined}>Use reset code</a></nav><AccountForm key={page} page={page} api={anonymous} onLogin={signedIn} /></>}</main></div>;
}
