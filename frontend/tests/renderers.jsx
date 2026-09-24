// Synthetic public fixtures only. Run through Vite; no API or participant data.
import React from 'react';
import { createRoot } from 'react-dom/client';
import { AdvancedMethods } from '../AdvancedMethods.jsx';
import '../preview.css';
const opts = [{ id: 'a', label: 'Alpha' }, { id: 'b', label: 'Beta' }];
const fixtures = [
 ['survey.ranking', { options: opts, rank_count: 2 }],
 ['survey.constant_sum', { options: opts, total_points: 100 }],
 ['card_sort', { mode: 'hybrid', cards: opts, categories: [{ id: 'g', label: 'Group' }], allow_unplaced: true }],
 ['tree_test', { root_id: 'root', nodes: [{ id: 'root', parent_id: null, label: 'Home', selectable: false }, { id: 'a', parent_id: 'root', label: 'Alpha', selectable: true }] }],
 ['accessibility.issue', { criterion_refs: [], capture_context: false }],
 ['language.review', { source_text: 'Hello world', source_language: 'en', target_language: 'fr', dimensions: [{ id: 'clarity', min: 1, max: 5 }] }],
 ['first_click', { asset_ref: { asset_id: 'public-fixture', asset_version: 1 }, asset_width: 800, asset_height: 400, input_modes: ['pointer','keyboard_cursor'] }],
];
window.results = {};
const blob = new Blob(['<svg xmlns="http://www.w3.org/2000/svg" width="800" height="400"><rect width="800" height="400" fill="lightblue"/><text x="350" y="200">Fixture</text></svg>'], { type: 'image/svg+xml' });
createRoot(document.getElementById('root')).render(<main className="study-preview"><h1>P11 synthetic renderer smoke</h1>{fixtures.map(([type, config]) => <section key={type} data-method={type}><h2>{type}</h2><AdvancedMethods block={{ type, config }} locale="en" onValue={v => { window.results[type] = v; }} onFailure={e => { document.body.dataset.error = e; }} onEvent={async () => {}} loadAsset={async () => blob} /></section>)}<output id="smoke" /></main>);
setTimeout(() => {
  const buttons = section => [...document.querySelector(`[data-method="${section}"]`).querySelectorAll('button')];
  buttons('survey.ranking').find(b => b.textContent === 'Rank Alpha').click();
  setTimeout(() => {
    buttons('survey.ranking').find(b => b.textContent === 'Rank Beta').click();
    buttons('accessibility.issue').find(b => b.textContent === 'Add issue').click();
    setTimeout(() => {
      const ok = window.results['survey.ranking']?.ordered_option_ids.join(',') === 'a,b' && document.querySelectorAll('[data-method="accessibility.issue"] textarea').length === 1 && document.querySelector('.first-click-image')?.naturalWidth === 800 && !document.body.dataset.error;
      document.querySelector('#smoke').textContent = ok ? 'PASS: seven renderers mounted; ranking interaction; issue editor; private-asset loading' : 'FAIL';
    }, 150);
  }, 150);
}, 1000);
