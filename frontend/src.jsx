import React from 'react';
import { createRoot } from 'react-dom/client';
import StudyPreview from './StudyPreview.jsx';
import CollectionRunner from './CollectionRunner.jsx';
import AccountApp from './AccountApp.jsx';

const previewToken = new URLSearchParams(location.hash.slice(1)).get('preview');
const sessionParams = new URLSearchParams(location.hash.slice(1));
const sessionId = sessionParams.get('session');
const sessionToken = sessionParams.get('session_token');
if (previewToken || sessionToken) history.replaceState(null, '', location.pathname + location.search);

createRoot(document.getElementById('root')).render(previewToken ? <StudyPreview token={previewToken} /> : sessionId && sessionToken ? <CollectionRunner sessionId={sessionId} token={sessionToken} locale={sessionParams.get('locale') || 'en'} /> : <AccountApp />);