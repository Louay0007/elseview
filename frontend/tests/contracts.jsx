import React from 'react';
import { createRoot } from 'react-dom/client';
import ContractWorkbench from '../ContractWorkbench.jsx';
const uuid = '11111111-1111-4111-8111-111111111111';
const requests = [], answers = [];
let registrations = 0;
let answerSaved = false, submitted = false, studyAttempts = 0, aiReads = 0;
const json = (data, status = 200) => new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json' } });
const assert = (condition, message) => { if (!condition) throw new Error(message); };
const studyBodies = [];
window.fetch = async (url, options = {}) => {
  const method = options.method || 'GET', body = options.body ? JSON.parse(options.body) : null;
  requests.push({ url, method, body, headers: options.headers });
  if (url === '/api/v1/auth/register' && method === 'POST') { assert(body.password.length >= 12 && body.email === 'fixture@example.test', 'Registration contract'); if (++registrations === 1) return json({ error: { code: 'VALIDATION_ERROR', message: 'Synthetic validation rejection' }, request_id: 'fixture-register' }, 422); assert(body.display_name === 'Corrected fixture', 'Corrected registration payload'); return json({ message: 'If the request is eligible, instructions will be delivered.' }, 202); }
  const base = `/api/v1/workspaces/${uuid}`;
  if (url === `${base}/studies` && method === 'POST') {
    assert(options.headers.Authorization === 'Bearer fixture-token', 'Bearer auth');
    studyBodies.push({ body, key: options.headers['Idempotency-Key'] });
    if (++studyAttempts === 1) throw new TypeError('Synthetic lost response');
    assert(JSON.stringify(studyBodies[0]) === JSON.stringify(studyBodies[1]), 'Study retry changed payload/key');
    return json({ study_id: uuid, version_id: uuid, revision: 1 }, 201);
  }
  if (url === `${base}/reviews/assignments/${uuid}/decision` && method === 'POST') { assert(body.verdict === 'accepted' && body.command_key && body.evidence.length === 0, 'Decision contract'); return json({ id: uuid, state: 'accepted', generation: 1 }); }
  if (url === `${base}/analytics/reports/${uuid}` && method === 'GET') return json({ id: uuid, version_id: uuid, revision: 1, state: 'draft', snapshot_id: uuid, metrics: {} });
  if (url === `${base}/ai/runs` && method === 'POST') { assert(body.operation === 'study_helper' && body.command_key && !body.researcher_text_approved, 'AI contract'); return json({ id: uuid, job_id: uuid, operation: 'study_helper', state: 'queued', draft: null, coverage: {}, charge_state: null, reserved_cost: null, actual_cost: null, currency: 'USD' }, 202); }
  if (url === `${base}/ai/runs/${uuid}` && method === 'GET') {
    if (++aiReads === 1) return json({ error: { code: 'UNAVAILABLE', message: 'Synthetic AI status interruption' }, request_id: 'fixture-ai' }, 503);
    return json({ id: uuid, state: 'draft', draft: { findings: [], limitations: ['Synthetic fixture'], insufficient_evidence: true } });
  }
  const collection = `/api/v1/collection/sessions/${uuid}`;
  if (url.startsWith(collection)) assert(options.headers['X-Session-Token'] === 'participant-fixture', 'Participant token');
  if (url === collection && method === 'GET') return json({ version_id: uuid, last_sequence: -1, revision: answerSaved ? 2 : 1, state: submitted ? 'submitted' : 'active', answers: {}, complete: answerSaved, submitted_at: submitted ? '2026-01-01T00:00:00Z' : null, block: answerSaved ? null : { block_key: 'question', type: 'survey.text', prompt: 'Describe this synthetic experience', required: true, config: { min_length: 1, max_length: 100 } } });
  if (url === `${collection}/answers/question` && method === 'PUT') {
    answers.push(body);
    assert(body.schema_version === 1 && body.expected_revision === 0 && body.occurrence === 0 && body.version_id === uuid && body.client_event_id && body.status === 'responded' && body.value.text === 'Synthetic response' && body.value.language === 'en', 'Canonical answer envelope');
    answerSaved = true;
    if (answers.length === 1) throw new TypeError('Synthetic response lost after save');
    assert(JSON.stringify(answers[0]) === JSON.stringify(body), 'Autosave retry changed envelope');
    return json({ revision: 1 });
  }
  if (url === `${collection}/submit` && method === 'POST') { assert(body.version_id === uuid && body.expected_revision === 2, 'Submission revision'); submitted = true; return json({ state: 'submitted' }); }
  throw new Error(`Unexpected mock request: ${method} ${url}`);
};
createRoot(document.getElementById('root')).render(<ContractWorkbench workspaceId={uuid} token="fixture-token" sessionId={uuid} sessionToken="participant-fixture" initial={{ registration: { display_name: 'Fixture', email: 'fixture@example.test', password: 'synthetic-password' }, study: { title: 'Synthetic study', retention_policy_id: uuid }, review: { assignment_id: uuid, rationale: 'Synthetic evidence checked' }, report: { report_id: uuid }, ai: { study_id: uuid } }} />);
const wait = async predicate => { for (let i = 0; i < 150; i++) { if (predicate()) return; await new Promise(resolve => setTimeout(resolve, 20)); } throw new Error('Timed out waiting for fixture state'); };
const section = title => document.querySelector(`section[aria-label="${title}"]`);
const click = (scope, text) => { const button = [...scope.querySelectorAll('button')].find(node => node.textContent === text); assert(button && !button.disabled, `Missing enabled ${text}`); button.click(); };
(async () => {
  try {
    await wait(() => section('Registration'));
    click(section('Registration'), 'Register'); await wait(() => section('Registration').textContent.includes('Synthetic validation rejection'));
    const name = section('Registration').querySelector('input[name="display_name"]');
    assert(!name.closest('fieldset').disabled, '422 must release inputs for correction');
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(name, 'Corrected fixture'); name.dispatchEvent(new Event('input', { bubbles: true }));
    await new Promise(resolve => setTimeout(resolve, 30));
    click(section('Registration'), 'Register'); await wait(() => section('Registration').textContent.includes('instructions will be delivered'));
    click(section('Create study'), 'Create study'); await wait(() => section('Create study').textContent.includes('Network unavailable'));
    click(section('Create study'), 'Retry same command'); await wait(() => section('Create study').textContent.includes('version_id'));
    click(section('Review'), 'Accept assignment'); await wait(() => section('Review').textContent.includes('"accepted"'));
    click(section('Report'), 'Load report'); await wait(() => section('Report').textContent.includes('snapshot_id'));
    click(section('Report'), 'Reload server record'); await wait(() => requests.filter(r => r.url.includes('/analytics/reports/')).length === 2);
    click(section('AI request'), 'Queue AI draft'); await wait(() => section('AI status').textContent.includes('AI state: queued'));
    click(section('AI status'), 'Refresh AI status'); await wait(() => section('AI status').textContent.includes('Synthetic AI status interruption'));
    click(section('AI status'), 'Refresh AI status'); await wait(() => section('AI status').textContent.includes('AI state: draft'));
    click(section('Participant'), 'Open participant session'); await wait(() => section('Participant').querySelector('textarea'));
    const textarea = section('Participant').querySelector('textarea');
    Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set.call(textarea, 'Synthetic response'); textarea.dispatchEvent(new Event('input', { bubbles: true }));
    await new Promise(resolve => setTimeout(resolve, 30));
    click(section('Participant'), 'Continue'); await wait(() => section('Participant').textContent.includes('Synthetic response lost'));
    click(section('Participant'), 'Continue'); await wait(() => section('Participant').textContent.includes('Submit completed study'));
    click(section('Participant'), 'Submit completed study'); await wait(() => section('Participant').textContent.includes('Study submitted.'));
    click(section('Participant'), 'Close participant session'); await wait(() => !section('Participant').querySelector('main'));
    click(section('Participant'), 'Open participant session'); await wait(() => section('Participant').textContent.includes('Study submitted.'));
    assert(answers.length === 2, 'Unexpected answer mutation on reload');
    assert([...document.querySelectorAll('input')].every(input => input.closest('label')), 'Inputs require labels');
    document.getElementById('fixture-result').textContent = `PASS: registration 422 correction, study retry, review, report reload, async AI error/retry, canonical collection autosave retry, submission and remount recovery (${requests.length} mocked requests). No DB/E2E claims.`;
  } catch (error) { document.getElementById('fixture-result').textContent = `FAIL: ${error.message}`; }
})();
