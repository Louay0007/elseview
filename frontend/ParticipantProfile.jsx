import React, { useEffect, useId, useMemo, useRef, useState } from 'react';
import './account.css';

const PROFILE = '/panel/profile';
const DEVICE_IDS = ['mobile', 'desktop', 'tablet'];
const targeted = attributes => ['country_id', 'city_id', 'experience'].some(key => attributes?.[key] != null);
const emptyDraft = () => ({ age: '', devices: [], languages: '', country: '', city: '', experience: {} });
const draftFrom = profile => {
  const a = profile?.attributes || {};
  return { age: a.age == null ? '' : String(a.age), devices: a.devices || [], languages: (a.languages || []).join('\n'), country: a.country_id || '', city: a.city_id || '', experience: { ...a.experience?.categories } };
};
const unknown = error => !error.status || error.status >= 500 || error.status === 408 || error.code === 'INVALID_RESPONSE';
function messageFor(error) {
  if ([401, 403].includes(error.status)) return 'Access to your private profile ended. Sign in again or check your account access.';
  if (error.code === 'CONSENT_DOCUMENT_MISMATCH') return 'The consent document changed. Reload the profile and documents, then read and agree again.';
  if (error.status === 422) return 'The profile was not accepted. Check age, language count, country/city identifiers and experience choices. Your entries have been kept.';
  if (error.status === 409) return 'The profile or consent changed. Reload the server profile before continuing.';
  if (error.status === 429) return 'Too many requests. Wait a few minutes before trying again.';
  return 'The server response was not confirmed. Check your connection and reload the server profile.';
}
function invalid() { throw Object.assign(new Error('Invalid response'), { code: 'INVALID_RESPONSE', status: 200 }); }
function profileData(value) {
  if (!value || !/^[0-9a-f-]{36}$/i.test(value.id) || !['active', 'paused', 'withdrawn'].includes(value.status) || !value.attributes || Array.isArray(value.attributes) || typeof value.attributes !== 'object') invalid();
  const a = value.attributes;
  if (a.age != null && (!Number.isInteger(a.age) || a.age < 18 || a.age > 120)) invalid();
  if (a.devices != null && (!Array.isArray(a.devices) || a.devices.length > 3 || a.devices.some(v => !DEVICE_IDS.includes(v)))) invalid();
  if (a.languages != null && (!Array.isArray(a.languages) || a.languages.length > 10 || a.languages.some(v => typeof v !== 'string'))) invalid();
  if (a.country_id != null && (typeof a.country_id !== 'string' || !/^[A-Z]{2}$/.test(a.country_id))) invalid();
  if (a.city_id != null && (typeof a.city_id !== 'string' || !/^geonames:[1-9][0-9]{0,9}$/.test(a.city_id) || !a.country_id)) invalid();
  if (a.experience != null && (a.experience.version !== '1' || !a.experience.categories || typeof a.experience.categories !== 'object' || Array.isArray(a.experience.categories) || Object.values(a.experience.categories).some(v => typeof v !== 'string'))) invalid();
  // Keep only editable attributes. In particular, never render or resend receipt provenance.
  return { id: value.id, status: value.status, attributes: Object.fromEntries(['age', 'devices', 'languages', 'country_id', 'city_id', 'experience'].filter(key => key in a).map(key => [key, a[key]])) };
}
function documentData(value, version) {
  if (!value || value.version !== version || typeof value.body !== 'string' || !/^[0-9a-f]{64}$/.test(value.digest)) invalid();
  return { version: value.version, body: value.body, digest: value.digest };
}
function vocabularyData(value) {
  if (!value || value.version !== '1' || value.public_targeting_consent_version !== '2' || !Array.isArray(value.country_ids) || !value.country_ids.length || value.country_ids.some(id => !/^[A-Z]{2}$/.test(id)) || !Array.isArray(value.experience_categories) || !value.experience_categories.length || !Array.isArray(value.experience_levels) || !value.experience_levels.length || [...value.experience_categories, ...value.experience_levels].some(id => typeof id !== 'string')) invalid();
  return { countries: value.country_ids, categories: value.experience_categories, levels: value.experience_levels };
}
const canonical = value => value == null ? null : Array.isArray(value) ? value.map(canonical) : typeof value === 'object' ? Object.fromEntries(Object.keys(value).sort().map(key => [key, canonical(value[key])])) : value;
function matchesIntent(profile, body) {
  if (body.decision === 'withdrawn') return profile?.status === 'withdrawn' && !Object.keys(profile.attributes).length;
  if (profile?.status !== 'active') return false;
  const defaults = { age: null, devices: [], languages: [], country_id: null, city_id: null, experience: null };
  return JSON.stringify(canonical({ ...defaults, ...profile.attributes })) === JSON.stringify(canonical({ ...defaults, ...body.attributes }));
}
const styles = `
.participant-profile.account-app { --pp-small:1rem; --pp-medium:1.25rem; --pp-large:1.563rem; --pp-radius:4px; --pp-target:44px; margin:0; padding:0; max-width:none; }
.participant-profile h2 { font-size:var(--pp-large); }
.participant-profile h3 { font-size:var(--pp-medium); }
.participant-profile section { margin-block:var(--space-xl); }
.participant-profile .pp-layout { display:grid; grid-template-columns:minmax(0,2fr) minmax(0,1fr); gap:var(--space-xl); align-items:start; }
.participant-profile button { border-radius:var(--pp-radius); }
.participant-profile button:not(:disabled):hover { text-decoration:underline; }
.participant-profile button:not(:disabled):active { border-color:var(--color-text); }
.participant-profile button:disabled { opacity:1; color:var(--color-muted); background:var(--color-subtle); cursor:not-allowed; }
.participant-profile label:has(input[type=checkbox]) { display:flex; align-items:center; gap:var(--space-m); min-height:var(--pp-target); }
.participant-profile input[type=checkbox] { width:var(--pp-target); min-width:var(--pp-target); height:var(--pp-target); margin:0; accent-color:var(--color-action); }
.participant-profile .pp-document { white-space:pre-wrap; }
.participant-profile select { min-width:0; max-width:100%; }
@media(max-width:650px) { .participant-profile .pp-layout { grid-template-columns:minmax(0,1fr); gap:var(--space-l); } }
@media(prefers-reduced-motion:reduce) { .participant-profile * { animation:none; transition:none; scroll-behavior:auto; } }
`;

