"""Native Blender sculpt construction. All mesh and rig coordinates are Z-up, -Y forward."""
import bpy, math, random, json, traceback, shutil
from pathlib import Path
from mathutils import Vector, Quaternion
P=Path(r'E:\EpsteinHorror\HorrorGame\Assets\Models\UncannyMaskMonster')
random.seed(28)

def material(name, color, rough=.5):
    m=bpy.data.materials.new(name); m.diffuse_color=(*color,1); m.use_nodes=True
    b=m.node_tree.nodes.get('Principled BSDF'); b.inputs['Base Color'].default_value=(*color,1); b.inputs['Roughness'].default_value=rough
    return m

def mesh(name, verts, faces, mat=None):
    d=bpy.data.meshes.new(name); d.from_pydata(verts,[],faces); d.update()
    o=bpy.data.objects.new(name,d); bpy.context.collection.objects.link(o)
    if mat: d.materials.append(mat)
    for f in d.polygons: f.use_smooth=True
    return o

def ell(name, c, s, mat=None):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32,ring_count=20,location=c)
    o=bpy.context.object; o.name=name; o.scale=s
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if mat:o.data.materials.append(mat)
    for f in o.data.polygons:f.use_smooth=True
    return o

def tube(name, coords, widths, depths=None, mat=None, sides=16):
    pts=[Vector(p) for p in coords]; verts=[]; faces=[]
    if depths is None:depths=widths
    for i,p in enumerate(pts):
        t=(pts[min(i+1,len(pts)-1)]-pts[max(i-1,0)]).normalized()
        u=t.cross(Vector((0,1,0))).normalized()
        if u.length<.1:u=Vector((1,0,0))
        v=t.cross(u).normalized()
        for j in range(sides):
            a=j*2*math.pi/sides
            q=p+u*math.cos(a)*widths[i]+v*math.sin(a)*depths[i]
            verts.append(q)
    for i in range(len(pts)-1):
        for j in range(sides):
            a=i*sides+j;b=i*sides+(j+1)%sides
            faces.append((a,b,b+sides,a+sides))
    faces.append(tuple(reversed(range(sides))))
    faces.append(tuple((len(pts)-1)*sides+j for j in range(sides)))
    o=mesh(name,verts,faces,mat)
    # Ensure a consistent outward orientation before Boolean/remesh operations.
    bpy.context.view_layer.objects.active=o;o.select_set(True)
    import bmesh
    bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(o.data);bm.free()
    o.select_set(False)
    return o

def join(objects,name):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:o.select_set(True)
    bpy.context.view_layer.objects.active=objects[0];bpy.ops.object.join()
    o=bpy.context.object;o.name=name;return o

def apply(o,mod):
    bpy.context.view_layer.objects.active=o;bpy.ops.object.modifier_apply(modifier=mod.name)

def aim(o,p):o.rotation_euler=(Vector(p)-o.location).to_track_quat('-Z','Y').to_euler()

