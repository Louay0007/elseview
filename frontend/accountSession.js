import { ApiError, createApiClient } from './apiClient.js';

// A refresh is single-flight, but a business command is never replayed automatically.
export function createAccountSession(login, { fetchImpl, now = Date.now, onExpired = () => {} } = {}) {
  let credentials = login, expiresAt = now() + login.expires_in * 1000;
  let closed = false, refreshing = null;
  const anonymous = createApiClient({ fetchImpl });
  function close() { closed = true; credentials = null; }
  function assertOpen() { if (closed) throw new ApiError('Sign in again to continue.', 401, 'SESSION_CLOSED'); }
  async function freshCredentials() {
    assertOpen();
    if (expiresAt - now() > 30000) return credentials;
    if (!refreshing) {
      refreshing = anonymous('/auth/refresh', { method: 'POST', csrfToken: credentials.csrf_token })
        .then(result => { assertOpen(); credentials = result; expiresAt = now() + result.expires_in * 1000; return result; })
        .catch(error => { if (!closed) { close(); onExpired(); } throw error; })
        .finally(() => { refreshing = null; });
    }
    return refreshing;
  }
  async function request(path, options) {
    const current = await freshCredentials();
    assertOpen();
    try {
      const result = await createApiClient({ token: current.access_token, fetchImpl })(path, options);
      assertOpen();
      return result;
    } catch (error) {
      if (error.status === 401 && !closed) { close(); onExpired(); }
      throw error;
    }
  }
  async function logout() {
    try {
      const current = await freshCredentials();
      assertOpen();
      await createApiClient({ token: current.access_token, fetchImpl })('/auth/logout', { method: 'POST', csrfToken: current.csrf_token });
    } finally { close(); }
  }
  return { request, logout, close, familyId: login.family_id };
}

export function accountRoute(hash = '') {
  const path = hash.replace(/^#/, '');
  if (path === '/login-sessions') return { page: 'login-sessions' };
  if (path === '/participant/profile') return { page: 'participant-profile' };
  if (path === '/participant/assessments') return { page: 'assessments' };
  if (path === '/participant/history') return { page: 'participant-history' };
  if (['/sign-in', '/register', '/recover', '/verify', '/reset'].includes(path)) return { page: path.slice(1) };
  const assignment = /^\/workspaces\/([0-9a-f-]{36})\/assignments(?:\/([0-9a-f-]{36}))?$/i.exec(path);
  if (assignment) return { page: assignment[2] ? 'evaluation' : 'assignments', workspaceId: assignment[1], assignmentId: assignment[2] };
  const reports = /^\/workspaces\/([0-9a-f-]{36})\/reports$/i.exec(path);
  if (reports) return { page: 'reports', workspaceId: reports[1] };
  const schedule = /^\/workspaces\/([0-9a-f-]{36})\/schedule\/([0-9a-f-]{36})$/i.exec(path);
  if (schedule) return { page: 'schedule', workspaceId: schedule[1], versionId: schedule[2] };
  const match = /^\/workspaces\/([0-9a-f-]{36})(?:\/studies\/([0-9a-f-]{36}))?$/i.exec(path);
  if (match) return { page: match[2] ? 'study' : 'workspace', workspaceId: match[1], studyId: match[2] };
  return { page: 'workspaces' };
}
export function accountError(error) {
  if (error.status === 401) return 'You could not be signed in. Check your details, verify your email, or request a password reset.';
  if (error.status === 403) return 'This action is not available to your account. Check your email verification or ask the workspace owner for access.';
  if (error.status === 404) return 'This record is unavailable or your access has changed. Return to your workspaces.';
  if (error.status === 409) return 'The record changed or this request was already used. Reload the server record before continuing.';
  if (error.status === 422) return 'Check the form requirements and try again. Your entries have been kept.';
  if (error.status === 429) return 'Too many requests. Wait a few minutes before trying again.';
  return 'The server response was not confirmed. Check your connection and reload the server record before repeating an action.';
}
