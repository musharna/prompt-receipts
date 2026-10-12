import { mkdirSync, copyFileSync, cpSync } from 'node:fs';
mkdirSync('dist', { recursive: true });
for (const file of ['index.html', 'style.css', 'main.js']) copyFileSync(file, `dist/${file}`);
cpSync('vendor', 'dist/vendor', { recursive: true });
console.log('Built self-contained terrarium app in dist/');
