"""Three planar grass cards with a triangular footprint; CC0 source texture."""
import bpy, math, json, traceback
from pathlib import Path
from mathutils import Vector, Quaternion
ROOT=Path(__file__).resolve().parent.parent
P=ROOT/'Assets/Models/GrassCards'
def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene=bpy.context.scene;scene.name='Grass | three-plane triangle'
    image=bpy.data.images.load(str(ROOT/'Tools/GrassSources/Pack01/grass_01/diffus.tga'))
    image.name='Grass_Blade_Cutout_CC0';image.alpha_mode='STRAIGHT'
    alpha=list(image.pixels)[3::4]
    if min(alpha)>.1 or max(alpha)<.5:raise RuntimeError('Source texture has no usable transparency')
    image.filepath_raw=str(P/'Grass_Blade_Cutout.png');image.file_format='PNG';image.save();image.pack()
    mat=bpy.data.materials.new('Grass | double-sided alpha cutout');mat.use_nodes=True;mat.diffuse_color=(.22,.31,.105,1);mat.use_backface_culling=False
    if hasattr(mat,'surface_render_method'):mat.surface_render_method='DITHERED'
    n=mat.node_tree.nodes;l=mat.node_tree.links;n.clear()
    out=n.new('ShaderNodeOutputMaterial');out.location=(420,0)
    bs=n.new('ShaderNodeBsdfPrincipled');bs.location=(140,0);bs.inputs['Roughness'].default_value=.8;bs.inputs['Specular IOR Level'].default_value=.22
    tex=n.new('ShaderNodeTexImage');tex.location=(-420,70);tex.image=image;tex.extension='CLIP';tex.interpolation='Linear'
    # A hard alpha cutout avoids sorting artifacts between overlapping cards.
    threshold=n.new('ShaderNodeMath');threshold.operation='GREATER_THAN';threshold.inputs[1].default_value=.35;threshold.location=(-100,-170)
    l.new(tex.outputs['Color'],bs.inputs['Base Color']);l.new(tex.outputs['Alpha'],threshold.inputs[0]);l.new(threshold.outputs[0],bs.inputs['Alpha']);l.new(bs.outputs[0],out.inputs['Surface'])
    verts=[];faces=[];uvs=[];width=.80;height=.72;radius=width/(2*math.sqrt(3))
    # Three vertical sides of an equilateral triangle. No solid volume or ground cap.
    for i in range(3):
        a=math.tau*i/3;normal=Vector((math.cos(a),math.sin(a),0));tangent=Vector((-math.sin(a),math.cos(a),0));center=normal*radius
        left=center-tangent*width/2;right=center+tangent*width/2
        k=len(verts);verts.extend([left,right,right+Vector((0,0,height)),left+Vector((0,0,height))]);faces.append((k,k+1,k+2,k+3))
        uvs.extend([(0,0),(1,0),(1,1),(0,1)] if i!=1 else [(1,0),(0,0),(0,1),(1,1)])
    data=bpy.data.meshes.new('Grass | 3 quads - 6 triangles');data.from_pydata(verts,[],faces);data.update();ob=bpy.data.objects.new('Grass_Triangle_3Planes',data);scene.collection.objects.link(ob);data.materials.append(mat)
    uv=data.uv_layers.new(name='Grass UV')
    for poly in data.polygons:
        for li in poly.loop_indices:uv.data[li].uv=uvs[data.loops[li].vertex_index]
    for i in range(3):group=ob.vertex_groups.new(name='Plane_%02d'%(i+1));group.add(list(range(i*4,i*4+4)),1,'REPLACE')
    ob['description']='Three vertical grass cards on an equilateral triangular footprint. 12 vertices, 3 quads, 6 triangles. Origin at ground center.'
    ob['texture_source']='Yughues / Nobiax, Grass Pack #01, CC0; https://opengameart.org/content/grass-pack-01'
    ob.asset_mark();ob.asset_data.description=ob['description'];ob.asset_data.author='Mesh: project asset; texture: Yughues / Nobiax (CC0)'
    bpy.context.view_layer.objects.active=ob;ob.select_set(True)
    # Export only the foliage mesh, excluding the inspection stage.
    bpy.ops.export_scene.fbx(filepath=str(P/'Grass_Triangle_3Planes.fbx'),use_selection=True,object_types={'MESH'},axis_forward='-Z',axis_up='Y',apply_unit_scale=True,use_mesh_modifiers=True,mesh_smooth_type='OFF',use_triangles=True,add_leaf_bones=False,path_mode='COPY',embed_textures=True)
    # Saved authoring scene stays minimal; presentation is a separate scene.
    preview=bpy.data.scenes.new('Preview | grass cutout');preview.collection.objects.link(ob);bpy.context.window.scene=preview
    world=bpy.data.worlds.new('Soft neutral surroundings');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.18,.20,.23,1);world.node_tree.nodes['Background'].inputs[1].default_value=.6;preview.world=world
    bpy.ops.mesh.primitive_plane_add(size=200);floor=bpy.context.object;floor.name='Preview ground only';floor.location.z=-.006
    ground=bpy.data.materials.new('Preview charcoal soil');ground.diffuse_color=(.06,.065,.055,1);ground.use_nodes=True;ground.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.06,.065,.055,1);ground.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.95;floor.data.materials.append(ground)
    def aim(o,p):o.rotation_euler=(Vector(p)-o.location).to_track_quat('-Z','Y').to_euler()
    bpy.ops.object.camera_add(location=(1.15,-1.85,1.08));cam=bpy.context.object;aim(cam,(0,0,.32));cam.data.type='ORTHO';cam.data.ortho_scale=1.18;preview.camera=cam
    for loc,power,size in [((-1,-2,3),180,3),((1,1,2),140,2)]:
        bpy.ops.object.light_add(type='AREA',location=loc);light=bpy.context.object;light.data.energy=power;light.data.size=size;aim(light,(0,0,.25))
    preview.render.engine='CYCLES';preview.cycles.samples=48;preview.cycles.use_denoising=True;preview.cycles.transparent_max_bounces=16
    try:
        prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
        for d in prefs.devices:d.use=d.type=='OPTIX'
        if any(d.type=='OPTIX' for d in prefs.devices):preview.cycles.device='GPU'
    except Exception:pass
    preview.render.resolution_x=1100;preview.render.resolution_y=1100;preview.render.resolution_percentage=100;preview.render.image_settings.file_format='PNG';preview.render.filepath=str(P/'Grass_Preview.png')
    bpy.context.window.scene=scene;scene.unit_settings.system='METRIC';bpy.context.view_layer.objects.active=ob;ob.select_set(True)
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=='VIEW_3D':
                space=area.spaces.active;space.shading.type='MATERIAL';space.region_3d.view_rotation=cam.rotation_euler.to_quaternion();space.region_3d.view_location=(0,0,.33);space.region_3d.view_distance=1.6
    note=bpy.data.texts.new('README | Grass cards');note.write('Three planes in a triangular footprint, 6 triangles, ground-centered pivot. Texture packed. Source: Yughues (Nobiax), Grass Pack #01, https://opengameart.org/content/grass-pack-01, CC0. Unity HDRP: use HDRP/Lit with Base Map Grass_Blade_Cutout.png, Alpha Clipping enabled (0.35), Double-Sided enabled, Smoothness 0.2. FBX exports only grass, not preview stage.')
    bpy.ops.wm.save_as_mainfile(filepath=str(P/'Grass_Triangle_3Planes.blend'))
    report={'vertices':len(data.vertices),'quads':len(data.polygons),'triangles':sum(len(p.vertices)-2 for p in data.polygons),'planes':3,'height_m':height,'triangle_side_m':width,'alpha_min':min(alpha),'alpha_max':max(alpha),'transparent_pixel_fraction':sum(a<.35 for a in alpha)/len(alpha),'texture_size':list(image.size),'texture_packed':bool(image.packed_file),'origin':list(ob.location),'double_sided':not mat.use_backface_culling}
    assert report['triangles']==6 and report['texture_packed'] and report['double_sided']
    (P/'Validation.json').write_text(json.dumps(report,indent=2))
    bpy.context.window.scene=preview;bpy.ops.render.render(write_still=True)
    (P/'Complete.txt').write_text('Saved Blender asset, FBX, transparent texture and verified rendered preview.')
try:build()
except Exception:(P/'Error.txt').write_text(traceback.format_exc());raise
