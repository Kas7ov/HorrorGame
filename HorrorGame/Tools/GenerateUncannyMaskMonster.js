const fs = require('fs');
const path = require('path');

// Generates a Blender- and Unity-compatible OBJ asset. The creature is original
// geometry: a hollow-eyed porcelain mask, bundled hair, an inky body, and long claws.
const root = path.resolve(__dirname, '..');
const outDir = path.join(root, 'Assets', 'Models', 'UncannyMaskMonster');
fs.mkdirSync(outDir, { recursive: true });

const verts = [];
const lines = [
  '# Uncanny Mask Monster - generated game mesh',
  '# Units: meters. Front faces -Z. Import scale: 1.',
  'mtllib UncannyMaskMonster.mtl',
  's 1',
];

function n(v) { return Number(v.toFixed(6)); }
function addVertex(p) { verts.push(p); return verts.length; }
function emitVertices() {
  for (const p of verts) lines.push(`v ${n(p[0])} ${n(p[1])} ${n(p[2])}`);
}
const faces = [];
let currentObject = 'UncannyMaskMonster';
function face(indices, material) { faces.push({ indices, material, object: currentObject }); }
function dot(a, b) { return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]; }
function sub(a, b) { return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]; }
function add(a, b) { return [a[0] + b[0], a[1] + b[1], a[2] + b[2]]; }
function scale(a, s) { return [a[0] * s, a[1] * s, a[2] * s]; }
function cross(a, b) { return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]; }
function len(a) { return Math.sqrt(dot(a, a)); }
function norm(a) { const l = len(a); return l > 0 ? scale(a, 1 / l) : [0, 1, 0]; }

function group(name, material) {
  currentObject = name;
}

function ellipsoid(name, material, center, radii, segments = 16, rings = 8) {
  group(name, material);
  const start = verts.length + 1;
  for (let i = 0; i <= rings; i++) {
    const phi = Math.PI * i / rings;
    const sp = Math.sin(phi);
    const cp = Math.cos(phi);
    for (let j = 0; j < segments; j++) {
      const theta = Math.PI * 2 * j / segments;
      addVertex([
        center[0] + radii[0] * sp * Math.cos(theta),
        center[1] + radii[1] * cp,
        center[2] + radii[2] * sp * Math.sin(theta),
      ]);
    }
  }
  for (let i = 0; i < rings; i++) {
    for (let j = 0; j < segments; j++) {
      const next = (j + 1) % segments;
      const a = start + i * segments + j;
      const b = start + i * segments + next;
      const c = start + (i + 1) * segments + next;
      const d = start + (i + 1) * segments + j;
      face([a, b, c, d], material);
    }
  }
}

function taper(name, material, from, to, r1, r2, segments = 10, cap = true) {
  group(name, material);
  const direction = norm(sub(to, from));
  const helper = Math.abs(direction[1]) > 0.85 ? [1, 0, 0] : [0, 1, 0];
  const u = norm(cross(direction, helper));
  const v = norm(cross(u, direction));
  const start = verts.length + 1;
  for (const [p, r] of [[from, r1], [to, r2]]) {
    for (let i = 0; i < segments; i++) {
      const theta = i * Math.PI * 2 / segments;
      addVertex(add(p, add(scale(u, Math.cos(theta) * r), scale(v, Math.sin(theta) * r))));
    }
  }
  for (let i = 0; i < segments; i++) {
    const next = (i + 1) % segments;
    face([start + i, start + next, start + segments + next, start + segments + i], material);
  }
  if (cap) {
    const a = addVertex(from);
    const b = addVertex(to);
    for (let i = 0; i < segments; i++) {
      const next = (i + 1) % segments;
      face([a, start + next, start + i], material);
      face([b, start + segments + i, start + segments + next], material);
    }
  }
}

function strand(name, points, radius, material = 'InkBlack') {
  for (let i = 0; i < points.length - 1; i++) {
    const shrink = 1 - i * 0.12;
    taper(`${name}_${i + 1}`, material, points[i], points[i + 1], radius * shrink, radius * shrink * 0.88, 7);
    if (i > 0) ellipsoid(`${name}_knot_${i}`, material, points[i], [radius * 1.05, radius * 1.05, radius * 1.05], 8, 4);
  }
}

// Main silhouette: narrow torso, too-long neck, and an off-centre shoulder slump.
ellipsoid('TatteredTorso', 'InkBlack', [0, 3.07, 0.05], [0.62, 1.16, 0.36], 20, 11);
ellipsoid('CrookedShoulders', 'InkBlack', [-0.05, 3.99, 0.03], [0.92, 0.35, 0.42], 18, 7);
ellipsoid('RibShadow', 'BodyShadow', [0, 3.22, -0.28], [0.47, 0.92, 0.1], 16, 8);
taper('NeedleNeck', 'InkBlack', [-0.06, 4.0, 0.03], [0.02, 5.15, -0.01], 0.19, 0.115, 12);
ellipsoid('HairSkull', 'InkBlack', [0.03, 5.83, 0.01], [0.70, 0.87, 0.48], 18, 11);

