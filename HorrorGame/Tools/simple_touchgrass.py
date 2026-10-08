import bpy
import math
from pathlib import Path
from mathutils import Vector

root = Path(__file__).resolve().parent.parent
destination = root / 'ArtSource/Grass/TouchGrass_SimpleTriangle.blend'
assert not destination.exists(), 'Simple version already exists; do not overwrite'
scene = bpy.data.scenes.new('Grass | 3 flat panels in a triangle')
bpy.context.window.scene = scene
scene.unit_settings.system = 'METRIC'
scene.world = bpy.data.worlds.new('Grass simple world')
scene.world.color = (.15, .15, .15)
material = bpy.data.materials['Grass | double-sided cutout']
width, height = .80, .72
radius = width / (2 * math.sqrt(3))
panels = []
for i in range(3):
    a = 2 * math.pi * i / 3
    normal = Vector((math.cos(a), math.sin(a), 0))
    tangent = Vector((-math.sin(a), math.cos(a), 0))
    middle = normal * radius
    left, right = middle - tangent * width / 2, middle + tangent * width / 2
    mesh = bpy.data.meshes.new(f'Panel {i+1} | single quad')
    mesh.from_pydata([left, right, right + Vector((0,0,height)), left + Vector((0,0,height))], [], [(0,1,2,3)])
    mesh.update()
    uv = mesh.uv_layers.new(name='Grass UV')
    for loop, coord in zip(uv.data, [(0,0),(1,0),(1,1),(0,1)]):
        loop.uv = coord
    obj = bpy.data.objects.new(f'Grass Panel {i+1}', mesh)
    scene.collection.objects.link(obj)
    mesh.materials.append(material)
    obj.select_set(True)
    panels.append(obj)
bpy.context.view_layer.objects.active = panels[0]
area = bpy.context.area
if area and area.type == 'CONSOLE':
    area.type = 'VIEW_3D'
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == 'VIEW_3D':
            space = area.spaces.active
            space.shading.type = 'MATERIAL'
            space.region_3d.view_location = (0,0,height/2)
            space.region_3d.view_distance = 1.9
            space.region_3d.view_rotation = Vector((1.25,-2.1,.95)).to_track_quat('Z','Y')
assert len(scene.objects) == 3
assert sum(len(o.data.vertices) for o in panels) == 12
assert sum(len(o.data.polygons) for o in panels) == 3
bpy.ops.wm.save_as_mainfile(filepath=str(destination))
