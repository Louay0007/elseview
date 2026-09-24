// Coordinates are relative to the contained asset, never the letterboxed element.
export function containedRect(rect, width, height) {
  if (![rect.left, rect.top, rect.width, rect.height, width, height].every(Number.isFinite) || rect.width <= 0 || rect.height <= 0 || width <= 0 || height <= 0) return null;
  const scale = Math.min(rect.width / width, rect.height / height);
  const w = width * scale, h = height * scale;
  return { left: rect.left + (rect.width - w) / 2, top: rect.top + (rect.height - h) / 2, width: w, height: h };
}
export function normalizedPoint(rect, width, height, clientX, clientY) {
  const box = containedRect(rect, width, height);
  if (!box || !Number.isFinite(clientX) || !Number.isFinite(clientY)) return null;
  const x = (clientX - box.left) / box.width, y = (clientY - box.top) / box.height;
  return x < 0 || x > 1 || y < 0 || y > 1 ? null : { x, y };
}
export function moveCursor(point, key, step = 0.01) {
  const delta = { ArrowLeft: [-step, 0], ArrowRight: [step, 0], ArrowUp: [0, -step], ArrowDown: [0, step] }[key];
  return delta ? { x: Math.max(0, Math.min(1, point.x + delta[0])), y: Math.max(0, Math.min(1, point.y + delta[1])) } : point;
}