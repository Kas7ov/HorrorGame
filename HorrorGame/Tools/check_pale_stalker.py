"""Read-only inspection of the saved Pale Stalker Blender asset.

Open the saved file, evaluate each scene before reading world-space transforms,
and write QA.json only. No geometry, weights, materials, or .blend file is saved.
Passing these checks does not establish production topology or visual quality.
"""

import json
import math
import re
import traceback
from pathlib import Path

import bpy
from mathutils import Vector


ASSET_DIR = Path(__file__).resolve().parents[1] / "Assets" / "Models" / "PaleStalker"
ASSET_FILE = ASSET_DIR / "PaleStalker.blend"
REPORT_FILE = ASSET_DIR / "QA.json"
EPSILON = 1e-5


def xyz(value):
    return [round(float(component), 7) for component in value]


def activate(scene):
    # Inactive-scene object matrices may not yet have been evaluated on load.
    bpy.context.window.scene = scene
    bpy.context.view_layer.update()


def components(obj):
    parents = list(range(len(obj.data.vertices)))

    def root(index):
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    for edge in obj.data.edges:
        first, second = map(root, edge.vertices)
        if first != second:
            parents[second] = first
    counts = {}
    roots = []
    for index in range(len(parents)):
        group = root(index)
        roots.append(group)
        counts[group] = counts.get(group, 0) + 1
    sizes = sorted(counts.values(), reverse=True)
    return {
        "object": obj.name,
        "vertices": len(obj.data.vertices),
        "polygons": len(obj.data.polygons),
        "component_count": len(sizes),
        "component_sizes": sizes,
    }, roots


def bounds(obj):
    corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    return {"min": [min(p[i] for p in corners) for i in range(3)],
            "max": [max(p[i] for p in corners) for i in range(3)]}


def is_inside(point, box):
    return all(box["min"][i] + EPSILON < point[i] < box["max"][i] - EPSILON
               for i in range(3))


