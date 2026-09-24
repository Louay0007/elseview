import test from 'node:test';
import assert from 'node:assert/strict';
import { containedRect, normalizedPoint, moveCursor } from './firstClickGeometry.js';
test('contain offsets and scroll viewport position', () => {
  const rect = { left: 10, top: 40, width: 400, height: 400 };
  assert.deepEqual(containedRect(rect, 800, 400), { left: 10, top: 140, width: 400, height: 200 });
  assert.equal(normalizedPoint(rect, 800, 400, 30, 100), null);
  assert.deepEqual(normalizedPoint(rect, 800, 400, 210, 240), { x: .5, y: .5 });
  assert.deepEqual(normalizedPoint(rect, 800, 400, 410, 340), { x: 1, y: 1 });
});
test('portrait resize recomputes bounds', () => {
  assert.deepEqual(containedRect({ left: 0, top: 0, width: 600, height: 300 }, 200, 400), { left: 225, top: 0, width: 150, height: 300 });
  assert.equal(normalizedPoint({ left: 0, top: 0, width: 0, height: 0 }, 20, 40, 0, 0), null);
  assert.equal(normalizedPoint({ left: 0, top: 0, width: 30, height: 30 }, 20, 40, NaN, 0), null);
});
test('keyboard movement clamps, never reverses with page direction', () => {
  assert.deepEqual(moveCursor({ x: 0, y: 1 }, 'ArrowLeft'), { x: 0, y: 1 });
  assert.deepEqual(moveCursor({ x: .5, y: .5 }, 'ArrowRight'), { x: .51, y: .5 });
});