// Porcelain mask floats on the front of the hair silhouette.
ellipsoid('PorcelainMask', 'MaskIvory', [0.02, 5.83, -0.435], [0.41, 0.62, 0.095], 18, 10);
ellipsoid('LeftEyeSocket', 'SocketVoid', [-0.17, 5.98, -0.515], [0.145, 0.16, 0.048], 14, 7);
ellipsoid('RightEyeSocket', 'SocketVoid', [0.19, 5.98, -0.515], [0.145, 0.16, 0.048], 14, 7);
ellipsoid('LeftDullEye', 'DullEye', [-0.17, 5.98, -0.552], [0.068, 0.074, 0.028], 12, 6);
ellipsoid('RightDullEye', 'DullEye', [0.19, 5.98, -0.552], [0.068, 0.074, 0.028], 12, 6);
ellipsoid('PinchedNose', 'MaskIvory', [0.015, 5.77, -0.545], [0.075, 0.16, 0.06], 10, 6);
ellipsoid('SilentMouth', 'MouthVoid', [0.02, 5.55, -0.53], [0.15, 0.055, 0.034], 12, 5);

// Uneven bundled hair makes the face feel trapped rather than simply wearing a mask.
const hair = [
  [[-0.36, 6.52, -0.05], [-0.66, 6.2, -0.28], [-0.69, 5.65, -0.29], [-0.49, 5.14, -0.2]],
  [[-0.12, 6.65, 0.04], [-0.42, 6.48, -0.18], [-0.59, 6.05, -0.29], [-0.53, 5.48, -0.3]],
  [[0.19, 6.62, 0.03], [0.56, 6.36, -0.12], [0.68, 5.94, -0.18], [0.51, 5.31, -0.18]],
  [[0.42, 6.37, 0.11], [0.74, 6.0, -0.01], [0.72, 5.52, -0.08], [0.48, 5.09, -0.17]],
  [[-0.52, 6.2, 0.19], [-0.76, 5.79, 0.12], [-0.66, 5.26, -0.05], [-0.42, 4.87, -0.14]],
  [[0.04, 6.66, -0.04], [0.17, 6.88, 0.02], [0.1, 7.05, 0.03]],
];
hair.forEach((points, i) => strand(`HairStrand_${i + 1}`, points, 0.06));

// Left arm hangs impossibly low, with individual digit silhouettes.
strand('DanglingLeftUpper', [[-0.67, 3.95, 0.02], [-0.98, 3.15, -0.04], [-0.91, 2.57, -0.17]], 0.16);
strand('DanglingLeftFore', [[-0.91, 2.59, -0.17], [-1.03, 1.83, -0.31], [-0.91, 1.27, -0.4]], 0.12);
ellipsoid('DanglingLeftPalm', 'InkBlack', [-0.89, 1.16, -0.42], [0.22, 0.3, 0.15], 12, 7);
[
  [[-1.04, 1.08, -0.52], [-1.13, 0.62, -0.55], [-1.06, 0.32, -0.6]],
  [[-0.91, 1.0, -0.56], [-0.94, 0.48, -0.61], [-0.84, 0.2, -0.65]],
  [[-0.77, 1.07, -0.52], [-0.71, 0.59, -0.58], [-0.64, 0.33, -0.61]],
].forEach((p, i) => strand(`DanglingDigit_${i + 1}`, p, 0.048, 'ClawBone'));

// The raised arm and hand push into the viewer, echoing the reference's threatening gesture.
strand('RaisedRightUpper', [[0.7, 3.92, 0.0], [0.93, 4.47, -0.12], [1.1, 4.94, -0.29]], 0.16);
strand('RaisedRightFore', [[1.1, 4.94, -0.29], [1.35, 5.31, -0.48], [1.52, 5.62, -0.67]], 0.13);
ellipsoid('RaisedPalm', 'InkBlack', [1.61, 5.74, -0.73], [0.31, 0.39, 0.13], 14, 8);
[
  [[1.4, 5.94, -0.78], [1.3, 6.55, -0.8], [1.34, 7.03, -0.78]],
  [[1.55, 6.04, -0.82], [1.52, 6.74, -0.85], [1.57, 7.25, -0.83]],
  [[1.71, 6.04, -0.82], [1.78, 6.68, -0.84], [1.84, 7.08, -0.82]],
  [[1.86, 5.95, -0.79], [2.04, 6.45, -0.8], [2.09, 6.8, -0.78]],
].forEach((p, i) => strand(`RaisedFinger_${i + 1}`, p, 0.058, 'ClawBone'));
strand('RaisedThumb', [[1.39, 5.58, -0.79], [1.1, 5.56, -0.83], [0.93, 5.75, -0.81]], 0.065, 'ClawBone');

