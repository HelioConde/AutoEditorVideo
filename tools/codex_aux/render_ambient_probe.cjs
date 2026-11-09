// Render the shipped EP01 overlay locally with synthetic anchors, free of private assets.
// Usage: node tools/codex_aux/render_ambient_probe.cjs <empty/new output directory>
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {createRequire} = require('node:module');
const pkg = createRequire(path.resolve(__dirname, '../../motion-remotion/package.json'));
const ts = pkg('typescript');
const {renderToStaticMarkup} = pkg('react-dom/server');
const src = fs.readFileSync(pkg.resolve('./src/fofinhos-ambient-effects.tsx'), 'utf8');
const code = ts.transpileModule(src, {compilerOptions: {
  module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020,
  jsx: ts.JsxEmit.ReactJSX,
}}).outputText;
const mod = {exports: {}};
new Function('require', 'module', 'exports', code)(pkg, mod, mod.exports);
const {FofinhosAmbientEffects} = mod.exports;
const output = process.argv[2];
if (!output) throw new Error('Pass a new or empty output directory.');
fs.mkdirSync(output, {recursive: true});
assert.equal(fs.readdirSync(output).length, 0, 'Output directory must be empty');
const keys = ['clouds', 'butterflies', 'petals', 'pollen', 'eggSparkles', 'motes'];
const cases = [
  {name: 'garden', index: 1, counts: [2,2,3,8,0,0], night: false, showEgg: false},
  {name: 'night-egg', index: 14, counts: [0,0,0,0,4,1], night: true, showEgg: true},
  {name: 'night-hidden', index: 14, counts: [99,99,99,99,99,99], night: true,
    showEgg: false, expected: [0,0,0,0,0,6]},
];
for (const c of cases) {
  const plan = Object.fromEntries(keys.map((key, i) => [key, c.counts[i]]));
  const scene = {index: c.index, startFrame: 100, eggX: .5, eggY: .55,
    night: c.night, showEgg: c.showEgg};
  const rendered = [];
  for (const local of [0, 12, 24, 48]) {
    const svg = FofinhosAmbientEffects({scene, frame: scene.startFrame + local, plan});
    assert.equal(svg.props.style.opacity, Math.min(1, local/24));
    // SVG child arrays are in paint order, with sparkles drawn after motes.
    const [clouds, butterflies, petals, pollen, motes, sparkles] =
      svg.props.children.map(group => group.length);
    assert.deepEqual([clouds, butterflies, petals, pollen, sparkles, motes],
      c.expected ?? c.counts);
    const markup = renderToStaticMarkup(svg);
    assert.match(markup, /^<svg/);
    assert.doesNotMatch(markup, /<(image|script|foreignObject)\b|\shref\s*=/i);
    fs.writeFileSync(path.join(output, `${c.name}-${local}.svg`), markup);
    rendered.push(markup);
  }
  assert.notEqual(rendered[2], rendered[3], 'Visible motion after fade-in');
}
console.log('12 SVG frames verified (3 cases, 4 times, production TSX).');
