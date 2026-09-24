// Transport only: no business rules, automatic mutation replay, or persisted credentials.
export class ApiError extends Error {
  constructor(message, status = 0, code = 'NETWORK_ERROR') { super(message); this.status = status; this.code = code; }
}
export function createApiClient({ token = '', fetchImpl = (...args) => fetch(...args) } = {}) {
  return async function request(path, { method = 'GET', body, idempotencyKey, signal } = {}) {
    const headers = { Accept: 'application/json' };
    if (token) headers.Authorization = `Bearer ${token}`;
    if (body !== undefined) headers['Content-Type'] = 'application/json';
    if (idempotencyKey) headers['Idempotency-Key'] = idempotencyKey;
    let response;
    try { response = await fetchImpl(`/api/v1${path}`, { method, headers, cache: 'no-store', credentials: 'same-origin', signal, ...(body !== undefined ? { body: JSON.stringify(body) } : {}) }); }
    catch (error) { if (error.name === 'AbortError') throw error; throw new ApiError('Network unavailable. Retry the same command or reload the server record.'); }
    if (response.status === 204) return null;
    const data = await response.json().catch(() => null);
    if (!response.ok) throw new ApiError(data?.error?.message || `Request failed (${response.status}).`, response.status, data?.error?.code || 'HTTP_ERROR');
    if (data === null) throw new ApiError('Server returned an unreadable response. Reload before issuing another command.', response.status, 'INVALID_RESPONSE');
    return data;
  };
}
