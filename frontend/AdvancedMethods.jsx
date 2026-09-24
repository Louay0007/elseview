import React, { useEffect, useRef, useState } from 'react';
import { containedRect, normalizedPoint, moveCursor } from './firstClickGeometry.js';
export const ADVANCED_METHOD_TYPES = ['survey.ranking', 'survey.constant_sum', 'first_click', 'card_sort', 'tree_test', 'accessibility.issue', 'language.review'];
const label = (value, locale) => typeof value === 'string' ? value : value?.[locale] || Object.values(value || {})[0] || '';

function FirstClick({ block, loadAsset, onValue, onEvent, onFailure }) {
  const c = block.config, image = useRef(null), frozen = useRef(block.first_click || null), start = useRef(null);
  const [src, setSrc] = useState(null), [ready, setReady] = useState(false), [saved, setSaved] = useState(!!block.first_click);
  const [cursor, setCursor] = useState({ x: .5, y: .5 }), [mode, setMode] = useState('pointer'), [box, setBox] = useState(null), [visible, setVisible] = useState(!document.hidden);
  const [pending, setPending] = useState(false);
  useEffect(() => {
    let live = true, url;
    loadAsset(c.asset_ref).then(blob => { if (live) { url = URL.createObjectURL(blob); setSrc(url); } }).catch(e => live && onFailure(e.message));
    if (block.first_click) onValue(block.first_click);
    const visibility = () => setVisible(!document.hidden);
    document.addEventListener('visibilitychange', visibility);
    return () => { live = false; if (url) URL.revokeObjectURL(url); document.removeEventListener('visibilitychange', visibility); };
  }, []);
  useEffect(() => {
    const update = () => { if (image.current) setBox(containedRect({ left: 0, top: 0, width: image.current.clientWidth, height: image.current.clientHeight }, c.asset_width, c.asset_height)); };
    const observer = new ResizeObserver(update); if (image.current) observer.observe(image.current);
    window.addEventListener('orientationchange', update); update();
    return () => { observer.disconnect(); window.removeEventListener('orientationchange', update); };
  }, [src, ready]);
  async function persist(value) {
    setPending(true);
    try { await onEvent('first_click.recorded', value, value.elapsed_ms); setSaved(true); onValue(value); }
    catch (e) { onFailure(e.message); } finally { setPending(false); }
  }
  function capture(point, input_mode) {
    if (!point || frozen.current || !ready || document.hidden || start.current === null) return;
    const value = { ...c.asset_ref, ...point, elapsed_ms: Math.min(3600000, Math.max(0, Math.round(performance.now() - start.current))), input_mode };
    frozen.current = value; persist(value);
  }
  return <section aria-label="First click task">
    <p>The first selection is final. Image margins are not selectable. Switching input mode does not select a point.</p>
    {c.input_modes.includes('keyboard_cursor') && <label className="field">Input mode<select value={mode} disabled={!!frozen.current} onChange={e => setMode(e.target.value)}><option value="pointer">Pointer</option><option value="keyboard_cursor">Keyboard cursor</option></select></label>}
    {!src && <p role="status">Loading private stimulus…</p>}
    <div className="first-click-stage">
      {src && <img ref={image} src={src} alt="Study stimulus; choose your first target" className="first-click-image" draggable={false} onLoad={e => {
        if (e.target.naturalWidth !== c.asset_width || e.target.naturalHeight !== c.asset_height) { onFailure('Stimulus dimensions do not match the published asset.'); return; }
        start.current = performance.now(); setReady(true);
      }} onError={() => onFailure('Stimulus unavailable.')} onPointerDown={e => { if (mode === 'pointer' && e.isPrimary && e.button === 0) capture(normalizedPoint(e.currentTarget.getBoundingClientRect(), c.asset_width, c.asset_height, e.clientX, e.clientY), 'pointer'); }} />}
      {mode === 'keyboard_cursor' && box && <span aria-hidden="true" className="spatial-cursor" style={{ left: box.left + cursor.x * box.width, top: box.top + cursor.y * box.height }}>+</span>}
    </div>
    {mode === 'keyboard_cursor' && <><p id="cursor-help">Use arrow keys to move 1%; Shift + arrow moves 10%. Enter or Space selects. Coordinates are measured from the image’s top-left.</p><button type="button" disabled={!ready || !visible || !!frozen.current} aria-describedby="cursor-help" onKeyDown={e => { if (e.key.startsWith('Arrow')) { e.preventDefault(); setCursor(p => moveCursor(p, e.key, e.shiftKey ? .1 : .01)); } }} onClick={() => capture(cursor, 'keyboard_cursor')}>Select cursor at {Math.round(cursor.x * 100)}%, {Math.round(cursor.y * 100)}%</button></>}
    <p role="status">{saved ? 'First selection recorded.' : pending ? 'Saving first selection…' : !visible ? 'Selection paused while hidden.' : ''}</p>
    {frozen.current && !saved && !pending && <button type="button" onClick={() => persist(frozen.current)}>Retry saving the same selection</button>}
  </section>;
}

