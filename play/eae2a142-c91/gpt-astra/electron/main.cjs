const { app, BrowserWindow, ipcMain, screen, Menu } = require('electron');
const path = require('node:path');
const fs = require('node:fs');
const { advance, cleanSettings } = require('./behavior.cjs');
let panel, pet, timer, state, settings = cleanSettings(), saveTimer;
const preferences = () => path.join(app.getPath('userData'), 'preferences.json');
const options = { preload: path.join(__dirname, 'preload.cjs'), contextIsolation: true, nodeIntegration: false, sandbox: true };
function send(channel, value) { for (const win of [panel, pet]) if (win && !win.isDestroyed()) win.webContents.send(channel, value); }
function createPanel() {
  if (panel && !panel.isDestroyed()) { panel.show(); panel.focus(); return; }
  panel = new BrowserWindow({ width: 1280, height: 980, minWidth: 420, minHeight: 600, title: 'Miso — a little desktop company', backgroundColor: '#fbf9f5', autoHideMenuBar: true, webPreferences: options });
  panel.loadFile(path.join(__dirname, '../index.html'));
  panel.on('closed', () => { panel = null; });
}
function adopt() {
  if (pet && !pet.isDestroyed()) { pet.showInactive(); return; }
  const display = screen.getDisplayNearestPoint(screen.getCursorScreenPoint());
  const area = display.workArea;
  state = { x: area.x + area.width * .55, direction: 1, cursor: screen.getCursorScreenPoint(), lastActivity: Date.now(), sleeping: false, manualSleep: false, paused: false };
  pet = new BrowserWindow({ x: Math.round(state.x), y: area.y + area.height - 150, width: 180, height: 150, transparent: true, frame: false, alwaysOnTop: true, resizable: false, skipTaskbar: true, hasShadow: false, focusable: false, show: false, webPreferences: options });
  pet.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });
  pet.loadFile(path.join(__dirname, '../index.html'), { query: { pet: '1' } });
  pet.once('ready-to-show', () => { if (pet) { pet.showInactive(); send('settings', settings); } });
  let previous = Date.now();
  timer = setInterval(() => {
    if (!pet || pet.isDestroyed()) return;
    const now = Date.now();
    const currentDisplay = screen.getAllDisplays().find(d => d.id === display.id) || screen.getPrimaryDisplay();
    const work = currentDisplay.workArea;
    state = advance(state, { now, cursor: screen.getCursorScreenPoint(), settings, bounds: { min: work.x, max: work.x + Math.max(0, work.width - 180) }, delta: Math.min((now - previous) / 1000, .1) });
    previous = now;
    pet.setPosition(Math.round(state.x), work.y + work.height - 150, false);
    pet.webContents.send('state', { sleeping: state.sleeping, paused: state.paused, direction: state.direction });
  }, 50);
  pet.on('closed', () => { clearInterval(timer); pet = null; });
}
function action(name) {
  if (!state || !pet) return;
  if (name === 'sleep') state.manualSleep = true;
  if (['wake', 'pet', 'snack'].includes(name)) { state.manualSleep = false; state.lastActivity = Date.now(); }
  if (name === 'pause') state.paused = true;
  if (name === 'wander') state.paused = false;
  send('action', name);
}
app.whenReady().then(() => {
  try { settings = cleanSettings(JSON.parse(fs.readFileSync(preferences(), 'utf8'))); } catch {}
  ipcMain.handle('adopt', adopt);
  ipcMain.handle('get-settings', () => settings);
  ipcMain.on('set-settings', (_event, value) => {
    settings = cleanSettings(value); send('settings', settings);
    clearTimeout(saveTimer); saveTimer = setTimeout(() => { try { fs.writeFileSync(preferences(), JSON.stringify(settings)); } catch (error) { console.error('Could not save Miso preferences:', error.message); } }, 250);
  });
  ipcMain.on('action', (_event, name) => action(name));
  ipcMain.on('pet-menu', () => Menu.buildFromTemplate([
    { label: 'A moment with Miso', enabled: false }, { type: 'separator' },
    { label: 'Give a snack', click: () => action('snack') },
    { label: state?.sleeping ? 'Wake Miso' : 'Time for a nap', click: () => action(state?.sleeping ? 'wake' : 'sleep') },
    { label: 'Open settings', click: createPanel }, { type: 'separator' },
    { label: 'Say goodbye', click: () => app.quit() }
  ]).popup({ window: pet }));
  createPanel();
  app.on('activate', createPanel);
});
app.on('window-all-closed', () => app.quit());
app.on('before-quit', () => { clearInterval(timer); clearTimeout(saveTimer); try { fs.writeFileSync(preferences(), JSON.stringify(settings)); } catch {} });
