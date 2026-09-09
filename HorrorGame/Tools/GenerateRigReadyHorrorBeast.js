const fs = require('fs');
const path = require('path');

// Original rig-ready creature. Symmetry, A-pose, and separated digits are intentional:
// it is built for a first armature pass, not for a dramatic static render pose.
const root = path.resolve(__dirname, '..');
const outDir = path.join(root, 'Assets', 'Models', 'UncannyMaskMonster');
fs.mkdirSync(outDir, { recursive: true });

for (const file of ['UncannyMaskMonster.obj', 'UncannyMaskMonster.mtl']) {
  const source = path.join(outDir, file);
  const backup = path.join(outDir, file.replace('.', '_PreRedesign.'));
  if (fs.existsSync(source) && !fs.existsSync(backup)) fs.copyFileSync(source, backup);
}

const verts = [];
const faces = [];
let activeObject = 'RiftStalker';
function n(v) { return Number(v.toFixed(6)); }
function addVertex(p) { verts.push(p); return verts.length; }
function face(indices, material) { faces.push({ indices, material, object: activeObject }); }
function group(name) { activeObject = name; }
function add(a, b) { return [a[0] + b[0], a[1] + b[1], a[2] + b[2]]; }
function sub(a, b) { return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]; }
function mul(a, s) { return [a[0] * s, a[1] * s, a[2] * s]; }
function dot(a, b) { return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]; }
function cross(a, b) { return [a[1] * b[2] - a[2] * b[0], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]; }
function norm(a) { const l = Math.sqrt(dot(a, a)); return l ? mul(a, 1 / l) : [0, 1, 0]; }

function ellipsoid(name, material, center, radii, segments = 16, rings = 8) {
  group(name);
  const start = verts.length + 1;
  for (let i = 0; i <= rings; i++) {
    const phi = Math.PI * i / rings;
    for (let j = 0; j < segments; j++) {
      const theta = Math.PI * 2 * j / segments;
      addVertex([
        center[0] + radii[0] * Math.sin(phi) * Math.cos(theta),
        center[1] + radii[1] * Math.cos(phi),
        center[2] + radii[2] * Math.sin(phi) * Math.sin(theta),
      ]);
    }
  }
  for (let i = 0; i < rings; i++) {
    for (let j = 0; j < segments; j++) {
      const next = (j + 1) % segments;
      face([start + i * segments + j, start + i * segments + next, start + (i + 1) * segments + next, start + (i + 1) * segments + j], material);
    }
  }
}

function taper(name, material, from, to, r1, r2, segments = 10) {
  group(name);
  const direction = norm(sub(to, from));
  const helper = Math.abs(direction[1]) > 0.86 ? [1, 0, 0] : [0, 1, 0];
  const u = norm(cross(direction, helper));
  const v = norm(cross(u, direction));
  const start = verts.length + 1;
  for (const [point, radius] of [[from, r1], [to, r2]]) {
    for (let i = 0; i < segments; i++) {
      const theta = Math.PI * 2 * i / segments;
      addVertex(add(point, add(mul(u, Math.cos(theta) * radius), mul(v, Math.sin(theta) * radius))));
    }
  }
  for (let i = 0; i < segments; i++) {
    const next = (i + 1) % segments;
    face([start + i, start + next, start + segments + next, start + segments + i], material);
  }
  const capA = addVertex(from);
  const capB = addVertex(to);
  for (let i = 0; i < segments; i++) {
    const next = (i + 1) % segments;
    face([capA, start + next, start + i], material);
    face([capB, start + segments + i, start + segments + next], material);
  }
}

function tendon(name, points, radius, material = 'TendonDark') {
  for (let i = 0; i < points.length - 1; i++) {
    const a = radius * (1 - i * 0.12);
    taper(`${name}_${i + 1}`, material, points[i], points[i + 1], a, a * 0.85, 7);
    if (i > 0) ellipsoid(`${name}_Joint_${i}`, material, points[i], [a, a, a], 8, 4);
  }
}

