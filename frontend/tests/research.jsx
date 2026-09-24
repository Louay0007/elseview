import React from 'react';
import { createRoot } from 'react-dom/client';
import { EvaluationForm } from '../EvaluationRunner.jsx';
const rights = { owner: 'Synthetic fixture', compensation_terms: 'Not a real assignment', label_license: 'Test', reuse_permission: false, training_permission: false, consent_scope: 'Local fixture only' };
const tasks = ['classification', 'text_spans', 'image_polygons', 'pairwise', 'language_review'];
const fixture = task => ({ id: task, rights, schema: { task, instructions: 'Synthetic renderer test; no human record is submitted.', instructions_version: 'v1', labels: [{ id: 'label', label: 'Example label' }], dimensions: [{ id: 'quality', min: 1, max: 5 }], min_annotations: 0, max_annotations: 5, allow_overlap: false, language_basis: 'Read original English', rubric_version: 'v1' }, source: { text: 'A😀éع', language: 'en', testcase: 'Synthetic case', candidates: [{ id: 'left', text: 'Synthetic left' }, { id: 'right', text: 'Synthetic right' }] } });
const request = async path => { if (path !== '/image') throw new Error('Fixture forbids submissions'); return new Response(new Blob(['<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><rect width="100" height="100" fill="gray"/></svg>'], { type: 'image/svg+xml' })); };
createRoot(document.getElementById('root')).render(<main><h1>Research renderer smoke (synthetic only)</h1><p id="result" role="status">Running…</p>{tasks.map(task => <section id={task} key={task}><h2>{task}</h2><EvaluationForm assignment={fixture(task)} request={request} onSaved={() => { throw new Error('Never submit fixture'); }} /></section>)}</main>);
setTimeout(() => {
  try {
    if (document.querySelectorAll('form').length !== 5) throw new Error('Missing forms');
    const span = document.querySelector('#text_spans textarea'); span.focus(); span.setSelectionRange(1, 3);
    [...document.querySelectorAll('#text_spans button')].find(b => b.textContent === 'Add selected passage').click();
    const cannot = document.querySelector('#pairwise input[value="cannot_judge"]'); cannot.click();
    setTimeout(() => {
      try {
        if (!document.querySelector('#text_spans').textContent.includes('code points 1–2: 😀')) throw new Error('Unicode selection');
        if (document.querySelectorAll('#pairwise input[type="number"]').length) throw new Error('Cannot judge rubric');
        if (!document.querySelector('#image_polygons img')?.complete) throw new Error('Private image');
        document.getElementById('result').textContent = 'PASS: five real forms; Unicode selection; cannot-judge rubric exclusion; private blob image. No submissions sent.';
      } catch(e) { document.getElementById('result').textContent = 'FAIL: ' + e.message; }
    }, 100);
  } catch(e) { document.getElementById('result').textContent = 'FAIL: ' + e.message; }
}, 1200);