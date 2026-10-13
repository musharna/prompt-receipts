const fs = require('fs'), d = __dirname;
const rd = f => fs.readFileSync(d + '/' + f, 'utf8');
const wrap = f => `(function(){const exports={};${rd(f)}\nObject.assign(window.MODEL_DEFS,exports);})();`;
const models = 'window.MODEL_DEFS={};' + wrap('m_simple.js') + wrap('m_crane.js');
let h = rd('tpl.html').replace('/*ENGINE*/', () => rd('engine.js')).replace('/*MODELS*/', () => models).replace('/*APP*/', () => rd('app.js'));
h = h.replace(/\\u([0-9a-f]{4})/g, (_, x) => '\\u' + x); // keep escapes as-is
fs.writeFileSync(d + '/../origami.html', h);
console.log('built', h.length);
