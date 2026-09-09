"""Refine the existing cervical head in-place after inspecting actual renders.

The original construction remains intact as a reproducible source. This pass
replaces its smooth crown / superficial linework with integral tissue relief
and covers the pale cervical surface accidentally visible inside the pharynx.
"""
import math
import random

import bpy
import bmesh
from mathutils import Vector, noise


def refine_head(scene, mats, api):
    """Refine neutral-space head objects and return newly created objects.

    Call on the neutral authoring scene, before duplicating/posing its meshes.
    Old surface-line and palate-rail groups are tagged as superseded and hidden;
    a pose-copy pass should skip ``superseded_cranium_detail`` objects.
    ``injury`` is FLOAT/POINT, 0 intact ivory dermis, 1 exposed pink-red tissue.
    """
    bpy.context.window.scene = scene
    bpy.context.view_layer.update()
    tube, mesh = api['smooth_tube'], api['mesh']
    apply = api.get('apply')
    added = []
    rng = random.Random(8092)

    def step(a, b, x):
        t = max(0.0, min(1.0, (x - a) / (b - a)))
        return t * t * (3.0 - 2.0 * t)

    def attr(ob, name, values):
        layer = ob.data.attributes.get(name) or ob.data.attributes.new(
            name=name, type='FLOAT', domain='POINT')
        if isinstance(values, (float, int)):
            for element in layer.data:
                element.value = values
        else:
            for element, value in zip(layer.data, values):
                element.value = value

    def make_tube(name, points, radii, material, depths=None):
        ob = tube(name, points, radii, depths, material)
        attr(ob, 'bloodflow', .15)
        attr(ob, 'injury', .0)
        added.append(ob)
        return ob

    head = next((ob for ob in scene.objects
                 if ob.type == 'MESH' and ob.name.startswith('HEAD | cervical')), None)
    if head is None:
        raise ValueError('Cervical HEAD mesh was not found in the neutral scene')
    if head.get('cranial_refinement_version') == 1:
        return []
    # Remove the visual effect of decorative red linework and bright horizontal
    # palate rails. This is recoverable: originals remain hidden in the source.
    for ob in scene.objects:
        if ob.name.startswith(('HEAD DETAIL | cranial folds',
                               'HEAD DETAIL | palatal folds')):
            ob.hide_render = True
            ob.hide_set(True)
            ob['superseded_cranium_detail'] = True

    if apply is not None:
        # Extra sampling resolves folded geometry rather than only shader noise.
        mod = head.modifiers.new('Cranial fold resolution', 'SUBSURF')
        mod.levels = 1
        apply(head, mod)
    head.data.update()
    normals = [v.normal.copy() for v in head.data.vertices]
    injuries = []
    for vertex, normal in zip(head.data.vertices, normals):
        p = vertex.co.copy()
        original = p.copy()
        crown = step(3.924, 4.005, p.z)
        # Flatten the very round crown, with asymmetric temporal planes.  Keep
        # the gum attachment / mouth silhouette fixed below z=3.93.
        p.x *= 1 - .085 * crown
        if p.z > 3.958:
            p.z = 3.958 + (p.z - 3.958) * .835
        p.y += .012 * crown * step(.09, .19, -p.y)
        hemisphere = abs(original.x)
        organic = noise.noise(original * 29.0)
        phase = hemisphere * 71 + 1.25 * math.sin(original.y * 24)
        phase += 1.6 * noise.noise(original * 19.0)
        crease = math.exp(-((math.sin(phase) / .22) ** 2))
        fold = .0045 * math.cos(phase) - .0085 * crease
        # Secondary convolutions are partial, not a regular grid or a uniform
        # all-over cracked-stone pattern.
        phase2 = original.y * 87 + math.sin(original.x * 37) * 1.4
        secondary = math.exp(-((math.sin(phase2) / .24) ** 2))
        fold -= .0032 * secondary * step(-.1, .45, organic)
        sagittal = math.exp(-((original.x / .013) ** 2))
        fold -= .006 * sagittal * step(3.995, 4.065, original.z)
        meso = noise.noise(original * 118.0) * .0014
        micro = noise.noise(original * 380.0) * .00055
        irregular_plane = noise.noise(original * 12.0) * .0045
        p += normal * crown * (fold + meso + micro + irregular_plane)
        vertex.co = p
        # Exposed upper tissue is mottled with retained thin white skin islands;
        # the frontal eyeless shield stays paler below the convoluted cap.
        torn = noise.noise(original * 18.0 + Vector((8.3, 1.7, 3.1)))
        patch = step(-.16, .32, torn)
        superior = step(3.99, 4.09, original.z)
        injury = crown * (.12 + .56 * patch + .17 * superior)
        injuries.append(min(.93, injury))
    attr(head, 'injury', injuries)
    attr(head, 'bloodflow', .15)
    head.data.update()
    head['cranial_refinement_version'] = 1

    # The previous cervical column protruded in front of the closing throat
    # disk. This wrinkled dark tissue liner is in front of that pale surface,
    # still recessed well behind both dental arcades and the jaw edge.
    vv, ff = [], []
    sides, rings = 80, 48
    center = Vector((0, -.105, 3.708))
    for j in range(rings + 1):
        phi = .0005 + (math.pi - .001) * j / rings
        for i in range(sides):
            theta = math.tau * i / sides
            px = .166 * math.sin(phi) * math.cos(theta)
            py = .110 * math.sin(phi) * math.sin(theta)
            pz = .252 * math.cos(phi)
            p = center + Vector((px, py, pz))
            # Transverse pharyngeal corrugation gives cavity depth at close
            # range; it is not a flat black cover placed over the face.
            relief = .0022 * math.sin(pz * 125 + px * 31)
            relief += .001 * noise.noise(p * 150)
            p.y += relief * max(0, -math.sin(theta))
            vv.append(p)
    for j in range(rings):
        for i in range(sides):
            a = j * sides + i
            b = j * sides + (i + 1) % sides
            ff.append((a, b, b + sides, a + sides))
    ff.append(tuple(reversed(range(sides))))
    ff.append(tuple(rings * sides + i for i in range(sides)))
    liner = mesh('HEAD REFINED | deep corrugated posterior oral tissue',
                 vv, ff, mats['throat'])
    bm = bmesh.new()
    bm.from_mesh(liner.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(liner.data)
    bm.free()
    liner['purpose'] = 'Conceals rear pale cervical tissue inside the mouth'
    added.append(liner)

    # Short dark palatal folds now lie on the recessed wall, not across air.
    for k in range(5):
        z = 3.794 + k * .022
        width = .097 - .010 * k
        points = []
        for i in range(7):
            x = -width + 2 * width * i / 6
            zlocal = z + .003 * math.sin(i * .9 + k)
            term = max(.01, 1 - (x / .166) ** 2 - ((zlocal - 3.708) / .252) ** 2)
            y = -.105 - .110 * math.sqrt(term) - .001
            points.append((x, y, zlocal))
        make_tube('HEAD REFINED | adherent mucosal ruga', points,
                  [.0013, .0027, .0033, .0035, .0033, .0027, .0013],
                  mats['throat'])

    # Vertex color factors let the shared tissue shader break up the otherwise
    # pristine mandible without repainting the pale central color scheme.
    jaw = next((ob for ob in scene.objects
                if ob.type == 'MESH' and ob.name.startswith('JAW |')), None)
    if jaw is not None:
        injury = []
        for vertex in jaw.data.vertices:
            p = vertex.co
            n = noise.noise(p * 47.0)
            injury.append(.16 + .33 * step(-.1, .44, n))
        attr(jaw, 'injury', injury)

    # Teeth remain separately editable as an organized disconnected assembly.
    # Small geometric chipping varies the tips; stains use the shared material.
    dental = next((ob for ob in scene.objects
                   if ob.type == 'MESH' and ob.name.startswith('HEAD DETAIL | dental arcade')), None)
    if dental is not None:
        for vertex in dental.data.vertices:
            p = vertex.co.copy()
            # Most perturbation is submillimetre and does not deform gums.
            n = noise.noise(p * 225.0)
            vertex.co += vertex.normal * (.00048 * n)
        attr(dental, 'injury', .12)
        dental.data.update()

    for ob in added:
        attr(ob, 'bloodflow', .15)
        if ob.data.attributes.get('injury') is None:
            attr(ob, 'injury', .0)
        for poly in ob.data.polygons:
            poly.use_smooth = True
        ob['anatomical_region'] = 'refined cervical cranium and oral cavity'
    bpy.context.view_layer.update()
    return added