def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    skin=material('SKIN | ashen dermis, mottled capillaries',(.40,.32,.30),.48)
    nodes=skin.node_tree.nodes;links=skin.node_tree.links;b=nodes.get('Principled BSDF')
    b.inputs['Subsurface Weight'].default_value=.08
    noise=nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=5.8;noise.inputs['Detail'].default_value=5
    geo=nodes.new('ShaderNodeNewGeometry');links.new(geo.outputs['Position'],noise.inputs['Vector'])
    ramp=nodes.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].position=.18;ramp.color_ramp.elements[0].color=(.35,.28,.28,1)
    ramp.color_ramp.elements[1].position=.82;ramp.color_ramp.elements[1].color=(.72,.65,.55,1)
    links.new(noise.outputs['Fac'],ramp.inputs[0])
    red=nodes.new('ShaderNodeValToRGB');red.color_ramp.elements[0].position=.15;red.color_ramp.elements[0].color=(.08,.007,.023,1)
    red.color_ramp.elements[1].position=.85;red.color_ramp.elements[1].color=(.37,.065,.075,1)
    links.new(noise.outputs['Fac'],red.inputs[0])
    attr=nodes.new('ShaderNodeAttribute');attr.attribute_name='perfusion'
    mix=nodes.new('ShaderNodeMixRGB');links.new(attr.outputs['Fac'],mix.inputs[0]);links.new(ramp.outputs[0],mix.inputs[1]);links.new(red.outputs[0],mix.inputs[2]);links.new(mix.outputs[0],b.inputs['Base Color'])
    pores=nodes.new('ShaderNodeTexNoise');pores.inputs['Scale'].default_value=145;pores.inputs['Detail'].default_value=3
    links.new(geo.outputs['Position'],pores.inputs['Vector'])
    bump=nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.3;bump.inputs['Distance'].default_value=.013
    links.new(pores.outputs['Fac'],bump.inputs['Height']);links.new(bump.outputs[0],b.inputs['Normal'])
    bone=material('TEETH | old ivory',(.56,.46,.28),.32)
    wet=material('MAW | wet burgundy',(.065,.008,.016),.24)
    nail=material('CLAWS | dark horn',(.065,.037,.028),.3)
    gum=material('GUMS | vascular lip tissue',(.18,.027,.037),.35)
    tongue_mat=material('TONGUE | living crimson',(.39,.047,.081),.22)
    tn=tongue_mat.node_tree.nodes;tl=tongue_mat.node_tree.links
    grain=tn.new('ShaderNodeTexNoise');grain.inputs['Scale'].default_value=38;grain.inputs['Detail'].default_value=2
    tb=tn.new('ShaderNodeBump');tb.inputs['Strength'].default_value=.24;tb.inputs['Distance'].default_value=.006
    tl.new(grain.outputs['Fac'],tb.inputs['Height']);tl.new(tb.outputs[0],tn.get('Principled BSDF').inputs['Normal'])
    flesh=[];hard=[];details=[];chains={}
    def form(name,c,w,d=None):
        if d is None:d=list(w)
        # Support rings retain the full attachment width when smoothing a loft.
        # Without them subdivision rounds off the ends and pinches the joints.
        c=[c[0],tuple(Vector(c[0]).lerp(Vector(c[1]),.08))]+c[1:-1]+[tuple(Vector(c[-2]).lerp(Vector(c[-1]),.92)),c[-1]]
        w=[w[0],w[0]*.92+w[1]*.08]+w[1:-1]+[w[-2]*.08+w[-1]*.92,w[-1]]
        d=[d[0],d[0]*.92+d[1]*.08]+d[1:-1]+[d[-2]*.08+d[-1]*.92,d[-1]]
        o=tube(name,c,w,d,skin)
        sub=o.modifiers.new('Round anatomical cross sections','SUBSURF');sub.levels=2;apply(o,sub)
        flesh.append(o);return o
    # A varying cross-section, with a narrow waist and broad thorax, establishes the whole torso.
    form('Torso continuous',[(0,.02,1.79),(0,.04,2.1),(0,.06,2.35),(0,.10,2.6),(0,.13,2.9),(0,.16,3.2),(0,.19,3.45),(0,.16,3.73)],
         [.15,.36,.30,.255,.38,.51,.54,.21],[.17,.24,.22,.215,.26,.28,.24,.17])
    form('Neck and trapezius',[(0,.17,3.4),(0,.16,3.67),(0,.09,3.86),(0,0,4.13)],[.31,.25,.155,.16],[.20,.20,.155,.16])
    # Elongated blind cranial dome; mouth is carved into this connected head volume.
    form('Blind cranial vault',[(0,-.055,4.025),(0,-.085,4.13),(0,-.07,4.33),(0,.015,4.50),(0,.06,4.58)],
         [.22,.28,.275,.20,.045],[.205,.265,.27,.21,.05])
    for s,side in [(1,'L'),(-1,'R')]:
        def mirror(p):return (s*p[0],p[1],p[2])
        sh=mirror((.58,.1,3.43));el=mirror((1.02,.03,2.98));wr=mirror((1.4,-.015,2.49))
        chains[side]=(sh,el,wr)
        flesh.append(ell('Elbow tissue bridge.'+side,el,(.105,.105,.125),skin))
        flesh.append(ell('Wrist tissue bridge.'+side,wr,(.087,.078,.095),skin))
        form('Deltoid to elbow.'+side,[mirror(p) for p in [(.48,.13,3.45),(.66,.12,3.46),(.78,.06,3.29),(.9,.01,3.13),(1.02,.03,2.98)]],
             [.185,.202,.164,.12,.10],[.18,.195,.165,.12,.10])
        form('Forearm tendon taper.'+side,[el,mirror((1.12,.045,2.89)),mirror((1.22,.035,2.72)),wr],[.10,.135,.105,.068],[.105,.12,.095,.061])
        palm=mirror((1.49,-.02,2.33))
        form('Palm.'+side,[wr,palm,mirror((1.53,-.025,2.19))],[.074,.145,.13],[.065,.067,.055])
        for i in range(4):
            x=1.415+i*.077
            coords=[mirror((x,-.027,2.23)),mirror((x+(i-1.5)*.022,-.04,2.06)),mirror((x+(i-1.5)*.045,-.06,1.9+(abs(i-1.5)*.045))),mirror((x+(i-1.5)*.045,-.105,1.82+abs(i-1.5)*.045))]
            form('Long finger %s.%s'%(i,side),coords,[.038,.032,.025,.015])
            end=Vector(coords[-1]);hard.append(tube('Hooked nail %s.%s'%(i,side),[coords[-2],end,end+Vector((s*.015,-.10,-.11))],[.027,.025,.001],mat=nail,sides=10))
        form('Opposing thumb.'+side,[mirror((1.4,-.02,2.37)),mirror((1.3,-.025,2.23)),mirror((1.28,-.08,2.09))],[.06,.045,.024])
        hard.append(tube('Thumb claw.'+side,[mirror((1.28,-.08,2.09)),mirror((1.29,-.16,2.0))],[.029,.001],mat=nail,sides=10))
        hip=mirror((.28,.04,2.05));knee=mirror((.4,-.075,1.19));ank=mirror((.45,.045,.32))
        flesh.append(ell('Knee tissue bridge.'+side,knee,(.12,.12,.14),skin))
        flesh.append(ell('Ankle tissue bridge.'+side,ank,(.09,.10,.12),skin))
        form('Thigh sculpt.'+side,[mirror((.235,.05,2.18)),hip,mirror((.34,.03,1.88)),mirror((.39,-.03,1.62)),mirror((.40,-.065,1.37)),knee],
             [.145,.205,.212,.172,.127,.112],[.145,.205,.215,.18,.14,.12])
        form('Shin calf.'+side,[knee,mirror((.42,.08,1.05)),mirror((.44,.13,.85)),mirror((.45,.1,.62)),ank],
             [.115,.13,.13,.085,.061],[.12,.155,.14,.09,.075])
        form('Ankle and foot.'+side,[ank,mirror((.45,-.07,.16)),mirror((.45,-.26,.12)),mirror((.45,-.40,.10))],[.073,.13,.16,.13],[.09,.105,.095,.06])
        for i in range(3):
            x=.33+i*.12
            form('Toe %s.%s'%(i,side),[mirror((x,-.3,.12)),mirror((x,-.51,.08)),mirror((x,-.61,.08))],[.061,.043,.028])
            hard.append(tube('Foot talon %s.%s'%(i,side),[mirror((x,-.55,.09)),mirror((x,-.69,.065)),mirror((x,-.76,.045))],[.038,.02,.001],mat=nail,sides=10))
        # Pectoral fans and serratus ridges become part of the fused dermis.
        for i in range(4):
            z=3.25-i*.125
            width=.43-i*.025
            form('Serratus fold',[mirror((.13,-.09,z)),mirror((.24,-.075,z-.08)),mirror((width*.85,-.045,z-.005)),mirror((width,.03,z+.1))],
                 [.018,.023,.022,.018],[.015,.019,.019,.015])
        for i in range(3):
            form('Pectoral fan',[mirror((.045,-.05,3.47-i*.048)),mirror((.25,-.10,3.43-i*.07)),mirror((.48,.01,3.44))],[.026,.04,.021],[.025,.032,.02])
        # Sculpted longitudinal muscle boundaries, kept shallow and fused.
        for offset in [-.06,.045]:
            form('Quadriceps ridge',[mirror((.29+offset,-.13,1.99)),mirror((.36+offset,-.17,1.74)),mirror((.40,-.17,1.30))],[.023,.031,.012])
        form('Tibial crest',[mirror((.4,-.16,1.18)),mirror((.44,-.02,.83)),mirror((.45,-.025,.39))],[.026,.023,.013])
        for i in range(3):
            form('Forearm cord',[mirror((1.035+i*.03,-.06,2.98-i*.035)),mirror((1.23+i*.022,-.095,2.72)),mirror((1.4,-.05,2.5))],[.022,.018,.007])
        # Scapular ridges give the rear silhouette its own anatomy.
        form('Scapula',[mirror((.13,.30,3.43)),mirror((.31,.35,3.31)),mirror((.28,.31,2.98))],[.034,.045,.016])
    for i in range(12):
        z=2.26+i*.105
        flesh.append(ell('Vertebral ridge',(0,.325+(.07 if z>2.9 else -.06),z),(.056,.075,.055),skin))
    body=join(flesh,'HOLLOWMAW | unified sculpt skin')
    rem=body.modifiers.new('Fuse anatomy into continuous skin','REMESH');rem.mode='VOXEL';rem.voxel_size=.014;rem.use_smooth_shade=True;apply(body,rem)
    sm=body.modifiers.new('Blend tissue transitions','SMOOTH');sm.factor=1.0;sm.iterations=8;apply(body,sm)
    # The maw is a real recess, with flesh thickness and a separate dark throat.
    cut=ell('Temporary mouth cutter',(0,-.27,3.88),(.244,.29,.285))
    mod=body.modifiers.new('Carved jaw opening','BOOLEAN');mod.operation='DIFFERENCE';mod.object=cut;apply(body,mod);bpy.data.objects.remove(cut,do_unlink=True)
    details.append(ell('Recessed throat',(0,-.135,3.86),(.208,.105,.265),wet))
    jaw_path=[(-.232,.02,4.085),(-.235,-.02,3.9),(-.18,-.18,3.67),(-.09,-.28,3.58),(0,-.31,3.55),(.09,-.28,3.58),(.18,-.18,3.67),(.235,-.02,3.9),(.232,.02,4.085)]
    jaw=tube('MANDIBLE | angular lower jaw',jaw_path,[.061,.068,.06,.067,.07,.067,.06,.068,.061],mat=skin,sides=20)
    sub=jaw.modifiers.new('Smooth mandibular ridge','SUBSURF');sub.levels=2;apply(jaw,sub);details.append(jaw)
    top=[];bottom=[]
    for i in range(19):
        u=-1+2*i/18
        top.append((u*.226,-.25-.075*math.sqrt(max(0,1-u*u)),4.158-.04*u*u))
        bottom.append((u*.163,-.337+.137*abs(u),3.615+.15*abs(u)**1.5))
    details.append(tube('Upper vascular gumline',top,[.022]*19,mat=gum,sides=12))
    details.append(tube('Lower vascular gumline',bottom,[.025]*19,mat=gum,sides=12))
    for row in [0,1]:
        for i in range(17 if row==0 else 13):
            u=-1+2*i/(16 if row==0 else 12)
            lng=random.uniform(.085,.135)+(.035 if i%5==0 else 0)
            if row==0:p=(u*.216,-.25-.075*math.sqrt(max(0,1-u*u)),4.158-.04*u*u)
            else:p=(u*.16,-.337+.137*abs(u),3.615+.15*abs(u)**1.5)
            q=(p[0]*.93+random.uniform(-.008,.008),p[1]-.035,p[2]+(-lng if row==0 else lng*.74))
            hard.append(tube('Maw tooth %s.%02d'%(row,i),[p,((p[0]+q[0])/2,p[1]-.025,(p[2]+q[2])/2),q],[.016,.009,.001],mat=bone,sides=10))
    tongue_points=[(0,-.16,3.79),(0,-.29,3.72),(0,-.48,3.66),(0,-.59,3.73),(0,-.62,3.81)]
    tongue=tube('TONGUE | wet curled tongue',tongue_points,[.051,.067,.055,.038,.003],[.031,.03,.027,.022,.002],mat=tongue_mat,sides=20)
    sub=tongue.modifiers.new('Tongue surface smoothing','SUBSURF');sub.levels=2;apply(tongue,sub);details.append(tongue)
    # Store the red-extremity mask on mesh points so it stays attached while deforming.
    def smoothstep(x):
        t=max(0.,min(1.,x));return t*t*(3-2*t)
    def color_skin(obj):
        att=obj.data.attributes.new(name='perfusion',type='FLOAT',domain='POINT')
        for v in obj.data.vertices:
            p=obj.matrix_world@v.co
            hand=smoothstep((abs(p.x)-1.1)/.40)
            foot=smoothstep((.68-p.z)/.51)
            flank=.21*smoothstep((abs(p.x)-.12)/.52)
            att.data[v.index].value=max(hand,foot,flank)
    color_skin(body);color_skin(jaw)
    # Fine dermal fissures follow the actual skin surface, including muscle curvature.
    from mathutils.bvhtree import BVHTree
    bpy.context.view_layer.update()
    tree=BVHTree.FromObject(body,bpy.context.evaluated_depsgraph_get())
    fissure=material('DERMIS | healed fissures',(.115,.055,.047),.65)
    paths=[[(.23,3.37),(.25,3.3),(.27,3.22),(.25,3.14)],
           [(.69,3.40),(.72,3.33),(.75,3.24),(.79,3.17)],
           [(.12,2.63),(.16,2.55),(.14,2.47),(.18,2.39)],
           [(.32,1.93),(.34,1.84),(.37,1.75),(.34,1.64),(.38,1.54)],
           [(.47,1.83),(.48,1.76),(.46,1.66),(.48,1.57)],
           [(1.13,2.90),(1.17,2.83),(1.22,2.75),(1.27,2.67)],
           [(.42,1.09),(.43,1.0),(.45,.92),(.43,.84)]]
    for s in [-1,1]:
        for j,path in enumerate(paths):
            pts=[]
            for x,z in path:
                p,n,idx,dist=tree.ray_cast(Vector((s*x,-3,z)),Vector((0,1,0)),6)
                if p is not None:pts.append(p+n*.002)
            if len(pts)>1:
                details.append(tube('Healed skin fissure %s.%s'%(s,j),pts,[.0015]+[.0035]*(len(pts)-2)+[.0015],mat=fissure,sides=6))
    # Bone guide is created directly in the very same native coordinates as the body.
    bpy.ops.object.armature_add(enter_editmode=True);rig=bpy.context.object;rig.name='RIG_Hollowmaw | -Y front'
    eb=rig.data.edit_bones;eb.remove(eb[0]);bones={}
    def bn(n,h,t,parent=None):
        b=eb.new(n);b.head=h;b.tail=t
        if parent:b.parent=bones[parent]
        bones[n]=b
    bn('root',(0,0,0),(0,0,.2));bn('pelvis',(0,.04,1.9),(0,.06,2.3),'root')
    bn('spine',(0,.06,2.3),(0,.12,2.85),'pelvis');bn('chest',(0,.12,2.85),(0,.17,3.45),'spine')
    bn('neck',(0,.17,3.45),(0,.08,4.08),'chest');bn('head',(0,.08,4.08),(0,.02,4.54),'neck')
    bn('jaw',(0,.02,4.085),(0,-.31,3.55),'head')
    bn('tongue.01',tongue_points[0],tongue_points[1],'jaw')
    bn('tongue.02',tongue_points[1],tongue_points[2],'tongue.01')
    bn('tongue.03',tongue_points[2],tongue_points[4],'tongue.02')
    for s,side in [(1,'L'),(-1,'R')]:
        sh,el,wr=chains[side]
        bn('clavicle.'+side,(s*.1,.15,3.43),sh,'chest');bn('upper_arm.'+side,sh,el,'clavicle.'+side)
        bn('forearm.'+side,el,wr,'upper_arm.'+side);bn('hand.'+side,wr,(s*1.52,-.025,2.21),'forearm.'+side)
        for i in range(4):
            x=1.415+i*.077
            h=(s*x,-.027,2.23);m=(s*(x+(i-1.5)*.022),-.04,2.06);t=(s*(x+(i-1.5)*.045),-.09,1.84+abs(i-1.5)*.045)
            bn('finger_%s.01.%s'%(i,side),h,m,'hand.'+side);bn('finger_%s.02.%s'%(i,side),m,t,'finger_%s.01.%s'%(i,side))
        bn('thumb.'+side,(s*1.4,-.02,2.37),(s*1.28,-.08,2.09),'hand.'+side)
        bn('thigh.'+side,(s*.28,.04,2.05),(s*.4,-.075,1.19),'pelvis')
        bn('shin.'+side,(s*.4,-.075,1.19),(s*.45,.045,.32),'thigh.'+side)
        bn('foot.'+side,(s*.45,.045,.32),(s*.45,-.4,.10),'shin.'+side)
        bn('toes.'+side,(s*.45,-.4,.10),(s*.45,-.66,.08),'foot.'+side)
    bpy.ops.object.mode_set(mode='OBJECT');rig.show_in_front=True;rig.data.display_type='OCTAHEDRAL'
    rig['status']='Aligned unweighted guide; retopology and production weights still required.'
    # Set a useful front view in every viewport. All objects have identity rotation/scale.
    bpy.ops.object.select_all(action='DESELECT');body.select_set(True);bpy.context.view_layer.objects.active=body
    for screen in bpy.data.screens:
        for a in screen.areas:
            if a.type=='VIEW_3D':
                a.spaces.active.region_3d.view_rotation=Quaternion((1,0,0),math.pi/2)
                a.spaces.active.region_3d.view_distance=7;a.spaces.active.region_3d.view_location=(0,0,2.2)
                a.spaces.active.shading.color_type='MATERIAL'
    old=P/'UncannyMaskMonster.blend';backup=P/'UncannyMaskMonster_BlockoutBackup.blend'
    if old.exists() and not backup.exists():shutil.copy2(old,backup)
    before=P/'Hollowmaw_BeforeJawRevision.blend'
    if (P/'Hollowmaw_Sculpt.blend').exists() and not before.exists():shutil.copy2(P/'Hollowmaw_Sculpt.blend',before)
    bpy.ops.wm.save_as_mainfile(filepath=str(P/'Hollowmaw_Sculpt.blend'))
    bpy.ops.wm.save_as_mainfile(filepath=str(old))
    report={'vertices':len(body.data.vertices),'faces':len(body.data.polygons),'bones':len(rig.data.bones),'front':'-Y','up':'+Z','weighted':False,'topology':'voxel fused sculpt; production retopology required'}
    (P/'Hollowmaw_Validation.json').write_text(json.dumps(report,indent=2))
    # Rendering is performed only after saving the clean asset.
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24
    scene.cycles.use_denoising=True;scene.render.resolution_x=900;scene.render.resolution_y=1050;scene.render.resolution_percentage=100
    scene.world=bpy.data.worlds.new('Studio');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.025,.032,.04,1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value=.25
    for loc,power,col,size in [((3,-5,6),700,(.83,.89,1),4),((-3,-2,3),420,(1,.72,.52),3),((0,3,4.5),850,(.64,.8,1),3)]:
        bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;o.data.energy=power;o.data.color=col;o.data.shape='DISK';o.data.size=size;aim(o,(0,0,2.3))
    bpy.ops.object.camera_add(location=(5,-10,4.7));cam=bpy.context.object;cam.data.type='ORTHO';cam.data.ortho_scale=5.35;aim(cam,(0,0,2.25));scene.camera=cam
    scene.render.image_settings.file_format='PNG';scene.render.filepath=str(P/'Hollowmaw_ThreeQuarter.png');bpy.ops.render.render(write_still=True)
    cam.location=(0,-10,2.6);aim(cam,(0,0,2.25));scene.render.filepath=str(P/'Hollowmaw_Front.png');bpy.ops.render.render(write_still=True)
    cam.location=(6,-8,4.25);cam.data.ortho_scale=1.45;aim(cam,(0,-.13,4.03));scene.render.filepath=str(P/'Hollowmaw_JawDetail.png');bpy.ops.render.render(write_still=True)
    cam.location=(10,0,2.8);cam.data.ortho_scale=5.35;aim(cam,(0,0,2.25));scene.render.filepath=str(P/'Hollowmaw_Side.png');bpy.ops.render.render(write_still=True)

try:build();(P/'Hollowmaw_Done.txt').write_text('Build and both previews completed.')
except Exception:(P/'Hollowmaw_Error.txt').write_text(traceback.format_exc());raise
