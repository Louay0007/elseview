import React, { useEffect, useId, useMemo, useRef, useState } from 'react';
import './account.css';

const PAGE_SIZE = 25;
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const TYPES = { json: 'application/json', csv: 'text/csv', pdf: 'application/pdf', xlsx: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' };
const uncertain = error => !error.status || error.status >= 500 || error.status === 408 || error.code === 'INVALID_RESPONSE';
const invalidResponse = () => Object.assign(new Error('Unreadable response'), { code: 'INVALID_RESPONSE' });
const stateLabel = state => ({ approved: 'Approved', draft: 'Draft — not approved', invalidated: 'Unavailable — invalidated' }[state] || 'Status unavailable');
const styles = `
.research-reports.account-app { --rr-radius:4px; --rr-target:44px; --rr-small:1rem; --rr-medium:1.25rem; --rr-large:1.563rem; --rr-rule:1px; --rr-focus:3px; margin:0; padding:0; max-width:none; }
.research-reports h2 { font-size:var(--rr-large); }
.research-reports h3 { font-size:var(--rr-medium); }
.research-reports h4 { font-size:var(--rr-small); }
.research-reports .rr-layout { display:grid; grid-template-columns:minmax(0,1fr) minmax(0,2fr); gap:var(--space-xl); }
.research-reports .rr-record { border-block-start:var(--rr-focus) solid var(--color-action); padding-block-start:var(--space-l); min-width:0; }
.research-reports .rr-meta { display:flex; flex-wrap:wrap; gap:var(--space-s) var(--space-l); padding:0; list-style:none; }
.research-reports .rr-original { white-space:pre-wrap; overflow-wrap:anywhere; font:inherit; border:var(--rr-rule) solid var(--color-border); border-radius:var(--rr-radius); padding:var(--space-m); max-height:30rem; overflow:auto; }
.research-reports .rr-fields { display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1fr); gap:var(--space-l); }
.research-reports button, .research-reports input, .research-reports select { border-radius:var(--rr-radius); }
.research-reports button:not(:disabled):hover { text-decoration:underline; }
.research-reports button:not(:disabled):active { border-color:var(--color-text); }
.research-reports button:disabled { opacity:1; color:var(--color-muted); background:var(--color-subtle); cursor:not-allowed; }
.research-reports summary { cursor:pointer; }
.research-reports .rr-choice { text-align:start; width:100%; }
.research-reports [aria-pressed=true] { border-inline-start:var(--rr-focus) solid var(--color-action); font-weight:700; }
.research-reports .rr-check { display:flex; align-items:center; gap:var(--space-m); min-height:var(--rr-target); }
.research-reports .rr-check input { width:var(--rr-target); min-width:var(--rr-target); height:var(--rr-target); margin:0; accent-color:var(--color-action); }
@media(max-width:650px) { .research-reports .rr-layout, .research-reports .rr-fields { grid-template-columns:minmax(0,1fr); gap:var(--space-l); } }
`;

function problem(error, action = 'read', scope = 'summary') {
  const known = {
    ANALYSIS_UNAVAILABLE: 'This report is no longer available. Consent, source data, or privacy permissions changed. Refresh the report list.',
    PRIVACY_RESTRICTED: 'Private report access is restricted. Contact the workspace owner; downloading cannot bypass a privacy restriction.',
    REVISION_CONFLICT: 'The report revision or approval state changed. Reload the latest report before another approval.',
    REPORT_INDEX_LIMIT: 'This report page exceeds privacy-check limits. Return to an earlier page or ask the workspace owner to review report availability.',
    EXPORT_TOO_LARGE: 'This report exceeds PDF/XLSX limits. Choose JSON or CSV instead.',
    EXPORT_TIMEOUT: 'Document rendering timed out. Retry this download or choose JSON or CSV.',
    EXPORT_BUSY: 'Document rendering is busy. Wait briefly, then retry this download.',
    EXPORT_FONT_UNAVAILABLE: 'The PDF Unicode font is unavailable. Ask your administrator to configure it, or choose another format.',
    EXPORT_RENDER_FAILED: 'The document could not be rendered safely. Retry the download or choose JSON or CSV.',
  };
  if (known[error.code]) return known[error.code];
  if (error.status === 401) return 'Your session ended. Sign in again to access private reports.';
  if (error.status === 403 || error.status === 404) {
    if (action === 'export' || action === 'download') return scope === 'raw'
      ? 'Raw export access is unavailable. Raw responses require both export and raw-data permission; ask the study owner for access or choose Summary.'
      : 'Summary export access is unavailable. Ask the study owner for export permission. The report may also have been removed or access revoked.';
    if (action === 'approve') return 'Approval is not permitted for this report. Ask the study owner for publish permission.';
    return 'This report is unavailable or your access changed. Ask the study owner for report access and refresh the list.';
  }
  if (error.status === 429) return 'Too many requests. Wait a few minutes before trying again.';
  if (error.status === 422) return 'Check the selected revision and export options, then try again.';
  if (error.status === 409) return 'The report changed. Reload its latest server record before continuing.';
  return action === 'read' ? 'Reports could not be loaded. Check your connection and retry the read.' : 'The server result was not confirmed. No business request will be repeated automatically.';
}

const validList = data => Array.isArray(data?.items) && data.items.every(item => UUID.test(item?.id || '') && (!item.title || typeof item.title === 'string') && (item.revision === undefined || (Number.isSafeInteger(item.revision) && item.revision > 0)) && (item.state === undefined || ['draft', 'approved', 'invalidated'].includes(item.state)));
const validReport = data => UUID.test(data?.id || '') && UUID.test(data.snapshot_id || '') && Number.isSafeInteger(data.revision) && data.revision > 0 && ['draft', 'approved', 'invalidated'].includes(data.state) && data.metrics && typeof data.metrics === 'object' && !Array.isArray(data.metrics);

function useRead(request, path, revision, validate = validReport) {
  const key = `${path}:${revision}`;
  const [state, setState] = useState({ key: '', data: null, busy: true, error: '' });
  useEffect(() => {
    if (!path) return;
    let active = true;
    const controller = new AbortController();
    setState(previous => ({ key, data: previous.path === path ? previous.data : null, path, busy: true, error: '' }));
    request(path, { signal: controller.signal }).then(data => {
      if (!validate(data)) throw invalidResponse();
      if (active) setState({ key, path, data, busy: false, error: '' });
    }).catch(error => {
      if (active) setState({ key, path, data: null, busy: false, error: problem(error) });
    });
    return () => { active = false; controller.abort(); };
  }, [request, path, revision, validate]);
  return state.key === key ? state : { data: null, busy: !!path, error: '' };
}
function ReadStatus({ resource, retry, label }) {
  return <><p role="status">{resource.busy ? `Loading ${label}…` : ''}</p><p role="alert">{resource.error}</p>{resource.error && <button className="secondary" onClick={retry}>Reload {label}</button>}</>;
}

// A new authenticated identity remounts the entire private subtree, including pending commands.
export default function ResearchReports({ request, sessionKey = '', workspaceId }) {
  const identity = useMemo(() => crypto.randomUUID(), [request, sessionKey, workspaceId]);
  return <ReportsPanel key={identity} request={request} workspaceId={workspaceId} />;
}
function ReportsPanel({ request, workspaceId }) {
  const [offset, setOffset] = useState(0), [revision, setRevision] = useState(0), [selected, setSelected] = useState('');
  const [locked, setLocked] = useState(false);
  const base = `/workspaces/${workspaceId}/analytics`;
  const list = useRead(request, `${base}/reports?limit=${PAGE_SIZE}&offset=${offset}`, revision, validList);
  const items = Array.isArray(list.data?.items) ? list.data.items : [];
  const refresh = () => { if (!locked) setRevision(value => value + 1); };
  return <div className="research-reports account-app"><style>{styles}</style>
    <nav aria-label="Report breadcrumb"><a href={`#/workspaces/${workspaceId}`}>Workspace studies</a></nav>
    <h2>Research reports</h2><p>Versioned evidence, reviewed approval, and private downloads. Access and consent are checked again on every download.</p>
    <div className="rr-layout"><section aria-label="Report list"><h3>Available reports</h3><button className="secondary" disabled={locked || list.busy} onClick={refresh}>Refresh reports</button>
      <ReadStatus resource={list} retry={refresh} label="reports" />
      {list.data && !items.length && <p className="notice">{offset ? 'No more accessible reports on this page. Return to the previous page.' : 'No reports are available to your account yet. Ask the study owner to create a report from an authorized analysis snapshot or grant you report access.'}</p>}
      <ul className="item-list">{items.map(item => <li key={item.id}><button className="secondary rr-choice" disabled={locked || list.busy} aria-pressed={selected === item.id} onClick={() => setSelected(item.id)}><bdi dir="auto">{item.title || `Report ${item.id.slice(0, 8)}`}</bdi>{item.revision && <span> · Revision {item.revision}</span>}</button>{item.state && <div>{stateLabel(item.state)}</div>}</li>)}</ul>
      <nav aria-label="Report pages"><button className="secondary" disabled={locked || list.busy || offset === 0} onClick={() => { setSelected(''); setOffset(value => Math.max(0, value - PAGE_SIZE)); }}>Previous page</button><span>Page {offset / PAGE_SIZE + 1}</span><button className="secondary" disabled={locked || list.busy || !list.data || list.data.has_more === false || items.length < PAGE_SIZE || offset >= 10000} onClick={() => { setSelected(''); setOffset(value => value + PAGE_SIZE); }}>Next page</button></nav>
    </section>
    {selected && !list.error && items.some(item => item.id === selected) ? <ReportDetail key={selected} request={request} base={base} reportId={selected} onLock={setLocked} /> : <section className="rr-record" aria-label="Report detail"><h3>Evidence register</h3><p>Choose a report to inspect its exact revision, approval status, and calculated metrics.</p><p className="muted">Summary downloads suppress small groups. Raw responses require separate permission.</p></section>}
    </div>
  </div>;
}
function ReportDetail({ request, base, reportId, onLock }) {
  const id = useId(), heading = useRef(null), alive = useRef(true), operationLock = useRef(false);
  const controllers = useRef(new Set()), urls = useRef(new Map());
  const [revision, setRevision] = useState(0), [version, setVersion] = useState(null), [versionInput, setVersionInput] = useState('');
  const [format, setFormat] = useState('pdf'), [scope, setScope] = useState('summary');
  const [pending, setPending] = useState(null), [artifact, setArtifact] = useState(null), [busy, setBusy] = useState(false), [slow, setSlow] = useState(false);
  const [error, setError] = useState(''), [message, setMessage] = useState(''), [confirm, setConfirm] = useState(false);
  const [blocked, setBlocked] = useState(false);
  const path = `${base}/reports/${reportId}`;
  const latest = useRead(request, path, revision);
  const history = useRead(request, version ? `${path}?revision=${version}` : null, revision);
  const record = version ? history : latest;
  const data = blocked ? null : record.data;
  const historical = !!version && version !== latest.data?.revision;
  const unavailable = busy || !!pending || blocked || latest.busy || record.busy || !data || !!latest.error;
  useEffect(() => { alive.current = true; heading.current?.focus(); return () => { alive.current = false; for (const controller of controllers.current) controller.abort(); for (const [url, timer] of urls.current) { clearTimeout(timer); URL.revokeObjectURL(url); } urls.current.clear(); onLock(false); }; }, []);
  useEffect(() => { onLock(busy || !!pending); }, [busy, pending, onLock]);
  useEffect(() => { if (!busy) { setSlow(false); return; } const timer = setTimeout(() => setSlow(true), 10000); return () => clearTimeout(timer); }, [busy]);
  function refresh() { if (operationLock.current) return; setVersion(null); setBlocked(false); setArtifact(null); setConfirm(false); setRevision(value => value + 1); }
  function chooseVersion(event) { event.preventDefault(); if (unavailable) return; setVersion(Number(versionInput)); setArtifact(null); setConfirm(false); setError(''); setMessage(''); }
  function rememberFailure(failure, operation) {
    setError(problem(failure, operation.kind, operation.scope));
    if ([401, 403, 404].includes(failure.status) || ['ANALYSIS_UNAVAILABLE', 'PRIVACY_RESTRICTED'].includes(failure.code)) { setArtifact(null); setBlocked(true); }
  }
  async function execute(operation) {
    if (operationLock.current) return;
    operationLock.current = true; setBusy(true); setPending(operation); setError(''); setMessage('');
    try {
      const result = await request(operation.path, { method: 'POST', body: JSON.parse(operation.serialized) });
      if (!alive.current) return;
      if (operation.kind === 'approve') {
        if (result?.id !== reportId || result?.state !== 'approved' || result?.revision !== JSON.parse(operation.serialized).expected_revision) throw invalidResponse();
        setPending(null); setConfirm(false); setMessage(`Revision ${result.revision} is approved.`); setRevision(value => value + 1);
      } else {
        if (!UUID.test(result?.id || '') || result.format !== operation.format || result.scope !== operation.scope) throw invalidResponse();
        const next = { id: result.id, format: operation.format, scope: operation.scope };
        setArtifact(next); setPending(null);
        await download(next);
      }
    } catch (failure) {
      if (!alive.current) return;
      rememberFailure(failure, operation);
      if (!uncertain(failure)) { setPending(null); if (failure.code === 'REVISION_CONFLICT') setRevision(value => value + 1); }
    } finally { operationLock.current = false; if (alive.current) setBusy(false); }
  }
  async function download(item) {
    const controller = new AbortController(); controllers.current.add(controller);
    try {
      const response = await request(`${base}/exports/${item.id}`, { rawResponse: true, signal: controller.signal });
      const type = response.headers.get('content-type')?.split(';')[0].trim().toLowerCase();
      if (type !== TYPES[item.format]) throw invalidResponse();
      const blob = await response.blob();
      if (!alive.current || controller.signal.aborted) return;
      const url = URL.createObjectURL(blob), link = document.createElement('a');
      urls.current.set(url, null);
      try { link.href = url; link.download = `report.${item.format}`; document.body.append(link); link.click(); }
      finally { link.remove(); urls.current.set(url, setTimeout(() => { URL.revokeObjectURL(url); urls.current.delete(url); }, 1000)); }
      setMessage(`${item.format.toUpperCase()} ${item.scope} download sent to your browser. Keep this private file secure; downloaded copies cannot be recalled.`);
    } catch (failure) {
      if (alive.current) { if (failure.name === 'AbortError') setMessage('Download canceled. No new export request was sent.'); else rememberFailure(failure, { kind: 'download', scope: item.scope }); }
    } finally { controllers.current.delete(controller); }
  }
  async function retryDownload() {
    if (operationLock.current || !artifact) return;
    operationLock.current = true; setBusy(true); setError(''); setMessage('');
    try { await download(artifact); } finally { operationLock.current = false; if (alive.current) setBusy(false); }
  }
  function startExport(event) {
    event.preventDefault(); if (unavailable || historical) return;
    execute({ kind: 'export', path: `${path}/exports`, serialized: JSON.stringify({ format, scope }), format, scope });
  }
  function approve(event) {
    event.preventDefault(); if (unavailable || historical || !confirm) return;
    execute({ kind: 'approve', path: `${path}/approve`, serialized: JSON.stringify({ expected_revision: data.revision }) });
  }
  return <section className="rr-record" aria-label="Report detail"><h3 ref={heading} tabIndex={-1}>Report {reportId.slice(0, 8)}</h3>
    <p className="muted">Report ID: <bdi>{reportId}</bdi></p>
    <button className="secondary" disabled={busy} onClick={refresh}>Reload latest report</button>
    <ReadStatus resource={latest} retry={refresh} label="latest report" />
    {version && <ReadStatus resource={history} retry={refresh} label="selected revision" />}
    <p id={`${id}-status`} role="status">{busy ? slow ? 'Still working. You can cancel a file download below; do not repeat a pending approval or export request.' : 'Contacting the server…' : message}</p>
    <p id={`${id}-error`} role="alert">{error}</p>
    {busy && artifact && <button className="secondary" onClick={() => { for (const controller of controllers.current) controller.abort(); }}>Cancel download</button>}
    {pending && !busy && <div className="notice"><h4>Unconfirmed {pending.kind === 'approve' ? 'approval' : 'export request'}</h4><p>Keep this page open. Only an explicit retry resends the exact saved request. {pending.kind === 'export' ? 'A lost export response cannot be looked up here. Retrying may create a duplicate export record against the server’s current revision, which may have changed; it does not publish or share a report.' : 'Reload the latest report to check whether this exact revision is approved before retrying.'}</p><button disabled={blocked} onClick={() => execute(pending)}>Retry exact request</button>{pending.kind === 'approve' && latest.data?.state === 'approved' && latest.data.revision === JSON.parse(pending.serialized).expected_revision && <button className="secondary" onClick={() => { setPending(null); setConfirm(false); setMessage('The server confirms this revision is approved. No approval was repeated.'); }}>Accept confirmed approval</button>}</div>}
    {data && !latest.error && <>
      <ul className="rr-meta" aria-label="Revision record"><li><strong>Revision {data.revision}</strong>{historical ? ' · Historical preview' : ' · Latest server record'}</li><li>{stateLabel(data.state)}</li></ul>
      <p>Calculated snapshot metrics · not AI-generated findings. Approval records a human publishing decision; it does not make a panel sample population-representative.</p>
      <p className="muted">Snapshot: <bdi>{data.snapshot_id}</bdi></p>
      <form onSubmit={chooseVersion}><label>Revision to inspect<input type="number" min="1" max={latest.data?.revision} step="1" required value={versionInput} onChange={event => setVersionInput(event.target.value)} disabled={busy || !!pending} /></label><div className="actions"><button className="secondary" disabled={unavailable}>View revision</button>{version && <button type="button" className="secondary" disabled={busy || !!pending} onClick={() => { setVersion(null); setArtifact(null); setConfirm(false); }}>View latest revision</button>}</div></form>
      <details open><summary>Authorized metrics — original text preserved</summary><p>Small or complementary groups may be suppressed. These metrics are not raw response access. Arabic, French, and other original text are not translated.</p><pre className="rr-original" dir="auto" tabIndex={0} aria-label="Original report metrics">{JSON.stringify(data.metrics, null, 2)}</pre></details>
      {data.state === 'draft' && !historical && <form onSubmit={approve} aria-describedby={`${id}-error`}><h4>Approve this revision</h4><p>Approval requires publish permission and applies only to the revision shown. It cannot be undone here.</p><label className="rr-check"><input type="checkbox" checked={confirm} onChange={event => setConfirm(event.target.checked)} disabled={unavailable} required />I reviewed revision {data.revision} and want to approve it.</label><button disabled={unavailable || !confirm}>Approve revision {data.revision}</button></form>}
      <form onSubmit={startExport} aria-describedby={`${id}-export-hint ${id}-error`}><h4>Private download</h4><p id={`${id}-export-hint`}>Summary applies disclosure suppression. Raw includes original responses and requires separate raw-data permission. {historical ? 'Downloads use the latest revision only. Return to the latest revision before exporting.' : 'The server pins the current revision when creating the export. Another researcher may revise it meanwhile; inspect the downloaded snapshot metadata.'}</p>
        <fieldset disabled={unavailable || historical}><legend>Download options</legend><div className="rr-fields"><label>Format<select value={format} onChange={event => { setFormat(event.target.value); setArtifact(null); }}>{Object.keys(TYPES).map(value => <option key={value} value={value}>{value.toUpperCase()}</option>)}</select></label><label>Data scope<select value={scope} onChange={event => { setScope(event.target.value); setArtifact(null); }}><option value="summary">Summary — suppressed metrics</option><option value="raw">Raw — original responses</option></select></label></div></fieldset>
        <div className="actions"><button disabled={unavailable || historical}>{busy ? 'Working…' : `Create ${format.toUpperCase()} ${scope} download`}</button>{artifact && <button type="button" className="secondary" disabled={unavailable} onClick={retryDownload}>Retry download</button>}</div>
      </form>
    </>}
  </section>;
}
