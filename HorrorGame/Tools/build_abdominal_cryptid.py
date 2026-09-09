"""Abdominal cryptid: neutral authoring sculpt + separate backward crawl scene.
Native Blender coordinates: +Z up, -Y forward. No image generation is used.
"""
import bpy, math, random, traceback, json, shutil
from pathlib import Path
from mathutils import Vector, Quaternion
from mathutils.bvhtree import BVHTree
P=Path(r'E:\EpsteinHorror\HorrorGame\Assets\Models\AbdominalCryptid')
P.mkdir(exist_ok=True)
H={}
# Reuse only the local mesh construction helpers, never run the older asset builder.
exec((Path(__file__).parent/'build_hollowmaw.py').read_text().split('\ntry:build();')[0],H)
ell,tube,join,apply,mat,aim=[H[n] for n in ['ell','tube','join','apply','material','aim']]
random.seed(82)
def step(a,b,x):
    t=max(0.,min(1.,(x-a)/(b-a)));return t*t*(3-2*t)
def log(s):
    with (P/'BuildStatus.txt').open('a') as f:f.write(s+'\n')
def remesh(parts,name,res=.011):
    o=join(parts,name);m=o.modifiers.new('Unified tissue','REMESH');m.mode='VOXEL';m.voxel_size=res;m.use_smooth_shade=True;apply(o,m)
    m=o.modifiers.new('Tissue blending','SMOOTH');m.factor=1;m.iterations=5;apply(o,m)
    return o
def smooth_tube(name,pts,r,d=None,material=None):
    if d is None:d=list(r)
    pts=[pts[0],tuple(Vector(pts[0]).lerp(Vector(pts[1]),.06))]+pts[1:-1]+[tuple(Vector(pts[-2]).lerp(Vector(pts[-1]),.94)),pts[-1]]
    r=[r[0],r[0]*.94+r[1]*.06]+r[1:-1]+[r[-2]*.06+r[-1]*.94,r[-1]]
    d=[d[0],d[0]*.94+d[1]*.06]+d[1:-1]+[d[-2]*.06+d[-1]*.94,d[-1]]
    o=tube(name,pts,r,d,material,sides=20);m=o.modifiers.new('Anatomic curvature','SUBSURF');m.levels=2;apply(o,m);return o
def skin_material():
    m=mat('Dermis | ivory core to vascular extremities',(.48,.39,.34),.49);n=m.node_tree.nodes;l=m.node_tree.links;b=n.get('Principled BSDF');b.inputs['Subsurface Weight'].default_value=.09
    tex=n.new('ShaderNodeTexCoord');noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=7;noise.inputs['Detail'].default_value=4;l.new(tex.outputs['Object'],noise.inputs['Vector'])
    ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].position=.2;ramp.color_ramp.elements[0].color=(.19,.13,.14,1);ramp.color_ramp.elements[1].position=.8;ramp.color_ramp.elements[1].color=(.64,.58,.48,1);l.new(noise.outputs['Fac'],ramp.inputs[0])
    red=n.new('ShaderNodeValToRGB');red.color_ramp.elements[0].color=(.032,.004,.012,1);red.color_ramp.elements[1].color=(.28,.038,.047,1);l.new(noise.outputs['Fac'],red.inputs[0])
    a=n.new('ShaderNodeAttribute');a.attribute_name='bloodflow';mix=n.new('ShaderNodeMixRGB');l.new(a.outputs['Fac'],mix.inputs[0]);l.new(ramp.outputs[0],mix.inputs[1]);l.new(red.outputs[0],mix.inputs[2]);l.new(mix.outputs[0],b.inputs['Base Color'])
    pores=n.new('ShaderNodeTexNoise');pores.inputs['Scale'].default_value=185;pores.inputs['Detail'].default_value=2;l.new(tex.outputs['Object'],pores.inputs['Vector'])
    bump=n.new('ShaderNodeBump');bump.inputs['Distance'].default_value=.003;bump.inputs['Strength'].default_value=.3;l.new(pores.outputs[0],bump.inputs['Height']);l.new(bump.outputs[0],b.inputs['Normal'])
    return m
def bloodmask(o,constant=None):
    if o.type!='MESH':return
    a=o.data.attributes.get('bloodflow') or o.data.attributes.new(name='bloodflow',type='FLOAT',domain='POINT')
    for v in o.data.vertices:
        p=o.matrix_world@v.co
        f=max(step(1.04,1.48,abs(p.x)),1-step(.23,.72,p.z),.14*step(.24,.60,abs(p.x))) if constant is None else constant
        a.data[v.index].value=f
