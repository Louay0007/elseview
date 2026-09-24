import { test } from 'node:test';
import assert from 'node:assert/strict';
import { codePointOffset, selectedSpan } from './researchHelpers.js';
test('Unicode offsets retain emoji, combining marks and RTL original', () => {
  const text = 'A😀e\u0301ع';
  assert.equal(codePointOffset(text, 3), 2);
  assert.deepEqual(selectedSpan(text, 1, 5, 'quote'), { label_id: 'quote', start: 1, end: 4 });
  assert.equal(codePointOffset(text, text.length), 5);
});
test('invalid and split-surrogate selections rejected', () => {
  for (const offset of [-1, 1.5, 4, 1]) assert.throws(() => codePointOffset('😀', offset));
  assert.throws(() => selectedSpan('abc', 2, 2, 'x'));
});