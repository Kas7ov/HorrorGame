import bpy
from pathlib import Path

root = Path(__file__).resolve().parent.parent
dest = root / 'ArtSource/Grass/BettermadeGrass_SingleMesh.blend'
fbx = root / 'ArtSource/Grass/BettermadeGrass_SingleMesh.fbx'
assert not dest.exists() and not fbx.exists(), 'Refusing to overwrite existing single mesh'
source_scene = bpy.context.scene
if bpy.context.object and bpy.context.object.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')
parent = source_scene.objects.get('BettermadeGrass')
assert parent is not None
panels = [o for o in parent.children_recursive if o.type == 'MESH']
assert len(panels) == 3, f'Expected 3 grass panels, found {len(panels)}'
vertices, faces, uv_faces = [], [], []
material = None
depsgraph = bpy.context.evaluated_depsgraph_get()
for panel in panels:
    evaluated = panel.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    offset = len(vertices)
    vertices.extend([evaluated.matrix_world @ v.co for v in mesh.vertices])
    assert mesh.uv_layers.active is not None
    for face in mesh.polygons:
        face_material = panel.material_slots[face.material_index].material
        if material is None:
            material = face_material
        assert face_material == material, 'Panel materials differ; cannot silently collapse them'
        faces.append(tuple(offset + i for i in face.vertices))
        uv_faces.append([tuple(mesh.uv_layers.active.data[i].uv) for i in face.loop_indices])
    evaluated.to_mesh_clear()
scene = bpy.data.scenes.new('BettermadeGrass | ONE mesh')
scene.world = source_scene.world
scene.unit_settings.system = 'METRIC'
data = bpy.data.meshes.new('BettermadeGrass_SingleMesh')
data.from_pydata(vertices, [], faces)
data.update()
uv = data.uv_layers.new(name='Grass UV')
for poly, values in zip(data.polygons, uv_faces):
    for index, value in zip(poly.loop_indices, values):
        uv.data[index].uv = value
data.materials.append(material)
obj = bpy.data.objects.new('BettermadeGrass', data)
scene.collection.objects.link(obj)
bpy.context.window.scene = scene
obj.select_set(True)
bpy.context.view_layer.objects.active = obj
assert len(scene.objects) == 1 and len(data.materials) == 1
assert len(data.vertices) == len(vertices) and len(data.polygons) == len(faces)
bpy.ops.export_scene.fbx(filepath=str(fbx), use_selection=True, object_types={'MESH'}, axis_forward='-Z', axis_up='Y', apply_unit_scale=True, apply_scale_options='FBX_SCALE_UNITS', add_leaf_bones=False, bake_anim=False, path_mode='AUTO')
if bpy.context.area and bpy.context.area.type == 'CONSOLE':
    bpy.context.area.type = 'VIEW_3D'
    bpy.context.area.spaces.active.shading.type = 'MATERIAL'
bpy.ops.wm.save_as_mainfile(filepath=str(dest))
# Verify the exported FBX by importing into a temporary inspection scene.
check = bpy.data.scenes.new('VERIFY | single FBX mesh')
bpy.context.window.scene = check
bpy.ops.import_scene.fbx(filepath=str(fbx))
imported = [o for o in check.objects if o.type == 'MESH']
assert len(imported) == 1, 'FBX must contain exactly one mesh'
assert len(imported[0].data.materials) == 1
bpy.context.window.scene = scene
print('VERIFIED: exported FBX contains exactly one mesh and one material slot')
