const { contextBridge, ipcRenderer } = require('electron');
contextBridge.exposeInMainWorld('miso', {
  adopt: () => ipcRenderer.invoke('adopt'),
  getSettings: () => ipcRenderer.invoke('get-settings'),
  setSettings: settings => ipcRenderer.send('set-settings', settings),
  action: action => ipcRenderer.send('action', action),
  menu: () => ipcRenderer.send('pet-menu'),
  onSettings: callback => ipcRenderer.on('settings', (_event, value) => callback(value)),
  onState: callback => ipcRenderer.on('state', (_event, value) => callback(value)),
  onAction: callback => ipcRenderer.on('action', (_event, value) => callback(value))
});
