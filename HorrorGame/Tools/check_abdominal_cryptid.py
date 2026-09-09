"""Read-only Blender validation of the saved cryptid; writes only QA.json.

Run using Blender's background Python mode after the asset build has finished.
This checks the saved geometry and guide, not production readiness or art quality.
"""
import json
import math
import re
import traceback
from pathlib import Path

import bpy
from mathutils import Vector


ASSET_DIR = Path(__file__).resolve().parents[1] / "Assets" / "Models" / "AbdominalCryptid"
ASSET_FILE = ASSET_DIR / "AbdominalCryptid.blend"
REPORT_FILE = ASSET_DIR / "QA.json"
EPSILON = 1e-5


def coordinates(value):
    return [round(float(component), 7) for component in value]


def components(obj):
    """Count actual vertex-edge islands without changing the mesh."""
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
    for index in range(len(parents)):
        group = root(index)
        counts[group] = counts.get(group, 0) + 1
    sizes = sorted(counts.values(), reverse=True)
    return {
        "object": obj.name,
        "vertices": len(obj.data.vertices),
        "polygons": len(obj.data.polygons),
        "component_count": len(sizes),
        "component_sizes": sizes,
    }


def world_bounds(obj):
    corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    return {
        "min": [min(point[axis] for point in corners) for axis in range(3)],
        "max": [max(point[axis] for point in corners) for axis in range(3)],
    }


def distance_to_segment(point, start, end):
    vector = end - start
    if vector.length_squared < EPSILON ** 2:
        return (point - start).length
    weight = max(0.0, min(1.0, (point - start).dot(vector) / vector.length_squared))
    return (point - start - weight * vector).length


