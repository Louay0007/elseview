import React, { useEffect, useRef, useState } from 'react';

// Uses the study-preview typography, spacing, colors and controls without changing preview behavior.
export default function TimedCollectionExposure({ block, versionId, request, onEvent, onSubmit, busy, onRecover, stopRequested = false }) {
  const initial = block.attempt_state === 'not_started' ? 'idle' : 'recovered';
  const [phase, setPhase] = useState(initial), [error, setError] = useState('');
  const [reason, setReason] = useState('technical'), [saving, setSaving] = useState(false);
  const image = useRef(null), heading = useRef(null), live = useRef(true);
  const data = useRef({ phase: initial, url: null, attempt: null, start: null, timer: null, deadline: null, result: null });
  const callbacks = useRef({ request, onEvent });
  callbacks.current = { request, onEvent };
  const change = value => { data.current.phase = value; if (live.current) setPhase(value); };
  function conceal() {
    if (image.current) { image.current.hidden = true; image.current.removeAttribute('src'); }
    if (data.current.url) URL.revokeObjectURL(data.current.url);
    data.current.url = null;
    clearTimeout(data.current.timer); clearTimeout(data.current.deadline);
  }
  async function persistResult() {
    const result = data.current.result;
    if (!result) return;
    setSaving(true); setError('');
    try {
      await callbacks.current.onEvent(result.interrupted ? 'exposure.interrupted' : 'exposure.ended', { attempt_id: result.attempt_id }, result.visible_ms);
      if (live.current) change(result.interrupted ? 'interrupted' : 'completed');
    } catch {
      if (live.current) { change('save_failed'); setError('The image is concealed. Retry saving this same timing result, or recover the session without replaying it.'); }
    } finally { if (live.current) setSaving(false); }
  }
  function finish(interrupted) {
    if (!['preparing', 'ready', 'starting', 'visible'].includes(data.current.phase)) return;
    const elapsed = data.current.start === null ? 0 : Math.min(3600000, Math.max(0, Math.round(performance.now() - data.current.start)));
    conceal();
    change('saving');
    if (!data.current.attempt) { change('uncertain'); return; }
    // Late timers are observations of interruption, never silently rounded to five seconds.
    data.current.result = { attempt_id: data.current.attempt, visible_ms: elapsed, interrupted: interrupted || elapsed < 4900 || elapsed > 5250 };
    void persistResult();
  }
  useEffect(() => {
    live.current = true; heading.current?.focus();
    const hidden = () => { if (document.hidden) finish(true); };
    const exit = () => finish(true);
    document.addEventListener('visibilitychange', hidden); window.addEventListener('pagehide', exit);
    return () => { live.current = false; finish(true); conceal(); document.removeEventListener('visibilitychange', hidden); window.removeEventListener('pagehide', exit); };
  }, []);
  useEffect(() => { if (stopRequested) { finish(true); conceal(); } }, [stopRequested]);
  async function prepare() {
    if (data.current.phase !== 'idle' || document.hidden || stopRequested) return;
    change('preparing'); setError('');
    data.current.capability = Array.from(crypto.getRandomValues(new Uint8Array(32)), x => x.toString(16).padStart(2, '0')).join('');
    data.current.deadline = setTimeout(() => finish(true), 30000);
    try {
      const response = await request(`/attempts/${encodeURIComponent(block.block_key)}/prepare`, { method: 'POST', body: JSON.stringify({ protocol_version: 2, version_id: versionId, capability: data.current.capability }) });
      const receipt = await response.json();
      data.current.attempt = receipt.attempt_id;
      if (!live.current || data.current.phase !== 'preparing') return;
      if (!receipt.asset_ref || receipt.state !== 'preparing') throw new Error('Preparation is no longer available.');
      const blob = await (await request(`/assets/${encodeURIComponent(receipt.asset_ref.asset_id)}`, { headers: { 'X-Exposure-Token': data.current.capability } })).blob();
      if (!live.current || data.current.phase !== 'preparing') return;
      data.current.url = URL.createObjectURL(blob);
      image.current.src = data.current.url;
      await image.current.decode();
      if (!live.current || data.current.phase !== 'preparing') return;
      if (document.hidden) { finish(true); return; }
      change('ready');
    } catch {
      if (!live.current || !['preparing', 'ready'].includes(data.current.phase)) return;
      setError('The image could not be prepared. It cannot be loaded again for this attempt. Record inability or recover the session.');
      if (data.current.attempt) finish(true); else { conceal(); change('uncertain'); }
    }
  }
  async function show() {
    if (data.current.phase !== 'ready') return;
    if (document.hidden) { finish(true); return; }
    change('starting');
    try {
      const receipt = await (await request(`/attempts/${encodeURIComponent(block.block_key)}/start`, { method: 'POST', body: JSON.stringify({ protocol_version: 2, version_id: versionId, attempt_id: data.current.attempt, capability: data.current.capability }) })).json();
      if (!live.current || data.current.phase !== 'starting') return;
      if (receipt.replay || receipt.state !== 'started') throw new Error('Start acknowledgement is uncertain.');
      await callbacks.current.onEvent('exposure.started', { attempt_id: data.current.attempt }, 0);
      if (!live.current || data.current.phase !== 'starting') return;
      requestAnimationFrame(() => {
        if (!live.current || data.current.phase !== 'starting') return;
        if (document.hidden) { finish(true); return; }
        clearTimeout(data.current.deadline);
        image.current.hidden = false;
        data.current.start = performance.now();
        change('visible');
        data.current.timer = setTimeout(() => finish(false), 5000);
      });
    } catch {
      if (!live.current || data.current.phase !== 'starting') return;
      conceal(); change('uncertain');
      setError('The start was not acknowledged. The image will not be shown again. Recover the session to continue safely.');
    }
  }
  async function recover() {
    conceal(); setSaving(true);
    try { await onRecover(); change('recovered'); setError(''); }
    catch { setError('Recovery failed. Check your connection and retry recovery.'); }
    finally { setSaving(false); }
  }
  const recoveredResult = ['completed', 'interrupted'].includes(block.attempt_state) && Number.isInteger(block.visible_ms) ? { attempt_id: block.attempt_id, visible_ms: block.visible_ms, interrupted: block.attempt_state === 'interrupted' } : null;
  const knownResult = phase === 'recovered' ? recoveredResult : data.current.result;
  const canContinue = ['completed', 'interrupted', 'recovered'].includes(phase) && knownResult;
  const locked = busy || saving || ['preparing', 'starting', 'visible', 'saving'].includes(phase);
  const status = { unable: 'Image concealed. If saving failed, retry recording inability below.', idle: 'Prepare the image when you are ready.', preparing: 'Loading and decoding the private image…', ready: 'Image ready. Start within thirty seconds of preparation.', starting: 'Confirming your one-time exposure…', visible: 'Viewing image for five seconds…', saving: 'Image concealed. Saving timing…', completed: 'Exposure complete. Continue to the recall questions.', interrupted: 'Exposure interrupted. It will not count as timing-valid.', recovered: 'Previous attempt recovered. The image cannot be shown again. Unknown timing must be recorded as inability.', uncertain: 'Exposure status is uncertain. Recover before continuing.' }[phase] || '';
  return <section aria-labelledby="timed-heading">
    <h2 id="timed-heading" ref={heading} tabIndex={-1}>{block.prompt}</h2>
    <p>A visual image appears once for five seconds. Loading time is not viewing time. Switching tabs or leaving interrupts the attempt. If a timed visual task is not accessible to you, choose “Unable to answer”; no personal explanation is needed.</p>
    <p>Timing is observed by your browser, not physically verified.</p>
    <img ref={image} className="preview-image" hidden={phase !== 'visible'} alt="Timed study stimulus" />
    <p role="status" aria-live="polite">{status}</p><p role="alert">{error}</p>
    <div className="actions">
      {phase === 'idle' && <button disabled={busy} onClick={prepare}>Prepare image</button>}
      {phase === 'ready' && <button disabled={busy} onClick={show}>Show image for five seconds</button>}
      {canContinue && <button disabled={busy || saving} onClick={() => onSubmit({ status: 'responded', value: knownResult })}>Continue to recall questions</button>}
      {phase === 'save_failed' && <button disabled={saving} onClick={persistResult}>Retry saving timing</button>}
      {['uncertain', 'save_failed'].includes(phase) && <button disabled={saving} onClick={recover}>Recover session without replay</button>}
    </div>
    <details><summary>Unable to answer</summary><p>No personal or medical explanation is required.</p>
      <label className="field">Reason<select disabled={locked} value={reason} onChange={e => setReason(e.target.value)}><option value="technical">Technical issue</option><option value="accessibility">Accessibility barrier</option><option value="declined">Prefer not to answer</option><option value="other">Other</option></select></label>
      <button disabled={locked || ['uncertain', 'save_failed'].includes(phase)} onClick={() => { conceal(); change('unable'); onSubmit({ status: 'unable', value: null, reason_code: reason }); }}>Record inability</button>
      {['preparing', 'starting', 'visible'].includes(phase) && <button onClick={() => finish(true)}>Stop this attempt</button>}
    </details>
  </section>;
}