def inspect():
    bpy.ops.wm.open_mainfile(filepath=str(ASSET_FILE))
    failures, checks = [], {}

    def check(name, passed, details=None):
        checks[name] = {"passed": bool(passed)}
        if details is not None:
            checks[name]["details"] = details
        if not passed:
            failures.append(name)

    neutral = next((s for s in bpy.data.scenes if s.name.startswith("01 |")), None)
    cinema = next((s for s in bpy.data.scenes if s.name.startswith("02 |")), None)
    check("two_required_scenes", neutral is not None and cinema is not None,
          {"scenes": list(bpy.data.scenes.keys())})
    if neutral is None or cinema is None:
        return {"asset": str(ASSET_FILE), "passed": False,
                "checks": checks, "failures": failures}
    activate(neutral)
    model = [o for o in neutral.objects if o.type == "MESH"]
    check("neutral_mesh_model_present", bool(model), {"mesh_objects": len(model)})

    body = next((o for o in model if o.name.startswith("BODY |")), None)
    body_components, roots = components(body) if body else ({}, [])
    check("body_single_connected_component", body is not None and
          body_components.get("component_count") == 1, body_components)
    if body:
        # A remesh may leave disconnected shoulder islands. Sample eight bins
        # along each torso-to-upper-arm bridge and compare their graph roots.
        shoulders = {}
        all_bridges = True
        for side, sign in (("L", 1), ("R", -1)):
            bins = [[] for _ in range(8)]
            connected_roots = set()
            for vertex in body.data.vertices:
                p = body.matrix_world @ vertex.co
                x = sign * p.x
                if .28 <= x < .64 and 3.10 <= p.z <= 3.54 and -.22 <= p.y <= .33:
                    index = min(7, int((x - .28) / .36 * 8))
                    bins[index].append(vertex.index)
                    connected_roots.add(roots[vertex.index])
            counts = [len(bucket) for bucket in bins]
            okay = all(count > 0 for count in counts) and len(connected_roots) == 1
            all_bridges = all_bridges and okay
            shoulders[side] = {"occupied_bins": counts,
                               "connected_components_sampled": len(connected_roots),
                               "passed": okay}
        check("shoulder_bridges_connected_and_occupied", all_bridges,
              {"shoulders": shoulders,
               "scope": "Vertex-edge continuity and bridge occupancy, not a visual seam-quality claim."})

    head_collection = next((c for c in bpy.data.collections if c.name.startswith("HEAD |")), None)
    cranial = [o for o in head_collection.all_objects if o.type == "MESH"] if head_collection else []
    cranial_bounds = []
    for obj in cranial:
        z_values = [(obj.matrix_world @ vertex.co).z for vertex in obj.data.vertices]
        if z_values:
            cranial_bounds.append({"object": obj.name, "min_z": min(z_values), "max_z": max(z_values)})
    minimum_head_z = min((row["min_z"] for row in cranial_bounds), default=None)
    check("all_cranial_and_oral_geometry_above_3_25m", minimum_head_z is not None and
          minimum_head_z >= 3.25 - EPSILON,
          {"minimum_z": minimum_head_z, "threshold_z": 3.25,
           "cranial_meshes": cranial_bounds})
    primary_head = next((o for o in cranial if o.name.startswith("HEAD |")), None)
    head_components, _ = components(primary_head) if primary_head else ({}, [])
    check("primary_cranium_single_connected_component", primary_head is not None and
          head_components.get("component_count") == 1, head_components)

    oral_pattern = re.compile(r"\b(?:mouth|jaw|tongue|dental|teeth|tooth|pharyn\w*|saliva|palatal|cranial)\b", re.I)
    low_oral_names = []
    oral_mesh_count = 0
    for obj in model:
        if not oral_pattern.search(obj.name):
            continue
        oral_mesh_count += 1
        low = min(((obj.matrix_world @ v.co).z for v in obj.data.vertices), default=999)
        if low < 3.25 - EPSILON:
            low_oral_names.append({"object": obj.name, "min_z": low})
    check("no_named_oral_geometry_at_pelvis", oral_mesh_count > 0 and not low_oral_names,
          {"oral_meshes_checked": oral_mesh_count, "low_objects": low_oral_names,
           "scope": "Collection bounds plus oral-name inventory; rendered inspection remains required."})

    rig = next((o for o in neutral.objects if o.type == "ARMATURE"), None)
    check("aligned_guide_present", rig is not None)
    if rig:
        bones = rig.data.bones
        head, neck, jaw, pelvis = [bones.get(name) for name in ("head", "neck", "jaw", "pelvis")]
        check("head_parent_is_neck", head is not None and neck is not None and head.parent == neck,
              {"head_parent": head.parent.name if head and head.parent else None})
        check("jaw_parent_is_head", jaw is not None and jaw.parent == head)

        def points(name):
            bone = bones.get(name)
            return ((rig.matrix_world @ bone.head_local, rig.matrix_world @ bone.tail_local)
                    if bone else None)

        root = points("root")
        up = root[1] - root[0] if root else Vector((0, 0, 0))
        check("guide_up_positive_z", up.length > EPSILON and
              up.normalized().dot(Vector((0, 0, 1))) > .999, {"root_direction": xyz(up)})
        feet = {side: points("foot." + side) for side in ("L", "R")}
        check("guide_feet_forward_negative_y", all(p is not None and p[1].y < p[0].y - .1
              for p in feet.values()), {"foot_directions": {side: xyz(p[1] - p[0]) if p else None
                                                            for side, p in feet.items()}})
        head_points, jaw_points = points("head"), points("jaw")
        check("guide_head_and_jaw_above_chest", all(p is not None and min(p[0].z, p[1].z) >= 3.25
              for p in (head_points, jaw_points)),
              {"head_endpoints": [xyz(p) for p in head_points] if head_points else None,
               "jaw_endpoints": [xyz(p) for p in jaw_points] if jaw_points else None})
        pelvis_z = max((rig.matrix_world @ pelvis.head_local).z,
                       (rig.matrix_world @ pelvis.tail_local).z) if pelvis else None
        check("cranial_pelvis_separation", pelvis_z is not None and minimum_head_z is not None and
              minimum_head_z - pelvis_z >= 1.0,
              {"pelvis_top_z": pelvis_z, "cranial_minimum_z": minimum_head_z,
               "vertical_separation": minimum_head_z - pelvis_z if pelvis_z is not None and minimum_head_z is not None else None})

        tongue_bones = sorted((b for b in bones if b.name.startswith("tongue.")), key=lambda b: b.name)
        chain_ok = len(tongue_bones) >= 5
        gaps = []
        for index, bone in enumerate(tongue_bones):
            chain_ok = chain_ok and bone.parent == (tongue_bones[index - 1] if index else jaw)
            if index:
                gaps.append((bone.head_local - tongue_bones[index - 1].tail_local).length)
        check("continuous_tongue_guide", chain_ok and all(g < EPSILON for g in gaps),
              {"bone_count": len(tongue_bones), "joint_gaps": gaps})

    eye_names = [o.name for o in model if re.search(r"\b(?:eyes?|eyeballs?|ocular|iris|pupils?)\b", o.name, re.I)]
    check("no_named_eye_geometry", not eye_names,
          {"matches": eye_names, "scope": "Names only. The word eyeless is not an eye object."})

    transform_failures, weight_rows, invalid_geometry = [], [], []
    vertices_checked = 0
    for obj in model + ([rig] if rig else []):
        matrix = obj.matrix_world
        error = max(abs(matrix[i][j] - (1.0 if i == j else 0.0))
                    for i in range(4) for j in range(4))
        if not math.isfinite(error) or error > EPSILON:
            transform_failures.append({"object": obj.name, "matrix_max_identity_error": error})
        if obj.type != "MESH":
            continue
        weighted_vertices = 0
        bad_vertices = []
        matrix_finite = all(math.isfinite(value) for row in matrix for value in row)
        for vertex in obj.data.vertices:
            vertices_checked += 1
            weighted_vertices += int(any(group.weight > EPSILON for group in vertex.groups))
            if not matrix_finite or not all(math.isfinite(value) for value in vertex.co) or not all(math.isfinite(value) for value in matrix @ vertex.co):
                if len(bad_vertices) < 10:
                    bad_vertices.append(vertex.index)
        if bad_vertices or not matrix_finite:
            invalid_geometry.append({"object": obj.name, "sample_bad_vertices": bad_vertices,
                                     "world_matrix_finite": matrix_finite})
        armature_modifiers = [mod.name for mod in obj.modifiers if mod.type == "ARMATURE"]
        armature_parent = obj.parent.name if obj.parent and obj.parent.type == "ARMATURE" else None
        if weighted_vertices or armature_modifiers or armature_parent:
            weight_rows.append({"object": obj.name, "weighted_vertices": weighted_vertices,
                                "armature_modifiers": armature_modifiers,
                                "armature_parent": armature_parent})
    check("model_and_guide_transforms_identity", not transform_failures,
          {"objects_checked": len(model) + int(rig is not None), "failures": transform_failures})
    check("model_vertices_finite", not invalid_geometry,
          {"vertices_checked": vertices_checked, "invalid_geometry": invalid_geometry})
    actual_unweighted = not weight_rows
    status_text = str(rig.get("status", "")) if rig else ""
    documented_unweighted = "unweighted" in status_text.lower()
    check("unweighted_guide_status_is_honest", actual_unweighted and documented_unweighted,
          {"actual_unweighted": actual_unweighted, "guide_status": status_text,
           "weighted_or_armature_bound_objects": weight_rows,
           "meaning": "This is a sculpt with an aligned guide, not a skinned animation-ready character."})

    # Compare datablock identity, not merely names, across the authoring and
    # cinematic scenes. Both views must show the same editable model.
    missing, mismatched = [], []
    for obj in model:
        other = cinema.objects.get(obj.name)
        if other is None:
            missing.append(obj.name)
        elif other != obj or other.data != obj.data:
            mismatched.append(obj.name)
    check("both_scenes_share_identical_model_objects_and_data", not missing and not mismatched,
          {"model_objects_checked": len(model), "missing_in_cinema": missing,
           "different_object_or_mesh_datablocks": mismatched})

    activate(cinema)
    camera = cinema.camera
    left, right, floor = [cinema.objects.get(name) for name in ("Left wall", "Right wall", "Wet corridor floor")]
    aperture, camera_info = None, {"camera": camera.name if camera else None}
    camera_safe = False
    if all(o is not None for o in (camera, left, right, floor)):
        lb, rb, fb = [bounds(o) for o in (left, right, floor)]
        aperture = {"min": [lb["max"][0], max(lb["min"][1], rb["min"][1]), fb["max"][2]],
                    "max": [rb["min"][0], min(lb["max"][1], rb["max"][1]), min(lb["max"][2], rb["max"][2])]}
        location = camera.matrix_world.translation
        camera_safe = all(aperture["min"][axis] + EPSILON < location[axis] < aperture["max"][axis] - EPSILON
                          for axis in (0, 2)) and not any(is_inside(location, box) for box in (lb, rb, fb))
        camera_info.update({"world_position": xyz(location), "corridor_interior_bounds": aperture,
                            "inside_longitudinal_extent": aperture["min"][1] <= location.y <= aperture["max"][1],
                            "front_entrance_setback": max(0.0, aperture["min"][1] - location.y),
                            "scope": "Camera must remain within lateral/vertical aperture and outside wall/floor solids. A position just in front of the open entrance is allowed."})
    check("cinematic_camera_clear_of_walls_and_floor", camera_safe, camera_info)

    environment_bad, environment_count = [], 0
    model_set = set(model)
    for obj in cinema.objects:
        if obj.type != "MESH" or obj in model_set:
            continue
        matrix_finite = all(math.isfinite(value) for row in obj.matrix_world for value in row)
        bad = not matrix_finite
        for vertex in obj.data.vertices:
            environment_count += 1
            bad = bad or not all(math.isfinite(value) for value in vertex.co)
        if bad:
            environment_bad.append(obj.name)
    check("cinematic_environment_vertices_finite", not environment_bad,
          {"vertices_checked": environment_count, "invalid_objects": environment_bad})

    return {"asset": str(ASSET_FILE), "passed": not failures,
            "checks": checks, "failures": failures,
            "limitations": ["The character is unweighted; no deformation or animation test is claimed.",
                            "Connectivity does not establish manifoldness, production retopology, UVs, or game-ready topology.",
                            "Eye absence, wound integration, shoulder seam quality, and realism require rendered visual inspection.",
                            "No .blend file was altered by this validator."]}


def serializable(value):
    # Failed finite-value checks must themselves still produce a valid report.
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if isinstance(value, dict):
        return {key: serializable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [serializable(item) for item in value]
    return value


try:
    report = inspect()
except Exception:
    report = {"asset": str(ASSET_FILE), "passed": False, "exception": traceback.format_exc()}
    REPORT_FILE.write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    raise
REPORT_FILE.write_text(json.dumps(serializable(report), indent=2, allow_nan=False), encoding="utf-8")
print("Pale Stalker QA: " + ("PASS" if report["passed"] else "FAIL") + " | " + str(REPORT_FILE))
if not report["passed"]:
    raise RuntimeError("Pale Stalker validation failed: " + ", ".join(report.get("failures", [])))