def inspect():
    bpy.ops.wm.open_mainfile(filepath=str(ASSET_FILE))
    failures = []
    checks = {}

    def check(name, passed, details=None):
        checks[name] = {"passed": bool(passed)}
        if details is not None:
            checks[name]["details"] = details
        if not passed:
            failures.append(name)

    neutral = bpy.data.scenes.get("01 | Neutral rigging source")
    cinematic = bpy.data.scenes.get("02 | Sewer backward crawl")
    check("required_scenes", neutral is not None and cinematic is not None)
    if neutral is None or cinematic is None:
        return {"asset": str(ASSET_FILE), "passed": False, "scenes": list(bpy.data.scenes.keys()), "checks": checks, "failures": failures}

    # Objects in inactive scenes can retain unevaluated identity world matrices.
    # Evaluate each scene before inspecting transforms in that scene.
    bpy.context.window.scene = neutral
    bpy.context.view_layer.update()

    rig = next((obj for obj in neutral.objects if obj.type == "ARMATURE" and obj.name.startswith("RIG_Cryptid")), None)
    check("neutral_rig_present", rig is not None)
    if rig is not None:
        bones = rig.data.bones
        head = bones.get("abdomen_head")
        jaw = bones.get("mandible")
        check("abdominal_head_parent", head is not None and head.parent is not None and head.parent.name == "pelvis", {"parent": head.parent.name if head and head.parent else None})
        check("mandible_parent", jaw is not None and jaw.parent == head)

        def endpoints(name):
            bone = bones.get(name)
            if bone is None:
                return None
            return rig.matrix_world @ bone.head_local, rig.matrix_world @ bone.tail_local

        root_points = endpoints("root")
        head_points = endpoints("abdomen_head")
        jaw_points = endpoints("mandible")
        foot_points = {side: endpoints("foot." + side) for side in ("L", "R")}
        check("native_up_positive_z", root_points is not None and (root_points[1] - root_points[0]).normalized().dot(Vector((0, 0, 1))) > .999)
        check("native_front_negative_y", all(points is not None and points[1].y < points[0].y - EPSILON for points in foot_points.values()) and head_points is not None and head_points[1].y < head_points[0].y and jaw_points is not None and jaw_points[1].y < jaw_points[0].y, {
            "evidence": "World-space head, mandible, and both foot bones extend toward -Y.",
            "head_direction": coordinates(head_points[1] - head_points[0]) if head_points else None,
            "foot_directions": {side: coordinates(points[1] - points[0]) if points else None for side, points in foot_points.items()},
        })
        check("head_hangs_down_from_abdomen", head_points is not None and head_points[1].z < head_points[0].z)

        tongue_bones = sorted((bone for bone in bones if bone.name.startswith("tongue.")), key=lambda bone: bone.name)
        check("five_tongue_segments", len(tongue_bones) == 5, {"names": [bone.name for bone in tongue_bones]})
        hierarchy_ok = bool(tongue_bones)
        endpoint_gaps = []
        for index, bone in enumerate(tongue_bones):
            expected_parent = jaw if index == 0 else tongue_bones[index - 1]
            hierarchy_ok = hierarchy_ok and bone.parent == expected_parent
            if index:
                endpoint_gaps.append((bone.head_local - tongue_bones[index - 1].tail_local).length)
        check("continuous_tongue_chain", hierarchy_ok and all(gap < EPSILON for gap in endpoint_gaps), {"joint_gaps": endpoint_gaps})
        tongue = next((obj for obj in neutral.objects if obj.type == "MESH" and obj.name.startswith("TONGUE |")), None)
        distances = []
        if tongue is not None and tongue_bones:
            segments = [(rig.matrix_world @ bone.head_local, rig.matrix_world @ bone.tail_local) for bone in tongue_bones]
            distances = [min(distance_to_segment(tongue.matrix_world @ vertex.co, start, end) for start, end in segments) for vertex in tongue.data.vertices]
        check("tongue_geometry_covered_by_chain", bool(distances) and max(distances) < .10, {
            "tongue_object": tongue.name if tongue else None,
            "max_surface_distance_to_chain": max(distances) if distances else None,
            "tolerance": .10,
            "last_bone_tip": coordinates(rig.matrix_world @ tongue_bones[-1].tail_local) if tongue_bones else None,
        })

    eye_names = [obj.name for obj in bpy.data.objects if obj.type == "MESH" and re.search(r"\b(?:eyes?|eyeballs?|ocular|iris|pupils?)\b", obj.name, re.IGNORECASE)]
    check("no_named_eye_geometry", not eye_names, {"matches": eye_names, "scope": "Name inventory only; not a visual anatomical test. Eyeless is not treated as an eye object."})

    for label, prefix in (("body", "CRYPTID |"), ("head", "HEAD |")):
        obj = next((item for item in neutral.objects if item.type == "MESH" and item.name.startswith(prefix)), None)
        data = components(obj) if obj is not None else {"object": None}
        check(label + "_single_connected_component", obj is not None and data["component_count"] == 1, data)

    transform_rows = []
    transform_failures = []
    for obj in neutral.objects:
        if obj.type not in {"MESH", "ARMATURE"}:
            continue
        _, rotation, scale = obj.matrix_world.decompose()
        rotation_error = abs(rotation.angle)
        rotation_error = min(rotation_error, abs(2 * math.pi - rotation_error))
        ok = rotation_error < EPSILON and max(abs(value - 1.0) for value in scale) < EPSILON
        transform_rows.append({"object": obj.name, "world_rotation_degrees": round(math.degrees(rotation_error), 8), "world_scale": coordinates(scale), "passed": ok})
        if not ok:
            transform_failures.append(obj.name)
    check("neutral_applied_rotation_and_scale", not transform_failures, {"checked_objects": len(transform_rows), "failures": transform_failures, "objects": transform_rows})

    bpy.context.window.scene = cinematic
    bpy.context.view_layer.update()

    left = cinematic.objects.get("Left sewer wall")
    right = cinematic.objects.get("Right sewer wall")
    floor = cinematic.objects.get("Floor")
    ceiling = cinematic.objects.get("Ceiling")
    camera = cinematic.camera
    corridor = None
    inside = False
    if all(obj is not None for obj in (left, right, floor, ceiling, camera)):
        lb, rb, fb, cb = [world_bounds(obj) for obj in (left, right, floor, ceiling)]
        corridor = {"min": [lb["max"][0], max(lb["min"][1], rb["min"][1]), fb["max"][2]], "max": [rb["min"][0], min(lb["max"][1], rb["max"][1]), cb["min"][2]]}
        location = camera.matrix_world.translation
        inside = all(corridor["min"][axis] + EPSILON < location[axis] < corridor["max"][axis] - EPSILON for axis in range(3))
    check("cinematic_camera_inside_corridor", inside, {"camera": camera.name if camera else None, "position": coordinates(camera.matrix_world.translation) if camera else None, "interior_bounds": corridor})

    bad_geometry = []
    vertex_count = 0
    mesh_objects = [obj for obj in bpy.data.objects if obj.type == "MESH"]
    for obj in mesh_objects:
        bad_count = 0
        bad_examples = []
        matrix_valid = all(math.isfinite(value) for row in obj.matrix_world for value in row)
        for vertex in obj.data.vertices:
            vertex_count += 1
            local_valid = all(math.isfinite(value) for value in vertex.co)
            world_valid = matrix_valid and local_valid and all(math.isfinite(value) for value in obj.matrix_world @ vertex.co)
            if not local_valid or not world_valid:
                bad_count += 1
                if len(bad_examples) < 5:
                    bad_examples.append(vertex.index)
        if bad_count or not matrix_valid:
            bad_geometry.append({"object": obj.name, "invalid_vertices": bad_count, "sample_indices": bad_examples, "matrix_finite": matrix_valid})
    check("all_geometry_finite", not bad_geometry, {"mesh_objects_checked": len(mesh_objects), "vertices_checked": vertex_count, "invalid_geometry": bad_geometry})

    return {"asset": str(ASSET_FILE), "passed": not failures, "scenes": list(bpy.data.scenes.keys()), "checks": checks, "failures": failures, "limitations": ["Armature is an unweighted guide; this does not validate animation deformation.", "Connected-component checks do not establish production retopology or manifoldness.", "Visual quality and final lighting require rendered-image review."]}


try:
    report = inspect()
except Exception:
    report = {"asset": str(ASSET_FILE), "passed": False, "exception": traceback.format_exc()}
    REPORT_FILE.write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    raise
REPORT_FILE.write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
print("Cryptid QA: " + ("PASS" if report["passed"] else "FAIL") + " | " + str(REPORT_FILE))
if not report["passed"]:
    raise RuntimeError("Cryptid validation failed: " + ", ".join(report.get("failures", [])))