// The parent owns navigation and memory-session authentication; neither is persisted here.
export default function ParticipantProfile({ request, sessionKey = '' }) {
  const identity = useMemo(() => crypto.randomUUID(), [request, sessionKey]);
  return <ProfilePanel key={identity} request={request} />;
}
function ProfilePanel({ request }) {
  const id = useId(), alive = useRef(false), sequence = useRef(0), lock = useRef(false), controller = useRef(null), errorHeading = useRef(null);
  const [profile, setProfile] = useState(null), [draft, setDraft] = useState(emptyDraft);
  const [documents, setDocuments] = useState({}), [vocabulary, setVocabulary] = useState(null);
  const [loaded, setLoaded] = useState(false), [busy, setBusy] = useState(true), [slow, setSlow] = useState(false), [blocked, setBlocked] = useState(false);
  const [error, setError] = useState(''), [notice, setNotice] = useState(''), [fieldErrors, setFieldErrors] = useState({});
  const [agreed, setAgreed] = useState(false), [withdrawAgreed, setWithdrawAgreed] = useState(false), [showWithdrawal, setShowWithdrawal] = useState(false);
  const [pending, setPending] = useState(null), [reconciled, setReconciled] = useState(false), [mustReload, setMustReload] = useState(false);
  const targetDraft = !!(draft.country || draft.city || Object.values(draft.experience).some(Boolean));
  const doc = documents[targetDraft ? '2' : '1'];
  const withdrawalDoc = documents[targeted(profile?.attributes) ? '2' : '1'];
  const ready = loaded && !!doc && !!vocabulary;
  const disabled = busy || !!pending || mustReload;
  useEffect(() => { setAgreed(false); }, [doc?.digest]);
  useEffect(() => { setWithdrawAgreed(false); }, [withdrawalDoc?.digest]);
  useEffect(() => { if (!busy) { setSlow(false); return; } const timer = setTimeout(() => setSlow(true), 10000); return () => clearTimeout(timer); }, [busy]);
  function revokeAccess() {
    sequence.current++; controller.current?.abort(); setProfile(null); setDraft(emptyDraft()); setDocuments({}); setVocabulary(null); setPending(null); setLoaded(false); setAgreed(false); setWithdrawAgreed(false); setBlocked(true); setError('Access to your private profile ended. Sign in again or check your account access.'); setNotice('');
  }
  async function load({ replaceDraft = false, reconcile = false } = {}) {
    if (lock.current || blocked) return;
    lock.current = true; const current = ++sequence.current;
    controller.current?.abort(); controller.current = new AbortController();
    setBusy(true); setError('');
    const read = async (path, parse, missing = false) => {
      try { return parse(await request(path, { signal: controller.current.signal })); }
      catch (failure) {
        if (alive.current && sequence.current === current && [401, 403].includes(failure.status)) revokeAccess();
        if (missing && failure.status === 404) return null;
        throw failure;
      }
    };
    const results = await Promise.allSettled([
      read(PROFILE, profileData, true), read('/panel/consent?version=1', value => documentData(value, '1')),
      read('/panel/consent?version=2', value => documentData(value, '2')), read('/recruiting/targeting-vocabulary', vocabularyData),
    ]);
    if (!alive.current || current !== sequence.current) return;
    const [p, d1, d2, v] = results;
    if (p.status === 'fulfilled') {
      setProfile(p.value); setLoaded(true);
      if (replaceDraft || !loaded || !p.value || p.value.status !== profile?.status || p.value.id !== profile?.id) { setDraft(draftFrom(p.value)); setFieldErrors({}); setAgreed(false); setWithdrawAgreed(false); }
      if (loaded && p.value?.status !== profile?.status && !reconcile) setNotice('The server participation state changed. Review the current profile and give fresh consent before making another change.');
      if (reconcile && pending) {
        setReconciled(true);
        if (matchesIntent(p.value, pending.body)) {
          setPending(null); setReconciled(false); setDraft(draftFrom(p.value)); setAgreed(false); setShowWithdrawal(false); setWithdrawAgreed(false);
          setNotice('The server profile now matches your requested change. No request was replayed; this confirms the current profile, not delivery history.');
        } else setNotice('Server profile checked. It does not currently match the saved request. No request was replayed. You may explicitly retry the unchanged original request.');
      }
    } else if (reconcile) setReconciled(false);
    setDocuments({ ...(d1.status === 'fulfilled' ? { '1': d1.value } : {}), ...(d2.status === 'fulfilled' ? { '2': d2.value } : {}) });
    setVocabulary(v.status === 'fulfilled' ? v.value : null);
    const failed = results.find(result => result.status === 'rejected');
    setError(failed ? messageFor(failed.reason) : ''); setMustReload(!!failed); setBusy(false); lock.current = false;
  }
  useEffect(() => {
    alive.current = true; load({ replaceDraft: true });
    return () => { alive.current = false; sequence.current++; controller.current?.abort(); lock.current = false; };
  }, [request]);
  function attributes() {
    const languages = draft.languages.split('\n').map(value => value.trim()).filter(Boolean);
    const categories = Object.fromEntries(Object.entries(draft.experience).filter(([, value]) => value));
    const errors = {};
    if (draft.age && (!/^\d+$/.test(draft.age) || Number(draft.age) < 18 || Number(draft.age) > 120)) errors.age = 'Enter a whole age from 18 to 120, or leave it blank.';
    if (languages.length > 10) errors.languages = 'Use at most 10 language identifiers, one per line.';
    if (draft.country && !vocabulary.countries.includes(draft.country)) errors.country = 'Choose a country identifier from the current vocabulary.';
    if (draft.city && (!draft.country || !/^geonames:[1-9][0-9]{0,9}$/.test(draft.city))) errors.city = 'A city requires a country and geonames: followed by a positive ID of at most 10 digits.';
    if (Object.entries(categories).some(([key, value]) => !vocabulary.categories.includes(key) || !vocabulary.levels.includes(value))) errors.experience = 'Choose categories and levels from the current vocabulary.';
    setFieldErrors(errors);
    if (Object.keys(errors).length) { setError('Check the highlighted profile fields. Nothing was sent.'); setTimeout(() => errorHeading.current?.focus(), 0); return null; }
    return { age: draft.age ? Number(draft.age) : null, devices: draft.devices, languages, country_id: draft.country || null, city_id: draft.city || null, experience: Object.keys(categories).length ? { version: '1', categories } : null };
  }
  async function mutate(body) {
    if (lock.current || blocked) return;
    lock.current = true; setBusy(true); setError(''); setNotice(''); setReconciled(false);
    const saved = { body: JSON.parse(JSON.stringify(body)) }; setPending(saved);
    try {
      const result = profileData(await request(PROFILE, { method: 'PUT', body: JSON.parse(JSON.stringify(saved.body)) }));
      if (!alive.current) return;
      if (!matchesIntent(result, body)) invalid();
      setProfile(result); setLoaded(true); setDraft(draftFrom(result)); setPending(null); setAgreed(false); setWithdrawAgreed(false); setShowWithdrawal(false); setFieldErrors({});
      setNotice(body.decision === 'withdrawn' ? 'Public-panel participation withdrawn. Editable profile attributes were cleared.' : 'Public-panel profile and consent saved. Your details remain self-reported and unverified.');
    } catch (failure) {
      if (!alive.current) return;
      if ([401, 403].includes(failure.status)) { revokeAccess(); return; }
      setError(unknown(failure) ? 'The change has an unknown outcome. Other changes are locked. Check the server profile before deciding whether to retry.' : messageFor(failure));
      if (!unknown(failure)) { setPending(null); if (failure.status === 409) { setMustReload(true); setAgreed(false); setWithdrawAgreed(false); } }
    } finally { lock.current = false; if (alive.current) setBusy(false); }
  }
  function submit(event) {
    event.preventDefault(); if (disabled || !ready || !agreed) return;
    const values = attributes(); if (!values) return;
    mutate({ decision: 'granted', attributes: values, document_version: doc.version, presented_digest: doc.digest, receipt_key: crypto.randomUUID() });
  }
  const update = (key, value) => setDraft(previous => ({ ...previous, [key]: value }));
  const field = key => ({ 'aria-invalid': !!fieldErrors[key], 'aria-describedby': `${id}-${key}-help ${id}-${key}-error` });
  const savedDoc = pending && documents[pending.body.document_version];
  if (blocked) return <section className="participant-profile account-app"><h2>Public-panel profile</h2><p role="alert">{error}</p></section>;
  return <section className="participant-profile account-app" aria-labelledby={`${id}-title`}>
    <style>{styles}</style><h2 id={`${id}-title`}>Public-panel profile</h2>
    <p className="notice"><strong>Participation: {loaded ? profile?.status || 'not joined' : 'not yet confirmed'}.</strong> Joining is optional. This profile supports public research invitation matching; it is not a public directory or proof of qualifications.</p>
    <p role="status">{busy ? slow ? 'Still waiting for the server. Keep this page open; do not submit a replacement request.' : 'Loading or saving your profile…' : notice}</p>
    <p role="alert" tabIndex={-1} ref={errorHeading}>{error}</p>
    {pending && !busy && <div className="notice"><p>Your saved request remains in this page’s memory only. Nothing will be replayed automatically.</p><button onClick={() => load({ reconcile: true })}>Check server profile</button>{reconciled && savedDoc?.digest === pending.body.presented_digest && <button className="secondary" onClick={() => mutate(pending.body)}>Retry original request</button>}{reconciled && savedDoc && savedDoc.digest !== pending.body.presented_digest && <p>The consent document changed. The old request cannot be retried here. Reload this page to review the server profile and give fresh consent.</p>}</div>}
    <button className="secondary" disabled={busy || !!pending} onClick={() => load()}>Reload profile and documents</button>
    <p>Reload checks the server without overwriting unsaved fields. Leaving this page loses unsaved details and any pending request. After an uncertain outcome, reopen the server profile before making another change.</p>
    {loaded && !profile && <p>No public-panel profile exists yet. Read the consent document to join; all matching attributes are optional.</p>}
    {loaded && profile?.status === 'withdrawn' && <p>Your profile is withdrawn and its editable attributes are empty. Rejoining requires fresh consent and newly entered details; invitation availability is checked separately.</p>}
    {loaded && <div className="pp-layout"><div>
      <form onSubmit={submit}>
        <fieldset disabled={disabled || !ready}><legend>Self-reported matching attributes</legend>
          <p>Saving replaces these editable details. Blank optional values remain unknown. Country/city associations and experience are unverified; none of these fields establish assessed language ability or professional credentials.</p>
          <label>Age (optional)<input name="age" type="number" min="18" max="120" step="1" value={draft.age} onChange={event => update('age', event.target.value)} {...field('age')} /></label><p id={`${id}-age-help`}>Whole years, from 18 to 120.</p><p id={`${id}-age-error`} role="alert">{fieldErrors.age}</p>
          <fieldset><legend>Devices (optional)</legend>{DEVICE_IDS.map(device => <label key={device}><input name={`device-${device}`} type="checkbox" checked={draft.devices.includes(device)} onChange={event => update('devices', event.target.checked ? [...draft.devices, device] : draft.devices.filter(value => value !== device))} />{device}</label>)}</fieldset>
          <label>Language identifiers (optional)<textarea name="languages" rows="3" value={draft.languages} onChange={event => update('languages', event.target.value)} {...field('languages')} /></label><p id={`${id}-languages-help`}>At most 10, one per line. Use the identifiers you report, such as fr or en. Matching uses exact values; these are not verified qualifications.</p><p id={`${id}-languages-error`} role="alert">{fieldErrors.languages}</p>
          <label>Country identifier (optional)<select name="country" value={draft.country} onChange={event => update('country', event.target.value)} {...field('country')}><option value="">Unknown / not provided</option>{vocabulary?.countries.map(country => <option key={country} value={country}>{country}</option>)}</select></label><p id={`${id}-country-help`}>ISO country identifiers supplied by the server. No location is inferred from your device or language.</p><p id={`${id}-country-error`} role="alert">{fieldErrors.country}</p>
          <label>City identifier (optional)<input name="city" value={draft.city} onChange={event => update('city', event.target.value)} {...field('city')} /></label><p id={`${id}-city-help`}>Use geonames: followed by a positive ID of at most 10 digits, with a country selected. This form has no city lookup; leave it blank if unknown. The city/country association is self-reported, not verified.</p><p id={`${id}-city-error`} role="alert">{fieldErrors.city}</p>
          <fieldset aria-describedby={`${id}-experience-help ${id}-experience-error`}><legend>Experience, version 1 (optional)</legend><p id={`${id}-experience-help`}>Self-reported familiarity, not employment history, interests, certification or verified professional credentials. Leave a category unknown rather than guessing.</p>{vocabulary?.categories.map(category => <label key={category}>{category}<select name={`experience-${category}`} value={draft.experience[category] || ''} onChange={event => update('experience', { ...draft.experience, [category]: event.target.value })}><option value="">Unknown / not provided</option>{vocabulary.levels.map(level => <option key={level} value={level}>{level}</option>)}</select></label>)}<p id={`${id}-experience-error`} role="alert">{fieldErrors.experience}</p></fieldset>
        </fieldset>
        <fieldset disabled={disabled || !ready}><legend>Read and confirm panel consent</legend>
          {doc ? <><p>{targetDraft ? 'Country, city or experience requires targeting consent version 2.' : 'Basic public-panel attributes use consent version 1.'}</p><details><summary>Read panel consent · version {doc.version}</summary><p className="pp-document">{doc.body}</p></details><label><input name="panel-consent" type="checkbox" required checked={agreed} onChange={event => setAgreed(event.target.checked)} />I have read and agree to this panel consent document.</label></> : <p>The required consent document is unavailable. Reload before saving.</p>}
          <button>{!profile ? 'Join public panel' : profile.status === 'withdrawn' ? 'Rejoin public panel' : profile.status === 'paused' ? 'Resume panel participation' : 'Save profile and consent'}</button>
        </fieldset>
      </form>
      {profile && profile.status !== 'withdrawn' && <section aria-labelledby={`${id}-withdraw`}><h3 id={`${id}-withdraw`}>Withdraw from the public panel</h3><p>Withdrawal is not a temporary pause. It clears these editable profile attributes, stops new public-panel matching and cancels pending recruitment notifications. Linked public invitations or reservations may no longer be usable. It does not erase all retained study, consent or financial records. Private workspace contacts and assessment consent are separate.</p>
        {!showWithdrawal ? <button className="secondary" disabled={disabled || !withdrawalDoc} onClick={() => setShowWithdrawal(true)}>Review panel withdrawal</button> : <form onSubmit={event => { event.preventDefault(); if (!disabled && withdrawAgreed && withdrawalDoc) mutate({ decision: 'withdrawn', attributes: {}, document_version: withdrawalDoc.version, presented_digest: withdrawalDoc.digest, receipt_key: crypto.randomUUID() }); }}><fieldset disabled={disabled || !withdrawalDoc}><legend>Confirm source-affecting withdrawal</legend>{withdrawalDoc && <details><summary>Read withdrawal consent · version {withdrawalDoc.version}</summary><p className="pp-document">{withdrawalDoc.body}</p></details>}<label><input name="withdraw-consent" type="checkbox" required checked={withdrawAgreed} onChange={event => setWithdrawAgreed(event.target.checked)} />I have read the document and understand that withdrawal clears my profile attributes and can block linked public participation.</label><div className="actions"><button type="button" className="secondary" onClick={() => { setShowWithdrawal(false); setWithdrawAgreed(false); }}>Keep panel participation</button><button>Confirm panel withdrawal</button></div></fieldset></form>}
      </section>}
    </div><aside aria-labelledby={`${id}-limits`}><h3 id={`${id}-limits`}>Participation controls</h3><p>Pause is not available in the current profile API. Withdrawal is not a substitute for a reversible pause.</p><button disabled>Pause unavailable</button><p>Interests are not supported by the current profile schema. Do not enter them as experience or language qualifications.</p><p>Optional matching data may already be frozen in candidate snapshots. Editing or withdrawing this profile does not promise to erase those retained records.</p><p>No credentials or profile drafts are written to browser storage. Assessment consent and reviewed-language results are managed separately.</p></aside></div>}
  </section>;
}