// Core: upright human-like proportions keep the silhouette convenient for a standard biped rig.
ellipsoid('Pelvis_Symmetric', 'FleshPale', [0, 3.18, 0.04], [0.78, 0.58, 0.48], 20, 10);
ellipsoid('Abdomen_Sinew', 'FleshPale', [0, 4.25, 0.0], [0.67, 0.98, 0.41], 20, 11);
ellipsoid('RibCage', 'FleshLight', [0, 5.45, 0.03], [0.98, 1.12, 0.56], 22, 12);
ellipsoid('BackCarapace', 'TendonDark', [0, 5.4, 0.43], [0.8, 1.18, 0.17], 20, 10);
ellipsoid('ShoulderMantle', 'FleshLight', [0, 6.15, 0.0], [1.36, 0.43, 0.56], 22, 8);
taper('NeckColumn', 'TendonDark', [0, 6.15, 0.05], [0, 7.08, 0.04], 0.29, 0.23, 12);

// Layered chest fibres and ribs provide a scarier, more intricate surface without obstructing joints.
for (const side of [-1, 1]) {
  for (let i = 0; i < 4; i++) {
    const y = 5.95 - i * 0.34;
    ellipsoid(`RibPlate_${side}_${i + 1}`, 'FleshLight', [side * (0.29 + i * 0.035), y, -0.45], [0.53 - i * 0.035, 0.12, 0.11], 14, 6);
    tendon(`RibTendon_${side}_${i + 1}`, [[side * 0.09, y + 0.05, -0.36], [side * 0.62, y - 0.08, -0.43]], 0.035, 'TendonRed');
  }
  ellipsoid(`PectoralMass_${side}`, 'FleshPale', [side * 0.46, 5.72, -0.28], [0.43, 0.38, 0.22], 16, 8);
  ellipsoid(`HipPlate_${side}`, 'FleshLight', [side * 0.52, 3.26, -0.22], [0.34, 0.37, 0.2], 14, 7);
}
ellipsoid('SternumCavity', 'CavityBlack', [0, 5.48, -0.52], [0.19, 0.72, 0.08], 14, 8);
for (let i = 0; i < 5; i++) taper(`BackSpine_${i + 1}`, 'ClawBone', [0, 4.55 + i * 0.5, 0.52], [0, 4.7 + i * 0.5, 0.98], 0.11, 0.012, 7);

// A skull with an open vertical maw: monstrous but centred and head-rig friendly.
ellipsoid('CrestedSkull', 'FleshLight', [0, 7.76, 0.03], [0.74, 0.9, 0.63], 20, 12);
ellipsoid('FacialCavity', 'CavityBlack', [0, 7.72, -0.61], [0.41, 0.56, 0.08], 16, 9);
ellipsoid('MawCore', 'MouthRed', [0, 7.46, -0.7], [0.3, 0.33, 0.07], 14, 7);
ellipsoid('BrowLeft', 'FleshPale', [-0.31, 8.0, -0.57], [0.3, 0.2, 0.11], 12, 6);
ellipsoid('BrowRight', 'FleshPale', [0.31, 8.0, -0.57], [0.3, 0.2, 0.11], 12, 6);
ellipsoid('EyeOrbLeft', 'DeadEye', [-0.21, 7.9, -0.68], [0.105, 0.115, 0.045], 12, 6);
ellipsoid('EyeOrbRight', 'DeadEye', [0.21, 7.9, -0.68], [0.105, 0.115, 0.045], 12, 6);
ellipsoid('ThirdEye', 'DeadEye', [0, 8.2, -0.68], [0.09, 0.1, 0.04], 12, 6);
for (const side of [-1, 1]) {
  tendon(`TempleTendons_${side}`, [[side * 0.62, 8.05, -0.08], [side * 0.86, 7.72, -0.08], [side * 0.65, 7.34, -0.18]], 0.055, 'TendonDark');
  taper(`CrestHorn_${side}`, 'ClawBone', [side * 0.4, 8.38, 0.18], [side * 0.88, 8.88, 0.38], 0.15, 0.018, 9);
}
for (const side of [-1, 1]) {
  for (let i = 0; i < 4; i++) {
    const x = side * (0.1 + i * 0.09);
    taper(`MawToothTop_${side}_${i}`, 'ToothIvory', [x, 7.7 - i * 0.02, -0.7], [x, 7.48 - i * 0.025, -0.76], 0.045, 0.008, 7);
    taper(`MawToothBottom_${side}_${i}`, 'ToothIvory', [x, 7.26 + i * 0.015, -0.7], [x, 7.43 + i * 0.025, -0.76], 0.04, 0.007, 7);
  }
}

