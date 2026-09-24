import React from 'react';
import { createRoot } from 'react-dom/client';
import LongitudinalRunner from '../LongitudinalRunner.jsx';
const slot = { id: 'slot', version_id: 'v', starts_at: '2027-01-01T10:00:00Z', ends_at: '2027-01-01T11:00:00Z', timezone: 'Africa/Tunis' };
const request = async (path, options) => {
  if (options?.method) throw new Error('Fixture forbids submission');
  return Response.json(path.startsWith('/slots?') ? [slot] : path.startsWith('/bookings?') ? [{ id: 'booking', state: 'booked', revision: 1, attendance: null, slot }] : [{ id: 'occurrence', ordinal: 0, state: 'open', timezone: 'Africa/Tunis', opens_at: slot.starts_at, due_at: slot.ends_at, grace_at: slot.ends_at, session_id: null }]);
};
createRoot(document.getElementById('root')).render(<LongitudinalRunner workspaceId="w" versionId="v" token="fixture-only" request={request} />);
setTimeout(() => {
  const body = document.body.textContent;
  const ok = ['Book selected time', 'Confirm reschedule', 'Confirm cancellation', 'Start occurrence', 'Africa/Tunis', 'Attendance: unknown'].every(s => body.includes(s)) && document.querySelectorAll('form').length === 2;
  document.getElementById('result').textContent = ok ? 'PASS: booking/reschedule/cancel forms; diary start; IANA display; unknown attendance. No submissions.' : 'FAIL';
}, 1200);
