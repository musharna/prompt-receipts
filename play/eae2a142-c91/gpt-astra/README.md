# Miso

A quiet axolotl companion that wanders above your taskbar and naps when your mouse is idle. Includes a responsive browser preview and an Electron desktop app.

## Run the browser preview

With Node.js installed:

```sh
npm run dev
```

Open http://localhost:5173, or open `index.html` directly without a server. The preview requires no npm packages. It supports colors, pace, snacks, petting, pausing, manual naps, and automatic naps based on activity inside the page.

## Run the desktop pet

```sh
npm install
npm start
```

Click **Bring Miso to my desktop**. A transparent, always-on-top window follows the bottom of the current display’s work area, above the taskbar or dock. Mouse position is checked across the desktop, so Miso sleeps after inactivity even while you work in another app. Movement wakes automatic naps; wake manual naps using the controls. Preferences are saved locally.

Click Miso to pet or wake it. Right-click Miso for snacks, settings, and **Say goodbye** to quit. Closing the settings window leaves your adopted pet running; its context menu reopens settings.

Electron requires a graphical desktop. Transparent windows and exact positioning depend on the window manager. On Linux, X11 is recommended; Wayland may restrict app-controlled positioning. Desktop operation still needs validation on your target OS. The browser cannot draw over other applications or see mouse movement outside its page.

The companion artwork is original inline SVG. Google Fonts supplies optional DM Sans and Instrument Serif; system fonts work offline. There are no accounts, analytics, notifications, or audio.

## Validate behavior

```sh
npm test
```