// Transport is injected: preview uses a no-op event ACK; collection must ACK events before values become submittable.
export function AdvancedMethods({ block, locale = 'en', onValue, onFailure, loadAsset, onEvent = async () => {} }) {
  const c = block.config, t = value => label(value, locale);
  const [order, setOrder] = useState([]), [points, setPoints] = useState({}), [groups, setGroups] = useState(c.categories || []), [placements, setPlacements] = useState({}), [groupName, setGroupName] = useState('');
  const [path, setPath] = useState(c.root_id ? [c.root_id] : []), [issues, setIssues] = useState([]), [ratings, setRatings] = useState({}), [rewrite, setRewrite] = useState('');
  const started = useRef(performance.now());
  const text = value => ({ text: value, language: locale });
  function emitIssue(next, nextRatings = ratings, nextRewrite = rewrite) {
    setIssues(next);
    if (block.type === 'accessibility.issue') onValue(next.some(i => !i.description.text.trim() || (i.context && (!i.context.input_method.trim() || !i.context.assistive_technology.trim()))) ? null : { issues: next });
    else onValue(c.dimensions.some(d => nextRatings[d.id] === undefined || nextRatings[d.id] === '') || next.some(i => !i.quote || !c.source_text.includes(i.quote) || !i.explanation.text.trim()) ? null : { ratings: c.dimensions.map(d => ({ dimension_id: d.id, value: Number(nextRatings[d.id]) })), issues: next, ...(nextRewrite.trim() ? { rewrite: { text: nextRewrite, language: c.target_language } } : {}) });
  }
  useEffect(() => { if (block.type === 'accessibility.issue') onValue({ issues: [] }); }, []);
  if (block.type === 'first_click') return <FirstClick {...{ block, loadAsset, onValue, onEvent, onFailure }} />;
  if (block.type === 'survey.ranking') {
    const update = next => { setOrder(next); onValue(next.length === c.rank_count ? { ordered_option_ids: next } : null); };
    return <section><p>Rank {c.rank_count} options. Use the move buttons to change order.</p><ol>{order.map((id, i) => <li key={id}>{t(c.options.find(o => o.id === id).label)} <button type="button" disabled={!i} onClick={() => { const next = [...order]; [next[i-1], next[i]] = [next[i], next[i-1]]; update(next); }}>Move up {t(c.options.find(o => o.id === id).label)}</button><button type="button" disabled={i === order.length-1} onClick={() => { const next = [...order]; [next[i+1], next[i]] = [next[i], next[i+1]]; update(next); }}>Move down</button><button type="button" onClick={() => update(order.filter(x => x !== id))}>Remove</button></li>)}</ol>{c.options.filter(o => !order.includes(o.id)).map(o => <button type="button" key={o.id} disabled={order.length >= c.rank_count} onClick={() => update([...order, o.id])}>Rank {t(o.label)}</button>)}<p role="status">{order.length} of {c.rank_count} ranked</p></section>;
  }
  if (block.type === 'survey.constant_sum') return <section><p>Allocate exactly {c.total_points} points. Enter zero explicitly.</p>{c.options.map(o => <label className="field" key={o.id}>{t(o.label)}<input type="number" min="0" max={c.total_points} step="1" required value={points[o.id] ?? ''} onChange={e => { const next = { ...points, [o.id]: e.target.value }; setPoints(next); const values = c.options.map(o => next[o.id]); onValue(values.every(v => v !== undefined && v !== '' && Number.isInteger(Number(v)) && Number(v) >= 0) && values.reduce((a,v) => a + Number(v), 0) === c.total_points ? { allocations: c.options.map(o => ({ option_id: o.id, points: Number(next[o.id]) })) } : null); }} /></label>)}<p role="status">{c.total_points - Object.values(points).reduce((a,v) => a + Number(v), 0)} points remaining</p></section>;
  if (block.type === 'card_sort') return <section><p>Assign each card to a group using its dropdown.</p>{c.mode !== 'closed' && <div><label className="field">New group name<input value={groupName} maxLength={500} onChange={e => setGroupName(e.target.value)} /></label><button type="button" disabled={!groupName.trim()} onClick={() => { setGroups([...groups, { id: `group_${crypto.randomUUID()}`, label: groupName.trim(), custom: true }]); setGroupName(''); onValue(null); }}>Add group</button></div>}{c.cards.map(card => <label className="field" key={card.id}>{t(card.label)}<select value={placements[card.id] || ''} onChange={e => {
    const next = { ...placements, [card.id]: e.target.value }; setPlacements(next);
    const unplaced = c.cards.filter(card => !next[card.id]).map(card => card.id);
    onValue(!c.allow_unplaced && unplaced.length ? null : { groups: groups.map(g => ({ group_id: g.id, card_ids: c.cards.filter(card => next[card.id] === g.id).map(card => card.id), ...(g.custom ? { label: text(g.label) } : {}) })), unplaced_card_ids: unplaced });
    onEvent('card_sort.changed', { card_id: card.id, placed_count: c.cards.length - unplaced.length }).catch(e => onFailure(e.message));
  }}><option value="">Unplaced</option>{groups.map(g => <option key={g.id} value={g.id}>{t(g.label)}</option>)}</select></label>)}</section>;
  if (block.type === 'tree_test') {
    const node = c.nodes.find(n => n.id === path.at(-1));
    const visit = async id => { try { await onEvent('tree.node_visited', { node_id: id }); setPath([...path, id]); onValue(null); } catch(e) { onFailure(e.message); } };
    const finish = outcome => onValue({ visited_node_ids: path, selected_node_id: outcome === 'selected' ? node.id : null, outcome, elapsed_ms: Math.min(3600000, Math.round(performance.now() - started.current)) });
    return <section><p aria-live="polite">Current location: {t(node.label)}</p>{node.parent_id && <button type="button" onClick={() => visit(node.parent_id)}>Back to parent</button>}<ul>{c.nodes.filter(n => n.parent_id === node.id).map(n => <li key={n.id}><button type="button" onClick={() => visit(n.id)}>Open {t(n.label)}</button></li>)}</ul><button type="button" disabled={!node.selectable} onClick={() => finish('selected')}>Choose {t(node.label)}</button><button type="button" onClick={() => finish('gave_up')}>I cannot find it</button></section>;
  }
  if (block.type === 'accessibility.issue') return <section><p>Report barriers, not medical information. You can continue with no issues. Evidence uploads are not collected.</p>{issues.map((issue, i) => <fieldset key={i}><legend>Issue {i+1}</legend><label className="field">Description<textarea required maxLength={10000} value={issue.description.text} onChange={e => emitIssue(issues.map((v,j) => j === i ? { ...v, description: text(e.target.value) } : v))} /></label><label className="field">Impact<select value={issue.impact} onChange={e => emitIssue(issues.map((v,j) => j === i ? { ...v, impact: e.target.value } : v))}>{['blocked','difficult','minor'].map(v => <option key={v}>{v}</option>)}</select></label><label className="field">Optional criterion<select value={issue.criterion_ref || ''} onChange={e => emitIssue(issues.map((v,j) => { if (j !== i) return v; const { criterion_ref, ...rest } = v; return e.target.value ? { ...rest, criterion_ref: e.target.value } : rest; }))}><option value="">Not specified</option>{c.criterion_refs.map(v => <option key={v}>{v}</option>)}</select></label>{c.capture_context && block.context_consent_granted === true && <fieldset><legend>Optional consented interaction context</legend>{['input_method', 'assistive_technology'].map(field => <label className="field" key={field}>{field === 'input_method' ? 'Input method' : 'Assistive technology (no diagnosis)'}<input maxLength={128} required={!!issue.context} value={issue.context?.[field] || ''} onChange={e => emitIssue(issues.map((v,j) => { if (j !== i) return v; const context = { input_method: '', assistive_technology: '', ...v.context, [field]: e.target.value }; const { context: old, ...rest } = v; return Object.values(context).some(Boolean) ? { ...rest, context } : rest; }))} /></label>)}</fieldset>}<button type="button" onClick={() => emitIssue(issues.filter((_,j) => i !== j))}>Remove issue</button></fieldset>)}<button type="button" onClick={() => emitIssue([...issues, { description: text(''), impact: 'difficult' }])}>Add issue</button></section>;
  if (block.type === 'language.review') return <section><h3>Source text</h3><p className="source-text" lang={c.source_language} dir="auto">{c.source_text}</p>{c.dimensions.map(d => <label key={d.id} className="field">{d.id} ({d.min}–{d.max})<input type="number" required min={d.min} max={d.max} step="1" value={ratings[d.id] ?? ''} onChange={e => { const next = { ...ratings, [d.id]: e.target.value }; setRatings(next); emitIssue(issues, next); }} /></label>)}{issues.map((issue,i) => <fieldset key={i}><legend>Language issue {i+1}</legend><label className="field">Exact source quote<textarea required value={issue.quote} onChange={e => emitIssue(issues.map((v,j) => j === i ? { ...v, quote: e.target.value } : v))} /></label>{issue.quote && !c.source_text.includes(issue.quote) && <p role="alert">Quote must occur exactly in the source.</p>}<label className="field">Explanation<textarea required maxLength={10000} value={issue.explanation.text} onChange={e => emitIssue(issues.map((v,j) => j === i ? { ...v, explanation: text(e.target.value) } : v))} /></label><button type="button" onClick={() => emitIssue(issues.filter((_,j) => i !== j))}>Remove issue</button></fieldset>)}<button type="button" onClick={() => emitIssue([...issues, { quote: '', explanation: text('') }])}>Add language issue</button><label className="field">Optional rewrite<textarea lang={c.target_language} dir="auto" maxLength={10000} value={rewrite} onChange={e => { setRewrite(e.target.value); emitIssue(issues, ratings, e.target.value); }} /></label></section>;
  return <p role="alert">Unsupported method.</p>;
}
