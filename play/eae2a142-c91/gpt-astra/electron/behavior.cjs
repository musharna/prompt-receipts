function advance(state, { now, cursor, settings, bounds, delta }) {
  const moved = cursor.x !== state.cursor.x || cursor.y !== state.cursor.y;
  const lastActivity = moved ? now : state.lastActivity;
  const sleeping = state.manualSleep || (settings.autoNap && now - lastActivity >= settings.napDelay * 1000);
  let x = state.x, direction = state.direction;
  if (!sleeping && !state.paused) {
    x += direction * (3 + settings.pace * 6) * delta;
    if (x >= bounds.max) { x = bounds.max; direction = -1; }
    if (x <= bounds.min) { x = bounds.min; direction = 1; }
  }
  x = Math.max(bounds.min, Math.min(bounds.max, x));
  return { ...state, x, direction, sleeping, cursor, lastActivity };
}
function cleanSettings(value = {}) {
  return {
    color: ['peach', 'rose', 'sage', 'lavender', 'cloud'].includes(value.color) ? value.color : 'peach',
    pace: Math.max(1, Math.min(5, Number(value.pace) || 2)),
    autoNap: value.autoNap !== false,
    napDelay: [15, 30, 60, 300].includes(Number(value.napDelay)) ? Number(value.napDelay) : 30
  };
}
module.exports = { advance, cleanSettings };
