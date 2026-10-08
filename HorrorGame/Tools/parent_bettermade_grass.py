import bpy
from pathlib import Path

root = Path(__file__).resolve().parent.parent
destination = root / 'ArtSource/Grass/BettermadeGrass.blend'
fbx = root / 'ArtSource/Grass/BettermadeGrass.fbx'
assert not destination.exists() and not fbx.exists(), 'Refusing to overwrite existing final grass'
scene = bpy.context.scene
if bpy.context.object and bpy.context.object.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')
panels = [scene.objects.get(f'Grass Panel {i}') for i in (1,2,3)]
assert all(o and o.type == 'MESH' for o in panels)
assert scene.objects.get('BettermadeGrass') is None
before = {o.name: [o.matrix_world @ v.co for v in o.data.vertices] for o in panels}
parent = bpy.data.objects.new('BettermadeGrass', None)
scene.collection.objects.link(parent)
parent.empty_display_type = 'PLAIN_AXES'
parent.empty_display_size = .2
for panel in panels:
    world = panel.matrix_world.copy()
    panel.parent = parent
    panel.matrix_world = world
bpy.context.view_layer.update()
for panel in panels:
    after = [panel.matrix_world @ v.co for v in panel.data.vertices]
    assert all((a-b).length < 1e-6 for a,b in zip(before[panel.name], after))
bpy.ops.object.select_all(action='DESELECT')
for obj in [parent] + panels:
    obj.select_set(True)
bpy.context.view_layer.objects.active = parent
bpy.ops.export_scene.fbx(filepath=str(fbx), use_selection=True, object_types={'EMPTY','MESH'}, axis_forward='-Z', axis_up='Y', add_leaf_bones=False, bake_anim=False, path_mode='AUTO')
bpy.ops.object.select_all(action='DESELECT')
parent.select_set(True)
if bpy.context.area and bpy.context.area.type == 'CONSOLE':
    bpy.context.area.type = 'VIEW_3D'
    bpy.context.area.spaces.active.shading.type = 'MATERIAL'
bpy.ops.wm.save_as_mainfile(filepath=str(destination))
print('BettermadeGrass: 3 children; all world-space vertices unchanged; blend and FBX saved')
