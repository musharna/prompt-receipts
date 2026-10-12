const test = require('node:test');
const assert = require('node:assert/strict');
const { advance, cleanSettings } = require('../electron/behavior.cjs');
const initial = { x: 50, direction: 1, cursor: { x: 10, y: 10 }, lastActivity: 0, manualSleep: false, sleeping: false, paused: false };
const input = { now: 1000, cursor: { x: 10, y: 10 }, settings: cleanSettings(), bounds: { min: 0, max: 100 }, delta: 1 };
test('walks and reverses at the edge without leaving the desktop', () => {
  const result = advance({ ...initial, x: 99 }, input);
  assert.equal(result.x, 100); assert.equal(result.direction, -1);
});
test('falls asleep after inactivity and wakes with global mouse movement', () => {
  const asleep = advance(initial, { ...input, now: 31000 });
  assert.equal(asleep.sleeping, true); assert.equal(asleep.x, 50);
  const awake = advance(asleep, { ...input, now: 32000, cursor: { x: 11, y: 10 } });
  assert.equal(awake.sleeping, false); assert.equal(awake.lastActivity, 32000);
});
test('manual naps persist through mouse movement', () => {
  assert.equal(advance({ ...initial, manualSleep: true }, { ...input, cursor: { x: 11, y: 11 } }).sleeping, true);
});
test('auto-nap can be disabled and wandering paused independently', () => {
  const result = advance({ ...initial, paused: true }, { ...input, now: 999999, settings: { ...input.settings, autoNap: false } });
  assert.equal(result.sleeping, false); assert.equal(result.x, 50);
});
test('handles negative display coordinates and display resizing', () => {
  const result = advance(initial, { ...input, bounds: { min: -1920, max: -180 } });
  assert.equal(result.x, -180);
});
test('normalizes untrusted or old saved settings', () => {
  assert.deepEqual(cleanSettings({ color: 'invalid', pace: 99, napDelay: -1 }), { color: 'peach', pace: 5, napDelay: 30, autoNap: true });
});
