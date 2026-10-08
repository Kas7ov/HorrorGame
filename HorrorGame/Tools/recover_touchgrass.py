"""Recover grass authoring file without touching Unity's FBX or materials."""
import bpy
import json
import math
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'ArtSource' / 'Grass'
OUT.mkdir(parents=True, exist_ok=True)
DEST = OUT / 'TouchGrass_Editable.blend'
if DEST.exists():
    raise RuntimeError('Refusing to overwrite existing authoring file')
# Keep the user's existing scene intact when run in an open Blender window.
scene = bpy.data.scenes.new('TouchGrass | editable curved cards')
bpy.context.window.scene = scene
bpy.ops.import_scene.fbx(filepath=str(ROOT / 'Assets/Models/GrassCards/TourchGrass.fbx'))
scene = bpy.context.scene
scene.name = 'TouchGrass | editable curved cards'
scene.unit_settings.system = 'METRIC'
meshes = [o for o in scene.objects if o.type == 'MESH']
assert meshes, 'No mesh found in source FBX'
original = bpy.data.collections.new('REFERENCE | original FBX (hidden)')
scene.collection.children.link(original)
editable = bpy.data.collections.new('GRASS | three editable curved cards')
scene.collection.children.link(editable)
for obj in meshes:
    backup = obj.copy()
    backup.data = obj.data.copy()
    original.objects.link(backup)
    backup.name = 'Original FBX | unmodified'
    for col in list(obj.users_collection):
        col.objects.unlink(obj)
    editable.objects.link(obj)
original.hide_viewport = True
original.hide_render = True
bpy.ops.object.select_all(action='DESELECT')
for obj in meshes:
    obj.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
if len(meshes) > 1:
    bpy.ops.object.join()
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.separate(type='LOOSE')
bpy.ops.object.mode_set(mode='OBJECT')
cards = list(editable.objects)
assert len(cards) == 3, f'Expected three cards, found {len(cards)}'

image = bpy.data.images.load(str(ROOT / 'Assets/Models/GrassCards/Grass_Blade_Cutout.png'))
image.name = 'Grass cutout | packed RGBA'
image.alpha_mode = 'STRAIGHT'
image.pack()
mat = bpy.data.materials.new('Grass | double-sided cutout')
mat.use_nodes = True
mat.use_backface_culling = False
if hasattr(mat, 'surface_render_method'):
    mat.surface_render_method = 'DITHERED'
nodes = mat.node_tree.nodes
nodes.clear()
output = nodes.new('ShaderNodeOutputMaterial')
output.location = (480, 0)
bsdf = nodes.new('ShaderNodeBsdfPrincipled')
bsdf.location = (140, 0)
bsdf.inputs['Roughness'].default_value = 0.8
bsdf.inputs['Specular IOR Level'].default_value = 0.2
texture = nodes.new('ShaderNodeTexImage')
texture.location = (-460, 80)
texture.image = image
texture.extension = 'CLIP'
cut = nodes.new('ShaderNodeMath')
cut.operation = 'GREATER_THAN'
cut.inputs[1].default_value = 0.13
cut.location = (-160, -180)
links = mat.node_tree.links
links.new(texture.outputs['Color'], bsdf.inputs['Base Color'])
links.new(texture.outputs['Alpha'], cut.inputs[0])
links.new(cut.outputs[0], bsdf.inputs['Alpha'])
links.new(bsdf.outputs[0], output.inputs['Surface'])
for i, obj in enumerate(sorted(cards, key=lambda ob: ob.name)):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    obj.name = f'Grass Card {i + 1:02d} | curved overlapping plane'
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    coords = [v.co.copy() for v in obj.data.vertices]
    bottom = min(v.z for v in coords)
    height = max(v.z for v in coords) - bottom
    assert height > 0.1
    center = sum(coords, Vector()) / len(coords)
    normal = obj.data.polygons[0].normal.copy()
    normal.z = 0
    normal.normalize()
    tangent = Vector((-normal.y, normal.x, 0))
    projections = [(v - center).dot(tangent) for v in coords]
    width = max(projections) - min(projections)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.tris_convert_to_quads()
    bpy.ops.mesh.subdivide(number_cuts=7, smoothness=0)
    bpy.ops.object.mode_set(mode='OBJECT')
    for vertex in obj.data.vertices:
        sideways = (vertex.co - center).dot(tangent)
        u = sideways / width + 0.5
        v = (vertex.co.z - bottom) / height
        # Wider cards cross their neighbours; a shallow bow softens the flat silhouette.
        vertex.co += tangent * sideways * 0.16
        vertex.co += normal * (width * 0.09 * math.sin(math.pi * u) * (0.3 + 0.7 * v))
        vertex.co += tangent * (width * 0.035 * v * v * (-1 if i == 1 else 1))
    obj.data.update()
    for face in obj.data.polygons:
        face.use_smooth = True
    obj['source'] = 'TourchGrass.fbx; original preserved in hidden REFERENCE collection'
    obj['editing'] = 'Tab: edit this card. Proportional Editing (O) for gentle curvature.'

bpy.ops.object.select_all(action='DESELECT')
for card in cards:
    card.select_set(True)
bpy.context.view_layer.objects.active = cards[0]
points = [o.matrix_world @ v.co for o in cards for v in o.data.vertices]
center = sum(points, Vector()) / len(points)
extent = max((p - center).length for p in points)
rotation = Vector((1.25, -2.1, 0.95)).to_track_quat('Z', 'Y')
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == 'VIEW_3D':
            space = area.spaces.active
            space.shading.type = 'MATERIAL'
            space.overlay.show_extras = False
            space.region_3d.view_location = center
            space.region_3d.view_distance = max(extent * 3.5, 1.5)
            space.region_3d.view_rotation = rotation
scene.render.engine = 'BLENDER_EEVEE'
if scene.world is None:
    scene.world = bpy.data.worlds.new('Grass neutral world')
scene.world.color = (0.15, 0.15, 0.15)
note = bpy.data.texts.new('README | edit and export')
note.write('Three individually editable, subdivided grass cards. Shallow curves and 16% additional width create overlapping edges. Original imported FBX is preserved in the hidden REFERENCE collection. Texture is packed. Select a card and press Tab to edit its vertices; O toggles proportional editing. Export only the three visible cards, using Selected Objects. Unity FBX, textures, scenes and materials have NOT been changed. Texture: Yughues/Nobiax Grass Pack 01, CC0.\n')
if bpy.context.area and bpy.context.area.type == 'CONSOLE':
    bpy.context.area.type = 'VIEW_3D'
    space = bpy.context.area.spaces.active
    space.shading.type = 'MATERIAL'
    space.region_3d.view_location = center
    space.region_3d.view_distance = max(extent * 3.5, 1.5)
    space.region_3d.view_rotation = rotation
bpy.ops.wm.save_as_mainfile(filepath=str(DEST))
report = {'file': str(DEST), 'cards': len(cards), 'vertices': sum(len(o.data.vertices) for o in cards), 'faces': sum(len(o.data.polygons) for o in cards), 'texture_packed': bool(image.packed_file), 'source_preserved': True}
print('GRASS_RECOVERY ' + json.dumps(report))