// Symmetric A-pose arms: clear shoulder/elbow/wrist centres and individually separated fingers.
function buildArm(side) {
  const tag = side < 0 ? 'L' : 'R';
  const shoulder = [side * 1.08, 6.05, 0];
  const elbow = [side * 1.91, 5.34, -0.03];
  const wrist = [side * 2.57, 4.68, -0.08];
  tendon(`Clavicle_${tag}`, [[side * 0.25, 6.1, -0.01], shoulder], 0.14, 'TendonDark');
  taper(`UpperArm_${tag}`, 'FleshPale', shoulder, elbow, 0.31, 0.22, 12);
  ellipsoid(`Deltoid_${tag}`, 'FleshLight', [side * 1.14, 5.9, -0.02], [0.37, 0.39, 0.35], 16, 8);
  ellipsoid(`Bicep_${tag}`, 'FleshLight', [side * 1.48, 5.62, -0.18], [0.31, 0.43, 0.22], 16, 8);
  ellipsoid(`Tricep_${tag}`, 'TendonDark', [side * 1.5, 5.63, 0.21], [0.26, 0.39, 0.18], 14, 7);
  ellipsoid(`ElbowNode_${tag}`, 'ClawBone', elbow, [0.24, 0.2, 0.22], 14, 7);
  taper(`Forearm_${tag}`, 'FleshPale', elbow, wrist, 0.23, 0.14, 12);
  tendon(`ForearmTendon_${tag}`, [[side * 1.95, 5.28, -0.22], [side * 2.34, 4.95, -0.25], wrist], 0.045, 'TendonRed');
  ellipsoid(`Palm_${tag}`, 'FleshLight', [side * 2.68, 4.5, -0.11], [0.24, 0.3, 0.16], 14, 7);
  for (let i = 0; i < 4; i++) {
    const offset = (i - 1.5) * 0.105;
    const base = [side * (2.68 + offset * 0.25), 4.34, -0.19 + offset];
    const mid = [side * (2.75 + offset * 0.35), 4.0, -0.26 + offset];
    const tip = [side * (2.79 + offset * 0.45), 3.73 + (i === 0 ? 0.06 : 0), -0.31 + offset];
    tendon(`Finger_${tag}_${i + 1}`, [base, mid, tip], 0.047, 'FleshPale');
    taper(`FingerClaw_${tag}_${i + 1}`, 'ClawBone', tip, [tip[0], tip[1] - 0.16, tip[2] - 0.08], 0.05, 0.006, 7);
  }
  tendon(`Thumb_${tag}`, [[side * 2.57, 4.52, -0.21], [side * 2.76, 4.35, -0.37], [side * 2.82, 4.14, -0.4]], 0.06, 'FleshPale');
}
buildArm(-1); buildArm(1);

// Symmetric straight legs and planted feet. No crouch, no twist, no crossing.
function buildLeg(side) {
  const tag = side < 0 ? 'L' : 'R';
  const hip = [side * 0.48, 3.12, 0.02];
  const knee = [side * 0.57, 1.83, -0.03];
  const ankle = [side * 0.55, 0.55, -0.01];
  taper(`Thigh_${tag}`, 'FleshPale', hip, knee, 0.4, 0.28, 14);
  ellipsoid(`Quadricep_${tag}`, 'FleshLight', [side * 0.52, 2.55, -0.22], [0.34, 0.57, 0.2], 16, 9);
  ellipsoid(`Hamstring_${tag}`, 'TendonDark', [side * 0.51, 2.53, 0.25], [0.29, 0.56, 0.17], 14, 8);
  ellipsoid(`KneeJoint_${tag}`, 'ClawBone', knee, [0.29, 0.24, 0.25], 16, 8);
  taper(`Shin_${tag}`, 'FleshPale', knee, ankle, 0.27, 0.16, 12);
  ellipsoid(`Calf_${tag}`, 'FleshLight', [side * 0.55, 1.16, 0.18], [0.31, 0.54, 0.22], 16, 8);
  tendon(`ShinTendon_${tag}`, [[side * 0.58, 1.72, -0.25], [side * 0.57, 1.1, -0.29], ankle], 0.048, 'TendonRed');
  ellipsoid(`Foot_${tag}`, 'FleshPale', [side * 0.55, 0.27, -0.4], [0.27, 0.2, 0.67], 16, 7);
  for (let i = 0; i < 3; i++) {
    const offset = (i - 1) * 0.14;
    const toeBase = [side * (0.55 + offset), 0.18, -0.7];
    const toeTip = [side * (0.55 + offset * 1.15), 0.12, -1.13];
    taper(`Toe_${tag}_${i + 1}`, 'FleshLight', toeBase, toeTip, 0.09, 0.05, 8);
    taper(`ToeClaw_${tag}_${i + 1}`, 'ClawBone', toeTip, [toeTip[0], toeTip[1] - 0.02, toeTip[2] - 0.18], 0.055, 0.006, 7);
  }
}
buildLeg(-1); buildLeg(1);

