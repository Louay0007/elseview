import React, { useEffect, useRef, useState } from 'react';
import { authenticatedRequest, selectedSpan } from './researchHelpers.js';
import { normalizedPoint } from './firstClickGeometry.js';
import './preview.css';

export function EvaluationForm({ assignment: a, request, onSaved }) {
  const [annotations, setAnnotations] = useState([]), [choice, setChoice] = useState(''), [ratings, setRatings] = useState({});
  const [reason, setReason] = useState(''), [language, setLanguage] = useState(a.source.language);
  const [label, setLabel] = useState(a.schema.labels[0]?.id || ''), [polygon, setPolygon] = useState([]);
  const [x, setX] = useState(''), [y, setY] = useState(''), [image, setImage] = useState('');
  const [error, setError] = useState(''), [busy, setBusy] = useState(false), [pending, setPending] = useState(null);
  const [turns, setTurns] = useState([]), [outcome, setOutcome] = useState(''), [duration, setDuration] = useState(''), [confirmed, setConfirmed] = useState(false);
  const text = useRef(null), task = a.schema.task;
  useEffect(() => {
    let active = true, url;
    if (task === 'image_polygons') request('/image').then(r => r.blob()).then(blob => { url = URL.createObjectURL(blob); if (active) setImage(url); else URL.revokeObjectURL(url); }).catch(() => setError('Private image unavailable.'));
    return () => { active = false; if (url) URL.revokeObjectURL(url); };
  }, [task, request]);
  const add = value => { setAnnotations(old => [...old, value]); setError(''); };
  function vertex(px, py) { if (![px, py].every(n => Number.isFinite(n) && n >= 0 && n <= 1) || polygon.length >= 100) { setError('Use coordinates from 0 to 1; maximum 100 vertices.'); return; } setPolygon(old => [...old, [px, py]]); }
  async function submit(event) {
    event.preventDefault(); setBusy(true); setError('');
    const body = pending || { reason: { text: reason, language }, annotations, ...(task === 'pairwise' ? { choice } : {}), ratings: ['pairwise', 'language_review'].includes(task) && choice !== 'cannot_judge' ? (task === 'pairwise' ? ['left', 'right'] : ['source']).flatMap(candidate_id => a.schema.dimensions.map(d => ({ candidate_id, dimension_id: d.id, value: Number(ratings[`${candidate_id}:${d.id}`]) }))) : [] };
    if (!pending && task === 'sandbox') Object.assign(body, { turns, outcome, duration_ms: Number(duration), scenario_revision: a.source.scenario.revision, fictional_confirmation: confirmed });
    setPending(body);
    try { await request('/outcome', { method: 'POST', body: JSON.stringify(body) }); onSaved(); }
    catch (e) { if (e.status === 422) { setPending(null); setError('Answer rejected. Check annotation bounds, overlapping spans, polygon intersections and required transcript limits, then correct your answer.'); } else setError('Submission not acknowledged. Retry sends exactly the same answer, or reload to check whether it was saved.'); }
    finally { setBusy(false); }
  }
  if (!['classification', 'text_spans', 'image_polygons', 'pairwise', 'language_review', 'sandbox'].includes(task)) return <p role="alert">This task is not supported here. No submission will be generated.</p>;
  if (a.outcome) return <p role="status">Your assignment has already been submitted.</p>;
  return <form onSubmit={submit}><p role="alert">{error}</p><p>{a.schema.instructions}</p><p>Instructions: {a.schema.instructions_version}. {a.schema.language_basis}</p>
    <details><summary>Rights and compensation</summary>{Object.entries(a.rights).map(([key, value]) => <p key={key}>{key.replaceAll('_', ' ')}: {String(value)}</p>)}</details>
    <p lang={a.source.language} dir="auto" style={{ whiteSpace: 'pre-wrap' }}>{a.source.text}</p>{a.source.testcase && <p>Test case: {a.source.testcase}</p>}
    {a.originals && <details><summary>Original independent reviews for adjudication</summary>{a.originals.map((o, i) => <pre key={i} style={{ whiteSpace: 'pre-wrap' }}>{JSON.stringify(o.body, null, 2)}</pre>)}</details>}
    <fieldset disabled={busy || !!pending}><legend>Your human review</legend>
      {task === 'sandbox' && <section><h2>Manual fictional transcript</h2><p>{a.source.scenario.instructions}</p><p>No live connector is used. These are your manually supplied, unverified observations, not verified bot output. Never enter real personal data, credentials, URLs or production actions.</p><p>Scenario {a.source.scenario.revision}; policy {a.source.scenario.business_policy_version}. Limit: {a.source.scenario.max_turns} turns, {a.source.scenario.max_characters} total characters.</p>
        {turns.map((turn, i) => <fieldset key={i}><legend>Turn {i + 1}</legend><label>Speaker<select value={turn.role} onChange={e => setTurns(turns.map((t, j) => i === j ? { ...t, role: e.target.value } : t))}><option value="user">User</option><option value="assistant">Assistant under test</option></select></label><label>Verbatim fictional text<textarea required maxLength={Math.min(20000, a.source.scenario.max_characters)} value={turn.text} onChange={e => setTurns(turns.map((t, j) => i === j ? { ...t, text: e.target.value } : t))} /></label><label>Turn language<input required value={turn.language} onChange={e => setTurns(turns.map((t, j) => i === j ? { ...t, language: e.target.value } : t))} /></label><button type="button" onClick={() => setTurns(turns.filter((_, j) => j !== i))}>Remove turn {i + 1}</button></fieldset>)}
        <button type="button" disabled={turns.length >= a.source.scenario.max_turns} onClick={() => setTurns([...turns, { role: 'user', text: '', language }])}>Add transcript turn</button><label>Observed outcome<select required value={outcome} onChange={e => setOutcome(e.target.value)}><option value="">Choose outcome</option><option value="completed">Completed</option><option value="failed">Task failed</option><option value="gave_up">Gave up</option><option value="infrastructure_failure">Infrastructure failure (not a model failure)</option></select></label><label>Observed duration (milliseconds)<input required type="number" min="0" step="1" max={a.source.scenario.max_duration_ms} value={duration} onChange={e => setDuration(e.target.value)} /></label><label><input type="checkbox" required checked={confirmed} onChange={e => setConfirmed(e.target.checked)} />I confirm this transcript uses fictional inputs only and contains no private data.</label></section>}
      {task === 'pairwise' && <><div>{a.source.candidates.map(c => <section key={c.id}><h2>{c.id === 'left' ? 'Left response' : 'Right response'}</h2><p dir="auto" style={{ whiteSpace: 'pre-wrap' }}>{c.text}</p></section>)}</div><fieldset><legend>Comparison</legend>{[['left', 'Left'], ['right', 'Right'], ['tie', 'Tie'], ['both_bad', 'Both bad'], ['cannot_judge', 'Cannot judge']].map(([v, name]) => <label key={v}><input required type="radio" name="choice" value={v} checked={choice === v} onChange={() => setChoice(v)} />{name}</label>)}</fieldset></>}
      {['pairwise', 'language_review'].includes(task) && choice !== 'cannot_judge' && (task === 'pairwise' ? ['left', 'right'] : ['source']).map(side => <fieldset key={side}><legend>{side} rubric · {a.schema.rubric_version}</legend>{a.schema.dimensions.map(d => <label key={d.id}>{d.id} ({d.min}–{d.max})<input required type="number" min={d.min} max={d.max} step="1" value={ratings[`${side}:${d.id}`] ?? ''} onChange={e => setRatings({ ...ratings, [`${side}:${d.id}`]: e.target.value })} /></label>)}</fieldset>)}
      {task === 'classification' && a.schema.labels.map(l => <label key={l.id}><input type="checkbox" checked={annotations.some(v => v.label_id === l.id)} onChange={e => setAnnotations(e.target.checked ? [...annotations, { label_id: l.id }] : annotations.filter(v => v.label_id !== l.id))} />{l.label}</label>)}
      {['text_spans', 'image_polygons'].includes(task) && <label>Annotation label<select value={label} onChange={e => setLabel(e.target.value)}>{a.schema.labels.map(l => <option key={l.id} value={l.id}>{l.label}</option>)}</select></label>}
      {task === 'text_spans' && <><label>Select original text (Shift + arrows also works)<textarea ref={text} readOnly value={a.source.text} dir="auto" rows="6" /></label><button type="button" onClick={() => { try { add(selectedSpan(a.source.text, text.current.selectionStart, text.current.selectionEnd, label)); } catch(e) { setError(e.message); } }}>Add selected passage</button></>}
      {task === 'image_polygons' && <><p>Click the image to add vertices, or enter normalized X/Y below using the keyboard. Letterbox clicks are ignored. Vertices follow your insertion order.</p>{image && <img src={image} alt="Source image for annotation" style={{ width: '100%', height: 360, objectFit: 'contain' }} onClick={e => { const p = normalizedPoint(e.currentTarget.getBoundingClientRect(), e.currentTarget.naturalWidth, e.currentTarget.naturalHeight, e.clientX, e.clientY); if (p) vertex(p.x, p.y); }} />}
        <label>X (0–1)<input type="number" min="0" max="1" step="any" value={x} onChange={e => setX(e.target.value)} /></label><label>Y (0–1)<input type="number" min="0" max="1" step="any" value={y} onChange={e => setY(e.target.value)} /></label><button type="button" onClick={() => x !== '' && y !== '' && vertex(Number(x), Number(y))}>Add vertex</button><ol aria-label="Polygon vertices">{polygon.map((p, i) => <li key={i}>{p.join(', ')}</li>)}</ol><button type="button" onClick={() => setPolygon(polygon.slice(0, -1))}>Undo vertex</button><button type="button" disabled={!image || polygon.length < 3} onClick={() => { add({ label_id: label, polygon }); setPolygon([]); }}>Add polygon</button></>}
      {task.startsWith('image_') || task === 'text_spans' ? <ol>{annotations.map((v, i) => <li key={i}>{v.label_id}: {v.polygon ? `${v.polygon.length} vertices` : `code points ${v.start}–${v.end}: ${Array.from(a.source.text).slice(v.start, v.end).join('')}`} <button type="button" onClick={() => setAnnotations(annotations.filter((_, j) => i !== j))}>Remove annotation {i + 1}</button></li>)}</ol> : null}
      {task.includes('_spans') || task.includes('_polygons') || task === 'classification' ? <p>{annotations.length} annotations. Required: {a.schema.min_annotations}–{a.schema.max_annotations}. Overlap {a.schema.allow_overlap ? 'allowed' : 'not allowed'}; server validates geometry.</p> : null}
      <label>Reason<textarea required maxLength="20000" value={reason} onChange={e => setReason(e.target.value)} /></label><label>Reason language<input required value={language} maxLength="80" onChange={e => setLanguage(e.target.value)} /></label>
    </fieldset><button disabled={busy} type="submit">{pending ? 'Retry identical submission' : 'Submit review'}</button><p role="status">{busy ? 'Saving…' : pending ? 'Answer frozen pending acknowledgement.' : ''}</p>
  </form>;
}

export default function EvaluationRunner({ workspaceId, token, assignmentId }) {
  const [a, setA] = useState(null), [error, setError] = useState('');
  const request = React.useCallback((path = '', options = {}) => authenticatedRequest(`/api/v1/workspaces/${encodeURIComponent(workspaceId)}/evaluation/assignments/${encodeURIComponent(assignmentId)}`, token, path, options), [workspaceId, token, assignmentId]);
  const load = () => request().then(r => r.json()).then(setA).catch(() => setError('Assignment unavailable. Check your authorization.'));
  useEffect(() => { load(); }, [request]);
  return <main className="study-preview"><h1>Human evaluation</h1><p role="alert">{error}</p><button onClick={load}>Reload assignment state</button>{a && <EvaluationForm key={a.id + Boolean(a.outcome)} assignment={a} request={request} onSaved={load} />}</main>;
}