// Torn garment spikes break up the clean primitive silhouette.
[
  [[-0.48, 2.24, -0.03], [-0.69, 1.65, -0.06]],
  [[-0.22, 2.03, -0.22], [-0.31, 1.45, -0.29]],
  [[0.12, 2.04, -0.23], [0.2, 1.42, -0.27]],
  [[0.44, 2.27, -0.04], [0.6, 1.72, -0.08]],
].forEach((p, i) => taper(`TatteredHem_${i + 1}`, 'InkBlack', p[0], p[1], 0.11, 0.015, 7));

emitVertices();
let active = null;
let activeObject = null;
for (const f of faces) {
  if (f.object !== activeObject) {
    lines.push(`o ${f.object}`);
    activeObject = f.object;
    active = null;
  }
  if (f.material !== active) {
    lines.push(`usemtl ${f.material}`);
    active = f.material;
  }
  lines.push(`f ${f.indices.join(' ')}`);
}

const materials = `# Uncanny Mask Monster materials\n\nnewmtl InkBlack\nKa 0.008 0.005 0.013\nKd 0.022 0.012 0.035\nKs 0.12 0.08 0.16\nNs 55\n\nnewmtl BodyShadow\nKa 0.012 0.01 0.018\nKd 0.055 0.032 0.075\nKs 0.04 0.02 0.07\nNs 15\n\nnewmtl MaskIvory\nKa 0.15 0.12 0.09\nKd 0.72 0.62 0.47\nKs 0.25 0.22 0.17\nNs 95\n\nnewmtl SocketVoid\nKa 0.001 0.001 0.001\nKd 0.003 0.002 0.005\nKs 0 0 0\nNs 1\n\nnewmtl DullEye\nKa 0.08 0.075 0.06\nKd 0.29 0.27 0.21\nKs 0.48 0.46 0.38\nNs 180\n\nnewmtl MouthVoid\nKa 0.018 0.002 0.004\nKd 0.06 0.006 0.009\nKs 0.03 0.0 0.0\nNs 10\n\nnewmtl ClawBone\nKa 0.03 0.025 0.02\nKd 0.17 0.14 0.12\nKs 0.18 0.14 0.11\nNs 48\n`;

fs.writeFileSync(path.join(outDir, 'UncannyMaskMonster.obj'), `${lines.join('\n')}\n`, 'utf8');
fs.writeFileSync(path.join(outDir, 'UncannyMaskMonster.mtl'), materials, 'utf8');

const readme = `# Uncanny Mask Monster\n\nOriginal horror-character mesh inspired by the **mood** of the supplied reference: a pale, mask-like face in a tangled black silhouette. It does not reproduce the source character.\n\n- **Format:** Wavefront OBJ + MTL (editable in Blender and imported directly by Unity)\n- **Scale:** meters; around 7.25 m tall to the tallest raised finger\n- **Facing direction:** -Z\n- **Geometry:** ${verts.length.toLocaleString()} vertices, ${faces.length.toLocaleString()} faces\n- **Materials:** embedded through \`UncannyMaskMonster.mtl\`\n\n## Blender\n\nUse **File > Import > Wavefront (.obj)** and select \`UncannyMaskMonster.obj\`. Both files must remain together in this folder for the materials to load. Then save as a native \`.blend\` if you want to continue sculpting or rigging.\n\n## Unity\n\nUnity imports the OBJ automatically from this folder. Drag the model into a scene, then create or replace materials as desired for HDRP.\n\nThe mesh is deliberately split into named pieces so it can be reworked, rigged, or replaced without starting over.\n`;
fs.writeFileSync(
  path.join(outDir, 'README.md'),
  readme.replace(
    'Then save as a native `.blend` if you want to continue sculpting or rigging.',
    "To create a native Blender asset, save a new Blender scene once in this folder, then run `BuildNativeBlend.py` from Blender's **Scripting** workspace. It creates `UncannyMaskMonster.blend` without overwriting the source mesh.",
  ).replace(
    '- **Format:** Wavefront OBJ + MTL (editable in Blender and imported directly by Unity)',
    '- **Format:** native Blender `.blend`, plus editable Wavefront OBJ + MTL source',
  ),
  'utf8',
);

console.log(`Created ${verts.length} vertices and ${faces.length} faces in ${outDir}`);