def cleanup(o):
    import bmesh
    bm=bmesh.new();bm.from_mesh(o.data);seen=set();islands=[]
    for v in bm.verts:
        if v in seen:continue
        todo=[v];seen.add(v);island=[]
        while todo:
            a=todo.pop();island.append(a)
            for e in a.link_edges:
                b=e.other_vert(a)
                if b not in seen:seen.add(b);todo.append(b)
        islands.append(island)
    tiny=[v for island in islands if len(island)<120 for v in island]
    if tiny:bmesh.ops.delete(bm,geom=tiny,context='VERTS')
    bm.to_mesh(o.data);bm.free();return sorted([len(c) for c in islands if len(c)>=120],reverse=True)

def build():
    bpy.ops.wm.read_factory_settings(use_empty=True);log('Constructing neutral anatomy')
    skin=skin_material();gum=mat('Mucosa | blood congested',(.10,.012,.021),.3);throat=mat('Throat | deep maroon',(.018,.001,.006),.25)
    tooth=mat('Teeth | stained bone',(.42,.34,.22),.3);horn=mat('Claws | dark keratin',(.07,.037,.026),.29)
    tongue_mat=mat('Tongue | papillary tissue',(.22,.024,.039),.26);suture=mat('Sutures | aged black thread',(.012,.007,.008),.64)
    saliva=mat('Saliva | viscous dark fluid',(.022,.007,.009),.085);bs=saliva.node_tree.nodes.get('Principled BSDF');bs.inputs['Transmission Weight'].default_value=.35;bs.inputs['IOR'].default_value=1.34
    n=tongue_mat.node_tree.nodes;l=tongue_mat.node_tree.links;t=n.new('ShaderNodeTexNoise');t.inputs['Scale'].default_value=95
    b=n.new('ShaderNodeBump');b.inputs['Distance'].default_value=.003;b.inputs['Strength'].default_value=.25;l.new(t.outputs[0],b.inputs['Height']);l.new(b.outputs[0],n.get('Principled BSDF').inputs['Normal'])
    parts=[];access=[];head_parts=[];rest={}
    def form(name,c,w,d=None):
        o=smooth_tube(name,c,w,d,skin);parts.append(o);return o
    core=form('Torso core',[(0,.02,1.82),(0,.04,2.02),(0,.06,2.24),(0,.10,2.5),(0,.14,2.77),(0,.18,3.07),(0,.19,3.32),(0,.15,3.55),(0,.09,3.69)],
         [.19,.345,.29,.235,.30,.43,.49,.33,.115],[.18,.23,.205,.18,.225,.26,.22,.16,.10])
    bpy.context.view_layer.update();core_surface=BVHTree.FromObject(core,bpy.context.evaluated_depsgraph_get())
    for s,side in [(1,'L'),(-1,'R')]:
        def q(p):return (s*p[0],p[1],p[2])
        sh=q((.48,.12,3.37));el=q((.98,.05,2.98));wr=q((1.43,-.015,2.48));hip=q((.27,.035,1.98));knee=q((.44,-.10,1.18));ank=q((.50,.06,.31))
        rest[side]={'shoulder':sh,'elbow':el,'wrist':wr,'hip':hip,'knee':knee,'ankle':ank}
        form('Lean upper arm',[q(p) for p in [(.40,.14,3.38),(.58,.14,3.37),(.73,.10,3.26),(.87,.055,3.1),(.98,.05,2.98)]],[.145,.17,.155,.11,.092],[.15,.165,.15,.105,.09])
        form('Long forearm',[el,q((1.1,.025,2.87)),q((1.26,0,2.67)),wr],[.09,.118,.081,.05],[.095,.105,.072,.048])
        parts.append(ell('Elbow tissue',el,(.099,.10,.11),skin));parts.append(ell('Wrist tissue',wr,(.061,.057,.072),skin))
        form('Long narrow palm',[wr,q((1.50,-.022,2.30)),q((1.52,-.026,2.18))],[.052,.112,.108],[.05,.055,.042])
        for i in range(4):
            x=1.412+i*.07;z=1.76+.045*abs(i-1.5)
            pts=[q((x,-.025,2.22)),q((x+.018*(i-1.5),-.044,2.04)),q((x+.033*(i-1.5),-.066,1.87)),q((x+.047*(i-1.5),-.105,z))]
            form('Spidery finger',pts,[.028,.024,.019,.012])
            e=Vector(pts[-1]);access.append(smooth_tube('Finger bone claw',[pts[-2],e,e+Vector((s*.013,-.14,-.13))],[.021,.019,.001],material=horn))
        form('Opposed thumb',[q((1.43,-.02,2.35)),q((1.30,-.045,2.22)),q((1.25,-.09,2.08))],[.04,.031,.018])
        access.append(smooth_tube('Thumb claw',[q((1.25,-.09,2.08)),q((1.26,-.17,1.98))],[.021,.001],material=horn))
        form('Sinewy thigh',[q((.23,.04,2.10)),hip,q((.335,.005,1.78)),q((.40,-.075,1.45)),knee],[.16,.18,.172,.115,.098],[.17,.195,.19,.13,.1])
        form('Long tibia',[knee,q((.455,.07,1.03)),q((.48,.125,.80)),q((.5,.09,.55)),ank],[.098,.118,.10,.061,.054],[.10,.143,.11,.073,.065])
        parts.append(ell('Knee tissue',knee,(.108,.107,.12),skin));parts.append(ell('Ankle tissue',ank,(.071,.075,.086),skin))
        form('Metatarsal fan',[ank,q((.50,-.08,.16)),q((.50,-.29,.12)),q((.50,-.39,.1))],[.055,.092,.13,.11],[.065,.073,.07,.045])
        for i in range(3):
            x=.385+i*.11
            form('Elongated toe',[q((x,-.3,.12)),q((x,-.51,.08)),q((x,-.63,.07))],[.045,.032,.02])
            access.append(smooth_tube('Toe bone claw',[q((x,-.58,.08)),q((x,-.73,.05)),q((x,-.81,.035))],[.027,.018,.001],material=horn))
        # Broad anatomical planes stay fused; the ribs are shallow under-skin forms.
        for i in range(5):
            z=3.18-i*.115;w=.37-i*.022;pts=[]
            for x,h in [(.12,z),(.215,z-.055),(w*.90,z-.01),(w,z+.055)]:
                p,n,_,_=core_surface.ray_cast(Vector((s*x,-2,h)),Vector((0,1,0)),4)
                if p is not None:pts.append(p-n*.014)
            if len(pts)>2:form('Subcutaneous rib',pts,[.012]+[.026]*(len(pts)-2)+[.011])
        form('Clavicle ridge',[q((.07,.0,3.46)),q((.26,-.015,3.45)),q((.43,.10,3.40))],[.019,.032,.016])
        form('Scapular blade',[q((.10,.30,3.42)),q((.30,.355,3.28)),q((.24,.30,3.03))],[.027,.044,.012])
        for off in [-.045,.035]:
            form('Quadricep boundary',[q((.28+off,-.115,1.99)),q((.35+off,-.16,1.73)),q((.44,-.18,1.24))],[.016,.024,.008])
        form('Tibial blade',[q((.44,-.17,1.18)),q((.49,-.005,.8)),q((.50,-.017,.36))],[.022,.018,.007])
        for i in range(3):form('Extensor tendon',[q((1.02+i*.02,-.03,2.96)),q((1.27+i*.015,-.065,2.66)),wr],[.015,.012,.007])
    for i in range(13):
        z=2.16+i*.112;y=.275 if z<2.75 else .38
        parts.append(ell('Spinal process',(0,y,z),(.032,.04,.035),skin))
    body=remesh(parts,'CRYPTID | continuous headless anatomy');log('Body fused')
    # No shoulder head: puckered stump with a transverse closure and black stitches.
    seam=smooth_tube('Raw shoulder closure',[(-.095,.066,3.685),(-.05,.055,3.702),(0,.052,3.71),(.06,.058,3.7),(.095,.07,3.685)],[.012,.017,.018,.016,.008],material=gum);access.append(seam)
    for i in range(7):
        x=-.077+i*.025
        access.append(smooth_tube('Stump stitch %02d'%i,[(x,.014,3.686),(x+.012,.052,3.72),(x+.006,.104,3.69)],[.004,.003,.004],material=suture))
    # Entire cranial assembly originates at the lower abdomen.
    head_parts.append(smooth_tube('Abdominal cranial attachment',[(0,.06,2.42),(0,-.16,2.30),(0,-.29,2.20),(0,-.36,2.12)],[.095,.145,.18,.20],[.075,.12,.16,.18],skin))
    head_parts.append(smooth_tube('Hanging blind dome',[(0,-.40,1.79),(0,-.40,1.95),(0,-.36,2.16),(0,-.28,2.28)],[.17,.264,.235,.10],[.17,.24,.20,.09],skin))
    head=remesh(head_parts,'HEAD | eyeless abdominal dome',.009)
    cutter=ell('Maw carving tool',(0,-.59,1.78),(.235,.27,.255))
    bo=head.modifiers.new('Recessed open mouth','BOOLEAN');bo.object=cutter;bo.operation='DIFFERENCE';apply(head,bo);bpy.data.objects.remove(cutter,do_unlink=True)
    head_objects=[head]
    head_objects.append(ell('THROAT | deep wet pharynx',(0,-.39,1.70),(.18,.08,.23),throat))
    jaw_pts=[(-.236,-.35,1.995),(-.225,-.42,1.80),(-.177,-.60,1.50),(-.08,-.72,1.35),(0,-.75,1.325),(.075,-.72,1.35),(.175,-.60,1.50),(.225,-.42,1.8),(.236,-.35,1.995)]
    jaw=smooth_tube('JAW | unhinged tapered mandible',jaw_pts,[.041,.044,.04,.045,.047,.045,.04,.044,.041],material=skin);head_objects.append(jaw)
    # Stretched cheek membranes close the sides while preserving the open V profile.
    for s in [-1,1]:
        verts=[(s*.23,-.34,1.99),(s*.23,-.45,1.86),(s*.17,-.58,1.52),(s*.095,-.62,1.45),(s*.14,-.36,1.68)]
        cheek=H['mesh']('Cheek | stretched corner membrane',verts,[(0,1,4),(1,2,4),(2,3,4)],gum)
        mod=cheek.modifiers.new('Membrane thickness','SOLIDIFY');mod.thickness=.01;apply(cheek,mod)
        mod=cheek.modifiers.new('Membrane curvature','SUBSURF');mod.levels=2;apply(cheek,mod);head_objects.append(cheek)
    top=[];bottom=[]
    for i in range(21):
        u=-1+2*i/20
        top.append((u*.212,-.56-.06*math.sqrt(max(0,1-u*u)),1.986-.055*u*u))
        bottom.append((u*.163,-.733+.12*abs(u),1.372+.18*abs(u)**1.6))
    head_objects.append(smooth_tube('Upper gum | irregular arch',top,[.014]*21,material=gum))
    head_objects.append(smooth_tube('Lower gum | tapered arch',bottom,[.017]*21,material=gum))
    for row in [0,1]:
        count=19 if row==0 else 15
        for i in range(count):
            if (row,i) in [(0,4),(1,11)]:continue
            u=-1+2*i/(count-1)+random.uniform(-.019,.019)
            if row==0:p=(u*.211,-.56-.06*math.sqrt(max(0,1-u*u)),1.986-.055*u*u)
            else:p=(u*.163,-.733+.12*abs(u),1.372+.18*abs(u)**1.6)
            length=random.uniform(.070,.145)*(1.13 if i%5==0 else 1)
            tip=(p[0]*.87+random.uniform(-.009,.009),p[1]-.034,p[2]+(-length if row==0 else length*.82))
            head_objects.append(smooth_tube('Needle tooth %s.%s'%(row,i),[p,(p[0]*.96,p[1]-.026,(p[2]+tip[2])/2),tip],[random.uniform(.011,.017),.008,.0008],material=tooth))
    tpts=[(0,-.40,1.68),(0,-.57,1.51),(.025,-.77,1.40),(.10,-.96,1.37),(.145,-1.08,1.44),(.13,-1.10,1.51)]
    tongue=smooth_tube('TONGUE | long grooved curl',tpts,[.04,.059,.065,.049,.029,.002],[.032,.038,.033,.026,.021,.002],tongue_mat);head_objects.append(tongue)
    head_objects.append(smooth_tube('Tongue central groove',[(.005,-.58,1.53),(.025,-.77,1.426),(.10,-.96,1.39),(.145,-1.08,1.455)],[.002,.003,.002,.0008],material=throat))
    for s in [-1,1]:
        head_objects.append(smooth_tube('Viscous saliva strand',[(s*.15,-.59,1.89),(s*.14,-.68,1.66),(s*.10,-.72,1.46)],[.0035,.0018,.0025],material=saliva))
    # Surface conforming scars and venules: thin, restrained irregular lines.
    bpy.context.view_layer.update();tree=BVHTree.FromObject(body,bpy.context.evaluated_depsgraph_get())
    scar=mat('Scars | bruised dermal creases',(.115,.048,.049),.62)
    paths=[[(.66,3.33),(.69,3.25),(.74,3.17)],[(.33,1.9),(.35,1.78),(.38,1.62)],[(1.13,2.86),(1.19,2.78),(1.26,2.67)],[(.18,2.67),(.16,2.59),(.19,2.50)]]
    for s in [-1,1]:
        for i,path in enumerate(paths):
            pts=[]
            for x,z in path:
                p,n,_,_=tree.ray_cast(Vector((s*x,-3,z)),Vector((0,1,0)),6)
                if p is not None:pts.append(p+n*.0015)
            if len(pts)>1:access.append(smooth_tube('Dermal crease',pts,[.0015]*len(pts),material=scar))
    bloodmask(body);bloodmask(head,.04);bloodmask(jaw,.35)
    body_islands=cleanup(body);head_islands=cleanup(head)
    # Store all native objects in a clearly separated neutral authoring scene.
    model=[body]+access+head_objects
    author=bpy.context.scene;author.name='01 | Neutral rigging source'
    # Named guide in native coordinates, with abdominal head parented to pelvis.
    bpy.ops.object.armature_add(enter_editmode=True);rig=bpy.context.object;rig.name='RIG_Cryptid | abdomen head, -Y forward';eb=rig.data.edit_bones;eb.remove(eb[0]);bones={}
    def bn(n,h,t,parent=None):
        b=eb.new(n);b.head=h;b.tail=t
        if parent:b.parent=bones[parent]
        b.align_roll(Vector((0,-1,0)));bones[n]=b
    bn('root',(0,0,0),(0,0,.2));bn('pelvis',(0,.04,1.9),(0,.06,2.24),'root');bn('lumbar',(0,.06,2.24),(0,.13,2.78),'pelvis');bn('thorax',(0,.13,2.78),(0,.18,3.32),'lumbar');bn('neck_stump',(0,.18,3.32),(0,.09,3.70),'thorax')
    bn('abdomen_head',(0,-.10,2.35),(0,-.4,1.95),'pelvis');bn('mandible',(0,-.35,1.99),(0,-.75,1.325),'abdomen_head')
    for i in range(5):bn('tongue.%02d'%i,tpts[i],tpts[i+1],'mandible' if i==0 else 'tongue.%02d'%(i-1))
    for s,side in [(1,'L'),(-1,'R')]:
        a=rest[side]
        bn('clavicle.'+side,(s*.08,.17,3.35),a['shoulder'],'thorax');bn('arm.'+side,a['shoulder'],a['elbow'],'clavicle.'+side);bn('forearm.'+side,a['elbow'],a['wrist'],'arm.'+side);bn('hand.'+side,a['wrist'],(s*1.52,-.026,2.18),'forearm.'+side)
        for i in range(4):
            x=1.412+i*.07;h=(s*x,-.025,2.22);m=(s*(x+.018*(i-1.5)),-.044,2.04);t=(s*(x+.047*(i-1.5)),-.105,1.76+.045*abs(i-1.5))
            bn('finger_%s.01.%s'%(i,side),h,m,'hand.'+side);bn('finger_%s.02.%s'%(i,side),m,t,'finger_%s.01.%s'%(i,side))
        bn('thumb.'+side,(s*1.43,-.02,2.35),(s*1.25,-.09,2.08),'hand.'+side)
        bn('thigh.'+side,a['hip'],a['knee'],'pelvis');bn('shin.'+side,a['knee'],a['ankle'],'thigh.'+side);bn('foot.'+side,a['ankle'],(s*.50,-.4,.10),'shin.'+side);bn('toes.'+side,(s*.5,-.4,.10),(s*.5,-.70,.07),'foot.'+side)
    bpy.ops.object.mode_set(mode='OBJECT');rig.show_in_front=True;rig.hide_render=True;rig['status']='Unweighted neutral guide. Cinematic crawl is a separate static sculpt.'
    # A separate posed mesh uses smooth positional maps for the cinematic crab-crawl.
    cinematic=bpy.data.scenes.new('02 | Sewer backward crawl');bpy.context.window.scene=cinematic
    spine_keys=[(1.82,.03,1.04),(2.24,.39,1.58),(2.78,.92,1.89),(3.32,1.32,1.73),(3.70,1.52,1.39)]
    def torso_map(p):
        z=p.z
        j=next((i for i in range(len(spine_keys)-1) if z<spine_keys[i+1][0]),len(spine_keys)-2)
        a,b=spine_keys[j],spine_keys[j+1];t=(z-a[0])/(b[0]-a[0]);t=max(-.3,min(1.3,t))
        p1=Vector((0,a[1],a[2]));p2=Vector((0,b[1],b[2]))
        p0=Vector((0,*spine_keys[j-1][1:])) if j else p1*2-p2
        p3=Vector((0,*spine_keys[j+2][1:])) if j+2<len(spine_keys) else p2*2-p1
        c=.5*((2*p1)+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t*t*t)
        tangent=((-p0+p2)+2*(2*p0-5*p1+4*p2-p3)*t+3*(-p0+3*p1-3*p2+p3)*t*t).normalized()
        depth=Vector((0,tangent.z,-tangent.y));return c+Vector((p.x,0,0))+(p.y-.12)*depth
    targets={}
    for s,side in [(1,'L'),(-1,'R')]:
        targets[side]={'shoulder':torso_map(Vector(rest[side]['shoulder'])),'elbow':Vector((s*1.04,1.49,.87)),'wrist':Vector((s*1.21,.59,.31)),
                       'hip':torso_map(Vector(rest[side]['hip'])),'knee':Vector((s*.98,-.03,1.13)),'ankle':Vector((s*.98,-.86,.24))}
    def segment(p,a,b,c,d):
        a,b,c,d=map(Vector,(a,b,c,d));v=b-a;w=d-c;t=(p-a).dot(v)/v.length_squared
        axis=a+v*t;return c+w*t+v.rotation_difference(w)@(p-axis)
    def blend_segments(p,source,dest):
        results=[]
        for i in range(len(source)-1):
            a,b=Vector(source[i]),Vector(source[i+1]);v=b-a;t=max(0,min(1,(p-a).dot(v)/v.length_squared));dist=(p-a-v*t).length_squared
            results.append((math.exp(-dist/.018),segment(p,a,b,dest[i],dest[i+1])))
        total=sum(w for w,_ in results)
        if total<1e-15:return min([( (p-Vector(a)).length,segment(p,a,b,c,d)) for a,b,c,d in zip(source,source[1:],dest,dest[1:])],key=lambda x:x[0])[1]
        return sum((q*w for w,q in results),Vector())/total
    def head_map(p):return Vector((p.x,p.y-.08,p.z-1.14))
    def pose(p,kind='body'):
        if kind=='head':return head_map(p)
        s=1 if p.x>=0 else -1;side='L' if s==1 else 'R';a=rest[side];b=targets[side]
        if (abs(p.x)>.64 and p.z>1.50) or (abs(p.x)>.43 and p.z>2.65):
            source=[a['shoulder'],a['elbow'],a['wrist'],(s*1.53,-.026,2.18),(s*1.57,-.13,1.72)]
            dest=[b['shoulder'],b['elbow'],b['wrist'],(s*1.22,.35,.12),(s*1.24,-.1,.07)]
            q=blend_segments(p,source,dest);w=step(.43,.64,abs(p.x));return torso_map(p).lerp(q,w)
        if p.z<2.16:
            source=[a['hip'],a['knee'],a['ankle'],(s*.50,-.40,.10),(s*.50,-.77,.04)]
            dest=[b['hip'],b['knee'],b['ankle'],(s*1.01,-1.18,.09),(s*1.03,-1.47,.05)]
            q=blend_segments(p,source,dest);w=(1-step(1.95,2.18,p.z))*step(.10,.27,abs(p.x));return torso_map(p).lerp(q,w)
        return torso_map(p)
    posed=[]
    for o in model:
        new=o.copy();new.data=o.data.copy();cinematic.collection.objects.link(new);new.name='CRAWL | '+o.name
        kind='head' if o in head_objects else 'body'
        for v in new.data.vertices:v.co=pose(o.matrix_world@v.co,kind)
        new.matrix_world.identity();posed.append(new)
        if o==body:posed_body=new
        if o==head:posed_head=new
    # Bridge the abdominal graft to the bent lower torso in the presentation sculpt.
    graft=smooth_tube('CRAWL | stretched abdominal attachment',[(0,.38,1.56),(0,.08,1.40),(0,-.27,1.21),(0,-.37,1.06)],[.17,.16,.15,.16],material=skin);bloodmask(graft,.08)
    # Fuse the static presentation's abdomen and head junction; transfer the vascular mask.
    from mathutils.kdtree import KDTree
    transfer=[]
    for o in [posed_body,posed_head,graft]:
        att=o.data.attributes.get('bloodflow')
        for v in o.data.vertices:transfer.append((o.matrix_world@v.co,att.data[v.index].value if att else .05))
    kd=KDTree(len(transfer))
    for i,(p,f) in enumerate(transfer):kd.insert(p,i)
    kd.balance();sculpt=remesh([posed_body,posed_head,graft],'CRAWL | continuous back-arched body and abdominal head',.01)
    att=sculpt.data.attributes.get('bloodflow') or sculpt.data.attributes.new(name='bloodflow',type='FLOAT',domain='POINT')
    for v in sculpt.data.vertices:
        _,idx,_=kd.find(v.co);att.data[v.index].value=transfer[idx][1]
    # Sewer environment: wet rough concrete, drainage trench, ribs, pipes and puddles.
    concrete=mat('Sewer | wet mottled concrete',(.045,.049,.044),.68);n=concrete.node_tree.nodes;l=concrete.node_tree.links;nb=n.new('ShaderNodeTexNoise');nb.inputs['Scale'].default_value=3.4;nb.inputs['Detail'].default_value=6
    tc=n.new('ShaderNodeTexCoord');l.new(tc.outputs['Object'],nb.inputs['Vector'])
    rr=n.new('ShaderNodeValToRGB');rr.color_ramp.elements[0].color=(.008,.012,.009,1);rr.color_ramp.elements[1].color=(.09,.095,.072,1);l.new(nb.outputs[0],rr.inputs[0]);l.new(rr.outputs[0],n.get('Principled BSDF').inputs['Base Color'])
    grain=n.new('ShaderNodeTexNoise');grain.inputs['Scale'].default_value=54;grain.inputs['Detail'].default_value=3;l.new(tc.outputs['Object'],grain.inputs['Vector'])
    bb=n.new('ShaderNodeBump');bb.inputs['Strength'].default_value=.65;bb.inputs['Distance'].default_value=.018;l.new(grain.outputs[0],bb.inputs['Height']);l.new(bb.outputs[0],n.get('Principled BSDF').inputs['Normal'])
    def cube(name,loc,scale,material):
        bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=name;o.scale=scale;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(material);return o
    cube('Floor',(0,3,-.14),(7,20,.22),concrete)
    cube('Left sewer wall',(-2.75,4,1.65),(.32,20,3.6),concrete);cube('Right sewer wall',(2.75,4,1.65),(.32,20,3.6),concrete)
    cube('Ceiling',(0,4,3.45),(5.7,20,.24),concrete)
    iron=mat('Oxidised iron',(.06,.037,.018),.6)
    for y in [-1,2,5,8]:
        for s in [-1,1]:cube('Wall reinforcement',(s*2.52,y,1.65),(.15,.18,3.35),iron)
    for s in [-1,1]:
        tube('Drain pipe',[(s*2.39,-4,.75),(s*2.39,12,.75)],[.115,.115],mat=iron,sides=20)
    water=mat('Water | oily shallow puddles',(.012,.018,.019),.105);water.node_tree.nodes.get('Principled BSDF').inputs['Metallic'].default_value=.3
    for i in range(11):
        x=random.uniform(-2.3,2.3);y=random.uniform(-2.5,6)
        rx=random.uniform(.2,.7);ry=random.uniform(.25,.9);phase=random.random()*6;verts=[(x,y,-.021)]
        for j in range(48):
            a=j*2*math.pi/48;r=1+.18*math.sin(3*a+phase)+.11*math.sin(7*a-phase)
            verts.append((x+rx*r*math.cos(a),y+ry*r*math.sin(a),-.021))
        H['mesh']('Irregular shallow puddle',verts,[(0,j+1,(j+1)%48+1) for j in range(48)],water)
    for i in range(23):
        x=random.choice([-1,1])*random.uniform(1.6,2.4);y=random.uniform(-2,6)
        o=cube('Concrete debris',(x,y,.025),(random.uniform(.04,.12),random.uniform(.05,.15),.05),concrete);o.rotation_euler.z=random.random()*6
    log('Sewer and crawl assembled')
    def setup(scene):
        scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
        try:
            prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
            for device in prefs.devices:device.use=(device.type=='OPTIX')
            if any(d.type=='OPTIX' for d in prefs.devices):scene.cycles.device='GPU'
        except Exception:pass
        scene.world=bpy.data.worlds.new('Near black air');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.014,.021,.028,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.07
    setup(cinematic)
    bpy.ops.object.camera_add(location=(1.3,-4.8,1.55));cam=bpy.context.object;cam.name='Cinematic flashlight camera';cam.data.lens=35;aim(cam,(0,.22,.89));cinematic.camera=cam
    bpy.ops.object.light_add(type='SPOT',location=(1.1,-3.1,1.45));light=bpy.context.object;light.name='Harsh flashlight';light.data.energy=760;light.data.color=(.83,.91,1);light.data.spot_size=math.radians(61);light.data.spot_blend=.38;light.data.shadow_soft_size=.06;aim(light,(0,.3,.95))
    for pos,power,col,size in [((-1.8,1.6,2.5),60,(.23,.48,.64),1.4),((0,6,2.3),40,(.44,.59,.35),.8)]:
        bpy.ops.object.light_add(type='AREA',location=pos);o=bpy.context.object;o.data.energy=power;o.data.color=col;o.data.size=size;aim(o,(0,.3,1))
    cinematic.render.resolution_x=1600;cinematic.render.resolution_y=1000
    # Native file opens on the neutral sculpt in material view; switch scenes for the sewer.
    bpy.context.window.scene=author
    setup(author)
    bpy.ops.object.camera_add(location=(5,-10,4.5));ac=bpy.context.object;ac.name='Neutral inspection camera';ac.data.type='ORTHO';ac.data.ortho_scale=4.55;aim(ac,(0,-.1,1.98));author.camera=ac
    for pos,power,col in [((3,-4,5),520,(.82,.90,1)),((-3,-2,2.5),220,(1,.73,.58)),((0,3,4),400,(.5,.66,1))]:
        bpy.ops.object.light_add(type='AREA',location=pos);o=bpy.context.object;o.data.energy=power;o.data.color=col;o.data.size=3;aim(o,(0,0,2))
    author.render.resolution_x=1000;author.render.resolution_y=1200
    bpy.ops.object.select_all(action='DESELECT');body.select_set(True);bpy.context.view_layer.objects.active=body
    for screen in bpy.data.screens:
        for a in screen.areas:
            if a.type=='VIEW_3D':
                a.spaces.active.region_3d.view_rotation=Quaternion((1,0,0),math.pi/2);a.spaces.active.region_3d.view_location=(0,-.1,1.98);a.spaces.active.region_3d.view_distance=6;a.spaces.active.region_3d.view_perspective='ORTHO';a.spaces.active.shading.type='MATERIAL'
    report={'body_vertices':len(body.data.vertices),'body_islands':body_islands,'head_islands':head_islands,'rig_bones':len(rig.data.bones),'forward':'-Y','up':'+Z','head_parent':rig.data.bones['abdomen_head'].parent.name,'eyes':0,'tongue':True,'weighted':False,'cinematic_pose':'separate static crawl sculpt'}
    (P/'Validation.json').write_text(json.dumps(report,indent=2))
    text=bpy.data.texts.new('READ ME | asset status');text.write('Scene 01: neutral sculpt + aligned unweighted armature. Scene 02: separate static backward crawl in sewer. Abdominal head is parented to pelvis. Sculpt topology needs retopology, UVs, baking and skinning for production animation. Both scenes use -Y forward / Z up.')
    bpy.ops.wm.save_as_mainfile(filepath=str(P/'AbdominalCryptid.blend'));log('Native asset saved')
    author.render.filepath=str(P/'Neutral_Inspection.png');bpy.ops.render.render(write_still=True);log('Neutral render complete')
    bpy.context.window.scene=cinematic;cinematic.render.filepath=str(P/'Sewer_Crawl_Preview.png');bpy.ops.render.render(write_still=True);log('Cinematic preview complete')
    (P/'Complete.txt').write_text('Saved native file and rendered neutral/cinematic inspections.')

try:build()
except Exception:(P/'Error.txt').write_text(traceback.format_exc());raise
