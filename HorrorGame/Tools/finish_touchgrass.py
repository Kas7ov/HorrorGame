import bpy
from pathlib import Path
from mathutils import Vector
import json
ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / 'ArtSource/Grass/TouchGrass_Editable.blend'
assert not DEST.exists()
scene = bpy.context.scene
cards = list(bpy.data.collections['GRASS | three editable curved cards'].objects)
assert len(cards) == 3
image = bpy.data.images['Grass cutout | packed RGBA']
points = [o.matrix_world @ v.co for o in cards for v in o.data.vertices]
center = sum(points, Vector()) / len(points)
extent = max((p - center).length for p in points)
rotation = Vector((1.25, -2.1, 0.95)).to_track_quat('Z', 'Y')
source = (ROOT / 'Tools/recover_touchgrass.py').read_text(encoding='utf-8')
exec(compile(source[source.index("scene.render.engine ="):], 'finish_recovery', 'exec'))
