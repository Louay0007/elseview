export function codePointOffset(text, utf16Offset) {
  if (!Number.isInteger(utf16Offset) || utf16Offset < 0 || utf16Offset > text.length) throw new Error('Invalid text offset.');
  if (utf16Offset > 0 && utf16Offset < text.length && /[\uD800-\uDBFF]/.test(text[utf16Offset - 1]) && /[\uDC00-\uDFFF]/.test(text[utf16Offset])) throw new Error('Selection splits a Unicode character.');
  return Array.from(text.slice(0, utf16Offset)).length;
}
export function selectedSpan(text, start, end, label_id) {
  const span = { label_id, start: codePointOffset(text, start), end: codePointOffset(text, end) };
  if (span.start >= span.end) throw new Error('Select a nonempty passage.');
  return span;
}
export async function authenticatedRequest(base, token, path = '', options = {}) {
  const response = await fetch(base + path, { ...options, cache: 'no-store', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` } });
  if (!response.ok) { const error = new Error(`Request failed (${response.status}). Check authorization or refresh server state before retrying.`); error.status = response.status; throw error; }
  return response;
}