const lines = [
  '# Rift Stalker - original rig-ready horror creature',
  '# A-pose, world origin at ground centre, source up axis Y, front -Z',
  'mtllib UncannyMaskMonster.mtl',
  's 1',
];
for (const p of verts) lines.push(`v ${n(p[0])} ${n(p[1])} ${n(p[2])}`);
let currentObject = null;
let currentMaterial = null;
for (const f of faces) {
  if (f.object !== currentObject) { lines.push(`o ${f.object}`); currentObject = f.object; currentMaterial = null; }
  if (f.material !== currentMaterial) { lines.push(`usemtl ${f.material}`); currentMaterial = f.material; }
  lines.push(`f ${f.indices.join(' ')}`);
}

const materials = `# Rift Stalker material library\n\nnewmtl FleshPale\nKa 0.11 0.05 0.06\nKd 0.52 0.27 0.30\nKs 0.17 0.08 0.10\nNs 58\n\nnewmtl FleshLight\nKa 0.16 0.08 0.09\nKd 0.71 0.43 0.46\nKs 0.24 0.14 0.16\nNs 72\n\nnewmtl TendonDark\nKa 0.04 0.008 0.015\nKd 0.18 0.025 0.05\nKs 0.12 0.025 0.04\nNs 38\n\nnewmtl TendonRed\nKa 0.08 0.005 0.01\nKd 0.39 0.035 0.06\nKs 0.18 0.03 0.04\nNs 45\n\nnewmtl CavityBlack\nKa 0.001 0.001 0.002\nKd 0.006 0.003 0.009\nKs 0.01 0.005 0.01\nNs 8\n\nnewmtl MouthRed\nKa 0.11 0.006 0.01\nKd 0.36 0.012 0.025\nKs 0.23 0.02 0.03\nNs 75\n\nnewmtl DeadEye\nKa 0.12 0.1 0.075\nKd 0.5 0.43 0.31\nKs 0.6 0.55 0.42\nNs 170\n\nnewmtl ToothIvory\nKa 0.13 0.1 0.07\nKd 0.68 0.58 0.39\nKs 0.3 0.25 0.16\nNs 95\n\nnewmtl ClawBone\nKa 0.06 0.045 0.035\nKd 0.29 0.21 0.16\nKs 0.22 0.16 0.11\nNs 55\n`;

fs.writeFileSync(path.join(outDir, 'UncannyMaskMonster.obj'), `${lines.join('\n')}\n`, 'utf8');
const styledMaterials = materials
  .replace('Kd 0.52 0.27 0.30', 'Kd 0.39 0.16 0.19')
  .replace('Kd 0.71 0.43 0.46', 'Kd 0.56 0.30 0.33')
  .replace('Kd 0.39 0.035 0.06', 'Kd 0.28 0.018 0.035');
fs.writeFileSync(path.join(outDir, 'UncannyMaskMonster.mtl'), styledMaterials, 'utf8');
fs.writeFileSync(path.join(outDir, 'RigReadyNotes.md'), `# Rift Stalker rigging notes\n\nThis redesign is in a neutral **A-pose** with mirrored, uncrossed limbs, planted feet, visibly separated knees/elbows/wrists, and separated fingers/toes.\n\n- Front axis: **-Z**\n- Source up axis: **Y**\n- Ground contact: y = 0\n- Recommended first armature: pelvis > spine > chest > neck > head; clavicle > upper arm > forearm > hand; hip > thigh > shin > foot > toe.\n- The native Blender file contains a matching, non-destructive armature guide called \`RIG_RiftStalker_Guide\`. It is not weighted to the mesh, leaving the final skinning method under your control.\n\nThe mesh uses deliberately named anatomy pieces so you can join, retopologize, or skin selectively.\n`, 'utf8');
console.log(`Generated redesigned rig-ready creature: ${verts.length} vertices, ${faces.length} faces, ${new Set(faces.map(f => f.object)).size} named pieces.`);
