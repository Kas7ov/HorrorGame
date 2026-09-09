import bpy, json
from pathlib import Path
from mathutils import Vector
P=Path(r'E:\EpsteinHorror\HorrorGame\Assets\Models\UncannyMaskMonster')
bpy.ops.wm.open_mainfile(filepath=str(P/'Hollowmaw_Sculpt.blend'))
body=bpy.data.objects.get('HOLLOWMAW | unified sculpt skin')
rig=bpy.data.objects.get('RIG_Hollowmaw | -Y front')
mandible=bpy.data.objects.get('MANDIBLE | angular lower jaw')
tongue=bpy.data.objects.get('TONGUE | wet curled tongue')
required_objects={
    'HOLLOWMAW | unified sculpt skin':body,
    'RIG_Hollowmaw | -Y front':rig,
    'MANDIBLE | angular lower jaw':mandible,
    'TONGUE | wet curled tongue':tongue,
}
missing=[name for name,obj in required_objects.items() if obj is None]
assert not missing, 'Missing required objects: '+', '.join(missing)
assert all(obj.type=='MESH' for obj in (body,mandible,tongue)), 'Body, mandible and tongue must be meshes'
assert rig.type=='ARMATURE', 'The guide must be an armature'
required_bones=['foot.L','foot.R','jaw','tongue.01','tongue.02','tongue.03']
missing_bones=[name for name in required_bones if name not in rig.data.bones]
assert not missing_bones, 'Missing required bones: '+', '.join(missing_bones)
adj=[[] for v in body.data.vertices]
for e in body.data.edges:
    a,b=e.vertices;adj[a].append(b);adj[b].append(a)
seen=set();components=[]
for v in body.data.vertices:
    if v.index in seen:continue
    todo=[v.index];seen.add(v.index);island=[]
    while todo:
        i=todo.pop();island.append(i)
        for j in adj[i]:
            if j not in seen:seen.add(j);todo.append(j)
    components.append(island)
tiny=[i for c in components if len(c)<100 for i in c]
if tiny:
    import bmesh
    bm=bmesh.new();bm.from_mesh(body.data);bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm,geom=[bm.verts[i] for i in tiny],context='VERTS');bm.to_mesh(body.data);bm.free()
    components=[c for c in components if len(c)>=100]
bpy.ops.object.select_all(action='DESELECT');body.select_set(True);bpy.context.view_layer.objects.active=body
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.region_3d.view_perspective='ORTHO'
            area.spaces.active.shading.type='MATERIAL'
report=json.loads((P/'Hollowmaw_Validation.json').read_text())
report['vertices']=len(body.data.vertices);report['faces']=len(body.data.polygons)
report['bones']=len(rig.data.bones)
report['required_objects_present']={name:obj is not None for name,obj in required_objects.items()}
report['required_bones_present']={name:name in rig.data.bones for name in required_bones}
report['tiny_remesh_fragments_removed']=len(tiny)
report['skin_connected_components']=sorted([len(c) for c in components],reverse=True)
report['native_mesh_rotation']=list(body.rotation_euler)
report['native_armature_rotation']=list(rig.rotation_euler)
report['native_mesh_scale']=list(body.scale)
report['native_armature_scale']=list(rig.scale)
report['forward_check']={n:list(rig.data.bones[n].tail_local) for n in ['foot.L','foot.R','jaw']}
report['mouth_bones']={}
for name in ['jaw','tongue.01','tongue.02','tongue.03']:
    bone=rig.data.bones[name]
    report['mouth_bones'][name]={
        'head_local':list(bone.head_local),
        'tail_local':list(bone.tail_local),
        'head_world':list(rig.matrix_world @ bone.head_local),
        'tail_world':list(rig.matrix_world @ bone.tail_local),
        'length':bone.length,
        'parent':bone.parent.name if bone.parent else None,
    }
report['mouth_meshes']={}
for obj in (mandible,tongue):
    corners=[obj.matrix_world @ Vector(point) for point in obj.bound_box]
    report['mouth_meshes'][obj.name]={
        'vertices':len(obj.data.vertices),
        'faces':len(obj.data.polygons),
        'world_bounds_min':[min(point[axis] for point in corners) for axis in range(3)],
        'world_bounds_max':[max(point[axis] for point in corners) for axis in range(3)],
        'world_origin':list(obj.matrix_world.translation),
    }
assert rig.data.bones['foot.L'].tail_local.y<0
assert rig.data.bones['foot.R'].tail_local.y<0
assert len(rig.data.bones)==44, 'Expected 41 original guide bones plus 3 tongue bones'
assert len(components)==1, 'The body must form one connected skin surface'
assert all(len(obj.data.vertices)>0 and len(obj.data.polygons)>0 for obj in (mandible,tongue)), 'Jaw and tongue geometry must not be empty'
assert rig.data.bones['tongue.01'].parent==rig.data.bones['jaw'], 'The tongue root must be parented to the jaw'
for name in ['tongue.01','tongue.02','tongue.03']:
    bone=rig.data.bones[name]
    assert bone.length>0.0001, 'Tongue bones must have nonzero length: '+name
    assert rig.data.bones['jaw'] in bone.parent_recursive, 'Every tongue bone must descend from the jaw: '+name
report['jaw_and_tongue_separate_meshes']=True
report['checks_passed']=True
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Hollowmaw_Sculpt.blend'))
bpy.ops.wm.save_as_mainfile(filepath=str(P/'UncannyMaskMonster.blend'))
(P/'Hollowmaw_Validation.json').write_text(json.dumps(report,indent=2))
