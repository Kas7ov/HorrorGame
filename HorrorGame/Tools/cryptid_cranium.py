"""Detailed cervical cryptid cranium, in native +Z-up / -Y-forward space.

This module creates real Blender geometry.  The gaping mouth belongs to the
head above the sternum; no cranial or oral geometry is attached to the pelvis.
The caller supplies its mesh helpers and the shared creature materials.
"""
import math
import random

import bpy
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def build_head(api, materials):
    tube = api['smooth_tube']
    mesh = api['mesh']
    ell = api['ell']
    remesh = api['remesh']
    apply = api['apply']
    join = api['join']
    rng = random.Random(7193)
    skin, blood, muscle, fascia, bone, horn, throat, tongue_mat, saliva = [
        materials[k] for k in ('skin', 'blood', 'muscle', 'fascia', 'bone',
                                'horn', 'throat', 'tongue', 'saliva')]
    objects = []
    groups = {'cranial folds': [], 'cheek sinews': [], 'dental arcade': [],
              'palatal folds': [], 'oral wetness': [], 'tongue detail': []}

    def addtube(name, pts, widths, mat, depths=None, group=None):
        ob = tube(name, pts, widths, depths, mat)
        (groups[group] if group else objects).append(ob)
        return ob

    def bloodflow(ob, value):
        if ob.type != 'MESH':
            return
        attr = ob.data.attributes.get('bloodflow') or ob.data.attributes.new(
            name='bloodflow', type='FLOAT', domain='POINT')
        for datum in attr.data:
            datum.value = value

    # An asymmetric, continuous cranial vault, not a stack of spheres.  Low
    # amplitude geometric folds complement material pores without inflating it.
    def cranial_point(theta, phi):
        sn = math.sin(phi)
        x = .239 * sn * math.cos(theta)
        y = -.014 + .206 * sn * math.sin(theta)
        z = 3.987 + .236 * math.cos(phi)
        upper = max(0.0, min(1.0, (z - 3.93) / .21))
        irregular = (math.sin(theta * 7.0 + phi * 3.7) * .0025
                     + math.sin(theta * 13.0 - phi * 8.1) * .0015)
        x += irregular * math.cos(theta) * upper
        y += irregular * math.sin(theta) * upper
        z += upper * .003 * math.sin(theta * 4.0 + phi * 6.0)
        # The sagittal fissure is sculpted into the surface, not a black stripe.
        sagittal = math.exp(-(x / .013) ** 2) * upper
        z -= .006 * sagittal
        return Vector((x, y, z))

    vertices, faces = [], []
    nr, ns = 62, 112
    for j in range(nr + 1):
        phi = .0005 + (math.pi - .001) * j / nr
        for i in range(ns):
            vertices.append(cranial_point(2 * math.pi * i / ns, phi))
    for j in range(nr):
        for i in range(ns):
            a = j * ns + i
            b = j * ns + (i + 1) % ns
            faces.append((a, b, b + ns, a + ns))
    faces.append(tuple(reversed(range(ns))))
    faces.append(tuple(nr * ns + i for i in range(ns)))
    vault = mesh('Cranial vault | blind asymmetric flesh', vertices, faces, skin)
    bm = bmesh.new()
    bm.from_mesh(vault.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(vault.data)
    bm.free()
    bridge = tube('Occipital cervical attachment',
                  [(0, .065, 3.60), (0, .105, 3.72), (0, .117, 3.86),
                   (0, .08, 3.99)], [.081, .101, .133, .14],
                  [.080, .080, .085, .11], skin)
    head = remesh([vault, bridge], 'HEAD | cervical eyeless cranium', .0065)
    # Cutting the actual solid produces a visibly recessed mouth rather than
    # placing a dark oval on an intact face.  The rear neck remains continuous.
    cutter = ell('Temporary oral cavity cutter', (0, -.302, 3.662),
                 (.218, .310, .300), None)
    modifier = head.modifiers.new('Open facial vault', 'BOOLEAN')
    modifier.operation = 'DIFFERENCE'
    modifier.solver = 'EXACT'
    modifier.object = cutter
    apply(head, modifier)
    bpy.data.objects.remove(cutter, do_unlink=True)
    bloodflow(head, .15)
    objects.append(head)
    bpy.context.view_layer.update()
    tree = BVHTree.FromObject(head, bpy.context.evaluated_depsgraph_get())

    def on_vault(theta, phi, offset=0.0):
        pos = cranial_point(theta, phi)
        normal = Vector((pos.x / .239, (pos.y + .014) / .206,
                         (pos.z - 3.987) / .236)).normalized()
        hit, n, _, _ = tree.ray_cast(pos + normal * .06, -normal, .15)
        return (hit + n * offset) if hit is not None else pos

    # Small interlocking sulci and vessels hug the vault.  None can be mistaken
    # for eyes: they are restricted to its superior surface and temporal edges.
    for side in (-1, 1):
        for k in range(7):
            pts, darkpts = [], []
            theta0 = -.94 + k * .34
            for j in range(13):
                t = j / 12
                phi = .20 + .94 * t
                theta = theta0 + .18 * math.sin(t * math.pi * 3 + k * 1.9)
                if side == -1:
                    theta = math.pi - theta
                pts.append(on_vault(theta, phi, -.0015))
                darkpts.append(on_vault(theta + side * .027, phi, .0005))
            widths = [.002 + .0045 * math.sin(math.pi * j / 12) ** .7
                      for j in range(13)]
            addtube('Adherent cranial fold', pts, widths,
                    muscle if k % 3 == 0 else skin, group='cranial folds')
            if k % 2 == 0:
                addtube('Branching cranial sulcus', darkpts,
                        [.0007] + [.00135] * 11 + [.0005], blood,
                        group='cranial folds')
    for side in (-1, 1):
        pts = [on_vault((-1.8 if side == -1 else -1.34) + .08 * math.sin(j),
                        .34 + j * .085, .001) for j in range(11)]
        addtube('Cranial capillary', pts, [.0012] * len(pts), blood,
                group='cranial folds')

    # The mandible has long angular rami and a narrow pointed mental ridge.
    # Its front edge is distinctly separated from the wet inner gumline.
    jaw_pts = [(-.209, -.095, 3.922), (-.219, -.195, 3.78),
               (-.186, -.30, 3.57), (-.103, -.397, 3.402),
               (-.022, -.428, 3.351), (.047, -.422, 3.360),
               (.132, -.378, 3.434), (.198, -.27, 3.63),
               (.214, -.105, 3.924)]
    jaw_widths = [.025, .026, .022, .023, .027, .026, .023, .024, .026]
    jaw = addtube('JAW | elongated angular mandible', jaw_pts, jaw_widths, skin)
    bloodflow(jaw, .29)
    # The bone lies partly under skin, creating a real jaw plane in side light.
    for side in (-1, 1):
        q = lambda p: (side * p[0], p[1], p[2])
        addtube('Exposed mandibular lamina',
                [q((.201, -.166, 3.844)), q((.191, -.262, 3.648)),
                 q((.125, -.357, 3.454)), q((.029, -.411, 3.365))],
                [.008, .011, .009, .004], fascia,
                depths=[.004, .006, .005, .002], group='cheek sinews')
        # A ruffled triangulated cheek web is narrow enough to leave the entire
        # central oral opening unobstructed.  Tension ridges follow its edges.
        vv, ff = [], []
        for j in range(12):
            t = j / 11
            upper = Vector(q((.193 + .018 * math.sin(t * math.pi),
                              -.08 - .10 * t, 3.921 - .04 * t)))
            lower = Vector(q((.080 + .111 * (1 - t),
                              -.39 + .11 * (1 - t), 3.421 + .24 * (1 - t))))
            for k in range(5):
                v = upper.lerp(lower, k / 4)
                v.x += side * .006 * math.sin(t * 17 + k) * math.sin(k / 4 * math.pi)
                vv.append(v)
        for j in range(11):
            for k in range(4):
                a = j * 5 + k
                ff.append((a, a + 1, a + 6, a + 5))
        cheek = mesh('Stretched buccal web', vv, ff, muscle)
        mod = cheek.modifiers.new('Cheek membrane', 'SOLIDIFY')
        mod.thickness = .004
        apply(cheek, mod)
        groups['cheek sinews'].append(cheek)
        for k in range(7):
            t = k / 6
            addtube('Cheek tension fascicle',
                    [q((.196 + .012 * t, -.086 - .11 * t, 3.930 - .048 * t)),
                     q((.202 - .057 * t, -.222 - .057 * t, 3.717 - .068 * t)),
                     q((.194 - .103 * t, -.280 - .115 * t, 3.662 - .225 * t))],
                    [.004, .0032, .002], fascia if k % 3 == 0 else blood,
                    group='cheek sinews')

    # A real concave pharyngeal funnel with soft transverse corrugations keeps
    # the cavity from reading as a featureless black painted triangle.
    vv, ff = [], []
    rings, sides = 15, 72
    for j in range(rings):
        t = j / (rings - 1)
        rx = .175 * (1 - t) + .031 * t
        rz = .235 * (1 - t) + .045 * t
        for i in range(sides):
            a = 2 * math.pi * i / sides
            ripple = 1 + .035 * math.sin(j * 2.3 + a * 5)
            x = math.cos(a) * rx * ripple
            z = 3.692 + .045 * t + math.sin(a) * rz * ripple
            y = -.244 + .270 * t + .012 * math.cos(a * 3 + j)
            vv.append((x, y, z))
    for j in range(rings - 1):
        for i in range(sides):
            a = j * sides + i
            b = j * sides + (i + 1) % sides
            ff.append((a, a + sides, b + sides, b))
    ff.append(tuple((rings - 1) * sides + i for i in range(sides)))
    pharynx = mesh('PHARYNX | recessed corrugated oral tunnel', vv, ff, throat)
    objects.append(pharynx)
    for k in range(6):
        z = 3.78 + k * .023
        width = .128 - k * .009
        pts = [(-width, -.20 + .008 * k, z), (-width * .5, -.216, z + .010),
               (0, -.218, z + .015), (width * .5, -.216, z + .010),
               (width, -.20 + .008 * k, z)]
        addtube('Palatal ruga', pts, [.002, .005, .006, .005, .002],
                muscle, group='palatal folds')

    def upper_gum(u):
        return Vector((u * .194, -.266 - .055 * math.sqrt(max(0, 1 - u * u)),
                       3.946 - .052 * abs(u) ** 1.65 + .006 * math.sin(u * 7)))

    def lower_gum(u):
        return Vector((u * .142, -.416 + .083 * abs(u) ** 1.3,
                       3.389 + .118 * abs(u) ** 1.7))

    for fun, name in ((upper_gum, 'Upper vascular gum'), (lower_gum, 'Lower torn gum')):
        points = [fun(-1 + 2 * i / 32) for i in range(33)]
        addtube(name, points, [.010 + .003 * math.sin(i * 1.87) ** 2
                              for i in range(33)], blood, group='dental arcade')

    def tooth(name, root, tip, radius, depth):
        """Swept asymmetric blade with a hooked, slightly rotated tip."""
        axis = (tip - root).normalized()
        side = axis.cross(Vector((0, 1, 0))).normalized()
        front = axis.cross(side).normalized()
        vv, ff = [], []
        nr, ns = 9, 9
        twist = rng.uniform(-.36, .36)
        for j in range(nr):
            t = j / (nr - 1)
            center = root.lerp(tip, t)
            center.y -= .017 * math.sin(math.pi * t)
            r = max(.0003, radius * (1 - t) ** .78)
            for i in range(ns):
                a = i * math.tau / ns + twist * t
                edge = 1 + .08 * math.cos(a * 3)
                vv.append(center + side * (math.cos(a) * r * edge)
                          + front * (math.sin(a) * r * depth))
        for j in range(nr - 1):
            for i in range(ns):
                a = j * ns + i
                b = j * ns + (i + 1) % ns
                ff.append((a, b, b + ns, a + ns))
        ff.append(tuple(reversed(range(ns))))
        ff.append(tuple((nr - 1) * ns + i for i in range(ns)))
        groups['dental arcade'].append(mesh(name, vv, ff, bone))

    # Deliberate irregularity in sockets, missing teeth and alternating hooked
    # canines.  The secondary arcade is shorter and lies behind the first.
    for row in (0, 1, 2):
        count = (19, 15, 11)[row]
        for i in range(count):
            if (row, i) in ((0, 5), (1, 10), (2, 3)):
                continue
            u = -1 + 2 * i / (count - 1) + rng.uniform(-.025, .025)
            u = max(-.98, min(.98, u))
            p = upper_gum(u) if row != 1 else lower_gum(u)
            canine = (row == 0 and i in (2, 15)) or (row == 1 and i in (2, 12))
            length = rng.uniform(.055, .105) + (.055 if canine else 0)
            if row == 2:
                p.y += .037
                p.z -= .004
                length *= .7
            tip = p + Vector((-p.x * rng.uniform(.10, .24) + rng.uniform(-.009, .009),
                              -.018 - rng.uniform(.005, .025),
                              length if row == 1 else -length))
            tooth('Irregular hooked tooth', p, tip,
                  rng.uniform(.008, .0125) * (1.2 if canine else 1),
                  rng.uniform(.63, .83))

    tongue_points = [(0, -.111, 3.654), (.008, -.268, 3.535),
                     (.025, -.453, 3.452), (.035, -.673, 3.424),
                     (.074, -.887, 3.435), (.125, -1.065, 3.490),
                     (.151, -1.194, 3.593), (.128, -1.251, 3.694)]
    tongue = addtube('TONGUE | long tapering muscular whip', tongue_points,
                     [.028, .048, .050, .038, .029, .023, .013, .0015],
                     tongue_mat,
                     depths=[.025, .030, .025, .021, .018, .014, .009, .0012])
    # The groove follows the visible dorsal surface, with secondary fiber lines.
    for off in (-.016, 0, .016):
        points = []
        for k, p in enumerate(tongue_points[1:-1], 1):
            v = Vector(p)
            v.x += off * (1 - (k / 9))
            v.z += [.031, .026, .021, .018, .014, .009][k - 1] * .87
            points.append(v)
        addtube('Longitudinal tongue sulcus', points,
                [.0013] * (len(points) - 1) + [.0004],
                blood if off else throat, group='tongue detail')
    # Tiny uneven papillae cluster near the broad proximal tongue, rather than
    # turning the distal tip into a row of beads.
    for k in range(30):
        t = rng.uniform(.07, .94)
        p = Vector(tongue_points[2]).lerp(Vector(tongue_points[4]), t)
        p.x += rng.uniform(-.021, .021) * (1 - t * .4)
        p.z += .022 * (1 - t * .2)
        tip = p + Vector((0, -.001, rng.uniform(.002, .004)))
        addtube('Tongue papilla', [p, tip], [.0018, .0002],
                tongue_mat, group='tongue detail')

    for side in (-1, 1):
        addtube('Adhesive saliva at oral commissure',
                [(side * .167, -.298, 3.892), (side * .156, -.336, 3.741),
                 (side * .126, -.378, 3.559), (side * .091, -.401, 3.467)],
                [.0029, .0011, .0016, .0025], saliva, group='oral wetness')
        addtube('Torn dark saliva filament',
                [(side * .073, -.322, 3.881), (side * .059, -.359, 3.733),
                 (side * .050, -.400, 3.606)],
                [.0024, .0008, .0021], saliva, group='oral wetness')
    addtube('Saliva trailing from tongue',
            [(.084, -.93, 3.448), (.08, -.93, 3.349), (.074, -.929, 3.303)],
            [.0029, .001, .0023], saliva, group='oral wetness')

    # Combine small details into a handful of organized editable assemblies.
    for name, parts in groups.items():
        if parts:
            ob = join(parts, 'HEAD DETAIL | ' + name)
            bloodflow(ob, .15)
            objects.append(ob)
    for ob in objects:
        bpy.ops.object.select_all(action='DESELECT')
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        if ob.type == 'MESH':
            for poly in ob.data.polygons:
                poly.use_smooth = True
        ob['anatomical_region'] = 'cervical head and upper sternum'
        ob.select_set(False)
    head['design_note'] = 'Eyeless cervical head. The oral assembly is never pelvic.'
    return {'objects': objects, 'head': head, 'jaw': jaw, 'tongue': tongue,
            'tongue_points': tongue_points,
            'bone_head': (0, .065, 3.64), 'bone_tail': (0, -.015, 4.14),
            'jaw_head': (0, -.105, 3.905), 'jaw_tail': (0, -.427, 3.351)}
