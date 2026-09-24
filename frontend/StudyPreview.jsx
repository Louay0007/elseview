import React, { useEffect, useRef, useState } from 'react';
import './preview.css';
import { AdvancedMethods, ADVANCED_METHOD_TYPES } from './AdvancedMethods.jsx';

export const supportedMethods = ['survey.single', 'survey.multi', 'survey.rating', 'survey.text', 'preference', 'five_second', 'prototype.task', ...ADVANCED_METHOD_TYPES];

async function callPreview(token, path, options = {}) {
  const response = await fetch(`/api/v1/${path}`, { ...options, headers: { 'Content-Type': 'application/json', 'X-Preview-Token': token, ...options.headers }, cache: 'no-store' });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const failure = new Error(body.error?.message || 'Preview unavailable. Reopen a current preview link.');
    failure.status = response.status;
    throw failure;
  }
  return response;
}

function PrivateImage({ token, reference, label, hidden = false, onReady, onFailure, loadAsset }) {
  const [source, setSource] = useState(null);
  useEffect(() => {
    const controller = new AbortController();
    let objectUrl;
    (loadAsset ? loadAsset(reference) : callPreview(token, `study-preview/assets/${reference.asset_id}`, { signal: controller.signal }).then(response => response.blob()))
      .then(blob => {
        if (controller.signal.aborted) return;
        objectUrl = URL.createObjectURL(blob);
        setSource(objectUrl);
      })
      .catch(error => { if (error.name !== 'AbortError') onFailure(error.message); });
    return () => { controller.abort(); if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [token, reference.asset_id]);
  return source ? <img className="preview-image" src={source} alt={label} hidden={hidden} onLoad={onReady} onError={() => onFailure('This image could not be displayed.')} /> : <p role="status">Loading private image…</p>;
}

function Exposure({ block, token, onValue, onFailure, loadAsset }) {
  const [ready, setReady] = useState(false);
  const [phase, setPhase] = useState('ready');
  const started = useRef(null);
  const completed = useRef(false);
  const marker = `elseview-exposure-${block.attempt_id}`;
  useEffect(() => {
    if (sessionStorage.getItem(marker)) {
      completed.current = true;
      setPhase('interrupted');
      onValue({ attempt_id: block.attempt_id, visible_ms: 0, interrupted: true });
    }
  }, []);
  useEffect(() => {
    if (phase !== 'visible') return;
    let timer;
    const end = interrupted => {
      if (completed.current) return;
      completed.current = true;
      const elapsed = Math.round(performance.now() - started.current);
      onValue({ attempt_id: block.attempt_id, visible_ms: elapsed, interrupted });
      setPhase(interrupted ? 'interrupted' : 'finished');
    };
    const frame = requestAnimationFrame(() => {
      started.current = performance.now();
      timer = setTimeout(() => end(false), block.config.exposure_ms);
    });
    const visibility = () => { if (document.hidden && started.current !== null) end(true); };
    document.addEventListener('visibilitychange', visibility);
    return () => { cancelAnimationFrame(frame); clearTimeout(timer); document.removeEventListener('visibilitychange', visibility); };
  }, [phase]);
  return <section aria-label="Timed image exposure">
    <p lang="en">A visual stimulus will appear once for five seconds. Switching tabs interrupts the attempt. You may choose “Unable to answer” instead.</p>
    <PrivateImage loadAsset={loadAsset} token={token} reference={block.config.asset_ref} label="Timed study stimulus" hidden={phase !== 'visible'} onReady={() => setReady(true)} onFailure={onFailure} />
    {phase === 'ready' && <button type="button" disabled={!ready} onClick={() => { sessionStorage.setItem(marker, 'started'); setPhase('visible'); }}>Show image for five seconds</button>}
    <p role="status">{phase === 'visible' ? 'Viewing image…' : phase === 'finished' ? 'Exposure complete. Continue to recall questions.' : phase === 'interrupted' ? 'Exposure interrupted. It will not be counted as timing-valid.' : !ready ? 'Preparing image…' : ''}</p>
  </section>;
}

export function Question({ block, token, locale, onSubmit, busy, loadAsset, onEvent }) {
  const [choice, setChoice] = useState('');
  const [selected, setSelected] = useState([]);
  const [text, setText] = useState('');
  const [observed, setObserved] = useState(null);
  const [error, setError] = useState('');
  const [step, setStep] = useState(0);
  const [launched, setLaunched] = useState(false);
  const [loadedAssets, setLoadedAssets] = useState({});
  const assetReady = id => setLoadedAssets(previous => ({ ...previous, [id]: true }));
  const [reason, setReason] = useState('technical');
  const start = useRef(performance.now());
  const heading = useRef(null);
  useEffect(() => { heading.current?.focus(); }, []);
  const config = block.config;
  const submit = event => {
    event.preventDefault();
    setError('');
    if (block.type === 'preference' && config.variants.some(variant => !loadedAssets[variant.asset_ref.asset_id])) { setError('Wait for every image to load, or choose unable to answer.'); return; }
    if (block.type === 'prototype.task' && config.target.mode === 'asset_flow' && !loadedAssets[config.target.asset_refs[step].asset_id]) { setError('Wait for the prototype image, or choose unable to answer.'); return; }
    let value;
    if (ADVANCED_METHOD_TYPES.includes(block.type)) { if (!observed) { setError('Complete this task or choose unable to answer.'); return; } value = observed; }
    if (block.type === 'survey.single') value = { option_id: choice };
    if (block.type === 'survey.multi') {
      if (selected.length < config.min_selected || selected.length > config.max_selected) { setError(`Choose between ${config.min_selected} and ${config.max_selected} options.`); return; }
      value = { option_ids: selected };
    }
    if (block.type === 'survey.rating') value = { value: Number(choice) };
    if (block.type === 'survey.text') value = { text, language: locale };
    if (block.type === 'preference') value = { assignment_id: block.assignment_id, decision: choice === 'tie' || choice === 'none' ? choice : 'variant', selected_variant_id: choice === 'tie' || choice === 'none' ? null : choice, reason: { text, language: locale } };
    if (block.type === 'five_second') { if (!observed) { setError('Complete the exposure or choose unable to answer.'); return; } value = observed; }
    if (block.type === 'prototype.task') {
      if (config.target.mode === 'external_link' && !launched) { setError('Open the prototype before reporting your result, or choose unable to answer.'); return; }
      const elapsed = Math.min(Math.round(performance.now() - start.current), 3600000);
      value = { outcome: elapsed > config.time_limit_ms ? 'gave_up' : choice, elapsed_ms: elapsed, ...(elapsed > config.time_limit_ms ? { termination_reason: 'timeout' } : {}), ...(text.trim() ? { notes: { text, language: locale } } : {}) };
    }
    onSubmit({ status: 'responded', value });
  };
  return <section aria-labelledby="question-heading">
    <h2 id="question-heading" ref={heading} tabIndex={-1}>{block.prompt}</h2>
    <p lang="en">{block.required ? 'Required question' : 'Optional question'}</p>
    <form onSubmit={submit} aria-busy={busy}>
      <fieldset disabled={busy}>
        <legend className="visually-hidden">{block.prompt}</legend>
        {ADVANCED_METHOD_TYPES.includes(block.type) && <AdvancedMethods block={block} locale={locale} onValue={setObserved} onFailure={setError} onEvent={onEvent} loadAsset={loadAsset || (reference => callPreview(token, `study-preview/assets/${reference.asset_id}`).then(response => response.blob()))} />}
        {['survey.single', 'survey.multi'].includes(block.type) && config.options.map(option => <label className="choice" key={option.id}>
          <input type={block.type === 'survey.multi' ? 'checkbox' : 'radio'} name="choice" value={option.id} required={block.type === 'survey.single'} checked={block.type === 'survey.multi' ? selected.includes(option.id) : choice === option.id} onChange={() => block.type === 'survey.multi' ? setSelected(previous => previous.includes(option.id) ? previous.filter(key => key !== option.id) : [...previous, option.id]) : setChoice(option.id)} />{option.label}
        </label>)}
        {block.type === 'survey.rating' && <label className="field">{config.endpoint_labels.low} — {config.endpoint_labels.high}<input type="number" value={choice} min={config.min} max={config.max} step={config.step} onChange={event => setChoice(event.target.value)} required /></label>}
        {block.type === 'survey.text' && <label className="field">{block.prompt}<textarea value={text} minLength={config.min_length} maxLength={config.max_length} onChange={event => setText(event.target.value)} required /></label>}
        {block.type === 'preference' && <>
          <div className="variants">{config.variants.map(variant => <label className="choice variant" key={variant.id}>
            <PrivateImage loadAsset={loadAsset} token={token} reference={variant.asset_ref} label={variant.label} onReady={() => assetReady(variant.asset_ref.asset_id)} onFailure={setError} />
            <span><input type="radio" name="variant" value={variant.id} checked={choice === variant.id} onChange={() => setChoice(variant.id)} required />{variant.label}</span>
          </label>)}</div>
          {config.allow_tie && <label className="choice"><input type="radio" name="variant" checked={choice === 'tie'} onChange={() => setChoice('tie')} />Equal preference</label>}
          {config.allow_none && <label className="choice"><input type="radio" name="variant" checked={choice === 'none'} onChange={() => setChoice('none')} />Neither option</label>}
          <label className="field">Why do you prefer this option?<textarea value={text} maxLength={10000} onChange={event => setText(event.target.value)} required /></label>
        </>}
        {block.type === 'five_second' && <Exposure block={block} token={token} onValue={setObserved} onFailure={setError} />}
        {block.type === 'prototype.task' && <>
          <p lang="en">Completion is self-reported; Elseview does not observe activity on external sites.</p>
          {config.target.mode === 'external_link' ? <a className="button" href={config.target.url} target="_blank" rel="noopener noreferrer" onClick={() => { setLaunched(true); start.current = performance.now(); }}>Open prototype in a new tab</a> : <>
            <PrivateImage loadAsset={loadAsset} token={token} reference={config.target.asset_refs[step]} label={`Prototype step ${step + 1}`} onReady={() => assetReady(config.target.asset_refs[step].asset_id)} onFailure={setError} />
            <div className="actions"><button type="button" disabled={step === 0} onClick={() => setStep(step - 1)}>Previous image</button><span>Image {step + 1} of {config.target.asset_refs.length}</span><button type="button" disabled={step + 1 === config.target.asset_refs.length} onClick={() => setStep(step + 1)}>Next image</button></div>
          </>}
          <label className="field">Task outcome<select value={choice} onChange={event => setChoice(event.target.value)} required><option value="">Choose an outcome</option><option value="completed">Completed</option><option value="failed">Could not complete</option><option value="gave_up">Stopped trying</option></select></label>
          <label className="field">Optional notes<textarea value={text} maxLength={10000} onChange={event => setText(event.target.value)} /></label>
        </>}
        <p id="local-error" role="alert">{error}</p>
        <div className="actions"><button type="submit">{busy ? 'Checking…' : 'Continue'}</button>{!block.required && <button type="button" onClick={() => onSubmit({ status: 'skipped', value: null })}>Skip</button>}</div>
        <details><summary>Unable to answer</summary><p lang="en">No personal or medical explanation is required. This ends this preview path without claiming completion.</p><label className="field">Reason<select value={reason} onChange={event => setReason(event.target.value)}><option value="technical">Technical issue</option><option value="accessibility">Accessibility barrier</option><option value="declined">Prefer not to answer</option><option value="other">Other</option></select></label><button type="button" onClick={() => onSubmit({ status: 'unable', value: null, reason_code: reason })}>Record inability</button></details>
      </fieldset>
    </form>
  </section>;
}

export default function StudyPreview({ token }) {
  const [state, setState] = useState(null);
  const [answers, setAnswers] = useState({});
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [locale, setLocale] = useState('fr');
  const load = async nextAnswers => {
    setBusy(true); setError('');
    try {
      const response = await callPreview(token, 'study-preview', { method: 'POST', body: JSON.stringify({ answers: nextAnswers }) });
      const result = await response.json();
      setState(result); setAnswers(nextAnswers); setLocale(result.locale);
    } catch (failure) { setError(failure.message); if ([401, 403, 404].includes(failure.status)) setState(null); }
    finally { setBusy(false); }
  };
  useEffect(() => { load({}); }, [token]);
  return <main className="study-preview" lang={locale} dir={locale?.startsWith('ar') ? 'rtl' : 'ltr'}>
    <header lang="en" dir="ltr"><p className="eyebrow">Elseview · See what you’re missing.</p><h1>Study preview</h1><p className="preview-notice">Test-only session. Preview answers are checked by the server but never saved as research data. No recruitment, reports, rewards or AI calls are created.</p></header>
    <p role="alert">{error}</p>
    {error && <button type="button" onClick={() => load(answers)}>Retry last saved preview step</button>}
    {!state && !error && <p role="status">Opening private preview…</p>}
    {state?.consent && <details><summary lang="en">Study consent — preview only</summary><p style={{ whiteSpace: 'pre-wrap' }}>{state.consent.body}</p></details>}
    {state?.block && <Question key={state.block.block_key} block={state.block} token={token} locale={locale} busy={busy} onSubmit={answer => load({ ...answers, [state.block.block_key]: answer })} />}
    {state?.complete && <section role="status" lang="en"><h2>{state.incomplete ? 'Preview stopped' : 'Preview complete'}</h2><p>{state.answered} preview answers checked. Nothing was added to study results.</p></section>}
  </main>;
}
