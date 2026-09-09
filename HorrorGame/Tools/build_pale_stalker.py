"""Layered anatomical horror sculpt. Native +Z up, -Y forward."""
import bpy, math, random, json, traceback, sys
from pathlib import Path
from mathutils import Vector, Quaternion
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'Assets/Models/PaleStalker';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'Tools'))
H={'__file__':str(ROOT/'Tools/build_abdominal_cryptid.py')}
exec((ROOT/'Tools/build_abdominal_cryptid.py').read_text().split('\ntry:build()')[0],H)
smooth_tube,remesh,cleanup,ell,mesh,join,apply,aim=[H[n] for n in ['smooth_tube','remesh','cleanup','ell','H','join','apply','aim']]
mesh=mesh['mesh']
from cryptid_materials import create_materials
from cryptid_cranium import build_head
random.seed(743)
def log(s):
    with (OUT/'BuildStatus.txt').open('a') as f:f.write(s+'\n')
def step(a,b,x):
    t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)
def attr(o,val=None):
    a=o.data.attributes.get('bloodflow') or o.data.attributes.new(name='bloodflow',type='FLOAT',domain='POINT')
    for v in o.data.vertices:
        p=o.matrix_world@v.co
        a.data[v.index].value=val if val is not None else max(step(1.03,1.50,abs(p.x)),1-step(.22,.69,p.z),.025)
def identity(o):
    m=o.matrix_world.copy()
    for v in o.data.vertices:v.co=m@v.co
    o.matrix_world.identity()
def tube(name,p,r,mat,d=None):return smooth_tube(name,p,r,d,mat)
def set_scene(scene):bpy.context.window.scene=scene;bpy.context.view_layer.update()

def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    M=create_materials();skin=M['skin'];base=[];details=[];rest={};log('Building lean connected anatomy')
    author=bpy.context.scene;author.name='01 | Neutral A-pose - neck head'
    def form(n,p,r,d=None):
        o=tube(n,p,r,skin,d);base.append(o);return o
    form('Tapered thorax and pelvis',[(0,.04,1.83),(0,.04,2.01),(0,.055,2.20),(0,.08,2.43),(0,.095,2.64),(0,.11,2.88),(0,.12,3.10),(0,.10,3.29),(0,.08,3.43)],
         [.155,.29,.255,.19,.22,.32,.40,.425,.255],[.13,.20,.17,.145,.16,.215,.23,.17,.115])
    form('Cervical column',[(0,.08,3.32),(0,.075,3.48),(0,.04,3.64),(0,.02,3.83)],[.23,.135,.085,.115],[.14,.12,.105,.11])
    for s,side in [(1,'L'),(-1,'R')]:
        def q(p):return (s*p[0],p[1],p[2])
        sh=q((.47,.08,3.30));el=q((.99,.035,2.92));wr=q((1.43,-.015,2.40));hip=q((.245,.04,1.98));knee=q((.405,-.10,1.17));ank=q((.47,.065,.30))
        rest[side]={'shoulder':sh,'elbow':el,'wrist':wr,'hip':hip,'knee':knee,'ankle':ank}
        form('Integrated shoulder and brachium '+side,[q((.30,.08,3.32)),q((.49,.08,3.34)),q((.62,.07,3.25)),q((.78,.04,3.12)),el],[.135,.15,.147,.114,.079],[.13,.16,.137,.103,.075])
        form('Ulna radius forearm '+side,[el,q((1.07,.02,2.82)),q((1.24,0,2.63)),wr],[.076,.103,.078,.041],[.074,.086,.061,.043])
        form('Narrow palm '+side,[wr,q((1.49,-.027,2.24)),q((1.50,-.032,2.12))],[.044,.101,.095],[.043,.049,.035])
        for i in range(4):
            x=1.401+i*.066;endz=1.66+.035*abs(i-1.35)
            pts=[q((x,-.027,2.16)),q((x+.02*(i-1.5),-.04,1.99)),q((x+.04*(i-1.5),-.075,1.81)),q((x+.062*(i-1.5),-.12,endz))]
            form('Phalanges '+side+str(i),pts,[.026,.021,.018,.0105])
            a=Vector(pts[-1]);details.append(tube('Curved keratin claw '+side+str(i),[pts[-2],a,a+Vector((s*.016,-.14,-.13))],[.02,.016,.0007],M['horn']))
            rest[side]['finger'+str(i)]=pts
        thumb=[q((1.435,-.025,2.30)),q((1.295,-.035,2.17)),q((1.245,-.08,2.04))]
        form('Opposing thumb '+side,thumb,[.035,.027,.014]);rest[side]['thumb']=thumb
        details.append(tube('Thumb hook '+side,[thumb[-1],q((1.23,-.16,1.93))],[.019,.0007],M['horn']))
        form('Femoral tissue '+side,[q((.21,.05,2.08)),hip,q((.295,.015,1.81)),q((.35,-.04,1.49)),knee],[.13,.156,.153,.105,.081],[.14,.17,.16,.108,.079])
        form('Tibial tissue '+side,[knee,q((.43,.055,1.02)),q((.45,.13,.81)),q((.47,.105,.52)),ank],[.08,.095,.082,.047,.044],[.078,.127,.1,.051,.047])
        form('Foot arch '+side,[ank,q((.47,-.04,.17)),q((.47,-.26,.11)),q((.47,-.38,.09))],[.046,.075,.112,.096],[.05,.06,.05,.035])
        for i in range(3):
            x=.37+i*.095
            form('Toe '+side+str(i),[q((x,-.29,.115)),q((x,-.49,.09)),q((x,-.62,.065))],[.032,.026,.014])
            details.append(tube('Toe hook '+side+str(i),[q((x,-.57,.074)),q((x,-.71,.038)),q((x,-.82,.025))],[.021,.014,.0006],M['horn']))
        form('Sternocleidomastoid '+side,[q((.03,-.023,3.38)),q((.074,-.047,3.54)),q((.086,-.046,3.75))],[.018,.025,.014])
        form('Achilles '+side,[q((.46,.20,.90)),q((.47,.135,.50)),q((.47,.12,.20))],[.018,.017,.01])
    body=remesh(base,'BODY | continuous lean dermis',.0075);cleanup(body);identity(body)
    # Depress the anterior chest surface itself to make a true recessed thoracic bed.
    for v in body.data.vertices:
        p=v.co
        if 2.60<p.z<3.31 and p.y<.05:
            edge=step(0,.10,.35-abs(p.x))*step(2.60,2.76,p.z)*(1-step(3.20,3.31,p.z))
            front=1-step(-.055,.045,p.y)
            p.y+=.085*edge*front
    body.data.update();attr(body)
    bpy.context.view_layer.update();surface=BVHTree.FromObject(body,bpy.context.evaluated_depsgraph_get())
    def project(x,z,back=False,lift=0):
        origin=Vector((x,3 if back else -3,z));direction=Vector((0,-1 if back else 1,0))
        p,n,_,_=surface.ray_cast(origin,direction,6)
        return (p+n*lift,n) if p is not None else (None,None)
    # Anatomical muscle ribbons are surfaces, not overlapping round primitives.
    def leaf(name,path,width,material,bulge=.014,back=False,fibers=12,offset=.003):
        a,b,c=[Vector((p[0],p[1])) for p in path];nlen=48;nwide=16;phase=random.random()*6.28
        def sample(t,u):
            p=(1-t)**2*a+2*t*(1-t)*b+t*t*c
            tan=2*(1-t)*(b-a)+2*t*(c-b);tan.normalize();across=Vector((-tan.y,tan.x))
            shape=math.sin(math.pi*t)**.58
            w=width*shape*(1+.055*math.sin(19*t+phase)+.025*math.sin(43*t))
            x,z=p+across*(u*w)
            loc,n=project(x,z,back)
            if loc is None:loc,n=project(p.x,p.y,back)
            if loc is None:return Vector((x,0,z))
            ridges=(.0010*math.sin(u*math.pi*13+math.sin(t*12))+.0006*math.sin(u*80+t*8))
            return loc+n*(offset+bulge*math.sin(math.pi*(u+1)/2)**1.2*shape+ridges*shape)
        verts=[sample(i/nlen,-1+2*j/nwide) for i in range(nlen+1) for j in range(nwide+1)]
        faces=[]
        for i in range(nlen):
            for j in range(nwide):
                k=i*(nwide+1)+j;faces.append((k,k+1,k+nwide+2,k+nwide+1))
        o=mesh(name,verts,faces,material);mod=o.modifiers.new('Fascicle thickness','SOLIDIFY');mod.thickness=.002;apply(o,mod);details.append(o)
        # Uneven pale peripheral fascial fibers border deep wine-red striations.
        fiber_objects=[]
        for k in range(fibers):
            u=-.94+1.88*k/max(1,fibers-1);start=random.uniform(.025,.13);end=random.uniform(.86,.98)
            pts=[sample(start+(end-start)*j/12,u+.022*math.sin(j*.7+phase)) for j in range(13)]
            r=random.uniform(.00085,.0017)
            fm=M['fascia'] if k%4==0 or k in [0,fibers-1] else M['blood']
            fiber_objects.append(tube(name+' fiber',pts,[r*.4]+[r]*11+[r*.25],fm))
        if fiber_objects:details.append(join(fiber_objects,name+' | grouped longitudinal fibers'))
        return o
    # Broad exposed thoracic membrane, wavy torn margins and underlying intercostals.
    for s,side in [(1,'L'),(-1,'R')]:
        for i in range(6):
            z=3.20-i*.086;outer=.345-i*.018
            # Dark red tissue sits in the depression, while ribs stand forward of it.
            leaf('Intercostal muscle %s.%02d'%(side,i),[(s*.025,z-.035),(s*.16,z-.065),(s*outer,z-.01)],.043,M['muscle'],.006,fibers=8)
            pts=[]
            for j in range(17):
                t=j/16;x=s*(.025+(outer-.025)*t);h=z-.040*math.sin(math.pi*t)+.025*t
                p,n=project(x,h,lift=.019+(.019*math.sin(math.pi*t)))
                if p is not None:pts.append(p)
            details.append(tube('Exposed flattened rib %s.%02d'%(side,i),pts,[.008]+[.021+.002*math.sin(j*1.4+i) for j in range(len(pts)-2)]+[.01],M['bone'],[.007]+[.011]*(len(pts)-2)+[.006]))
            # Ragged fascial filaments run obliquely over selected ribs.
            if i%2==0:
                p=[project(s*x,h,lift=.043)[0] for x,h in [(.08,z+.04),(.15,z-.045),(.23,z-.105)]]
                if all(v is not None for v in p):details.append(tube('Thoracic torn fascia '+side+str(i),p,[.002,.0035,.001],M['fascia']))
        # Layered pectoralis fan runs from sternum toward humeral insertion.
        for i in range(3):
            leaf('Pectoralis fascicle '+side+str(i),[(s*.03,3.29-i*.058),(s*.21,3.32-i*.031),(s*.48,3.31-i*.025)],.031,M['muscle'],.017,fibers=10)
        leaf('Anterior deltoid '+side,[(s*.47,3.40),(s*.59,3.28),(s*.70,3.15)],.092,M['muscle'],.012,fibers=18)
        leaf('Biceps brachii '+side,[(s*.66,3.20),(s*.78,3.10),(s*.96,2.955)],.061,M['muscle'],.013,fibers=16)
        leaf('Brachioradialis '+side,[(s*1.005,2.90),(s*1.145,2.775),(s*1.407,2.43)],.041,M['muscle'],.009,fibers=12)
        leaf('Forearm aponeurosis '+side,[(s*1.05,2.81),(s*1.24,2.69),(s*1.44,2.405)],.017,M['fascia'],.008,fibers=4)
        leaf('Rectus femoris '+side,[(s*.255,1.97),(s*.33,1.67),(s*.402,1.24)],.071,M['muscle'],.010,fibers=17)
        leaf('Vastus lateralis '+side,[(s*.35,1.925),(s*.423,1.63),(s*.446,1.29)],.037,M['muscle'],.006,fibers=9)
        leaf('Tibialis anterior '+side,[(s*.405,1.125),(s*.455,.78),(s*.47,.335)],.029,M['muscle'],.006,fibers=10)
        leaf('External oblique '+side,[(s*.275,2.72),(s*.18,2.44),(s*.215,2.11)],.03,M['fascia'],.007,fibers=6)
        # Back surfaces: layered scapula, trapezius and spinal erectors.
        leaf('Scapular fascia '+side,[(s*.13,3.31),(s*.35,3.22),(s*.22,2.92)],.065,M['fascia'],.018,True,10)
        leaf('Trapezius fascicles '+side,[(s*.08,3.51),(s*.16,3.35),(s*.39,3.29)],.042,M['muscle'],.011,True,12)
        leaf('Erector spinae '+side,[(s*.066,3.14),(s*.08,2.73),(s*.085,2.22)],.03,M['muscle'],.009,True,8)
        leaf('Triceps '+side,[(s*.57,3.28),(s*.73,3.16),(s*.95,2.96)],.069,M['muscle'],.015,True,16)
        leaf('Posterior calf '+side,[(s*.43,1.10),(s*.45,.87),(s*.47,.53)],.046,M['muscle'],.012,True,12)
        # Hand metacarpals, sheath tendons, knuckle wrinkles, and branching veins.
        for i in range(4):
            path=rest[side]['finger'+str(i)];x=path[0][0]
            p=[]
            for j in range(11):
                t=j/10;xx=(1-t)*s*1.43+t*x;z=2.395*(1-t)+2.14*t
                hit,n=project(xx,z,lift=.006)
                if hit is not None:p.append(hit)
            if len(p)>2:details.append(tube('Hand tendon '+side+str(i),p,[.0025]+[.005]*(len(p)-2)+[.002],M['fascia']))
            for k in [1,2]:
                c=Vector(path[k]);wrinkles=[]
                for zoff in [-.009,0,.009]:
                    pts=[]
                    for j in range(7):
                        x=c.x+(j-3)*.006;z=c.z+zoff+.004*math.cos(j*.8);p,n=project(x,z,lift=.0015)
                        if p is not None:pts.append(p)
                    if len(pts)>2:wrinkles.append(tube('Knuckle fold',pts,[.0012]*len(pts),M['scar']))
                if wrinkles:details.append(join(wrinkles,'Finger articulation creases '+side+str(i)+str(k)))
        for k in range(3):
            pts=[]
            for j in range(15):
                t=j/14;x=s*(1.19+.21*t+.012*math.sin(t*11+k));z=2.67-.27*t+k*.018;p,n=project(x,z,lift=.003)
                if p is not None:pts.append(p)
            if len(pts)>3:details.append(tube('Vascular hand branch '+side+str(k),pts,[.0015]+[.002]*(len(pts)-2)+[.0007],M['vein']))
        for i in range(3):
            p=[project(s*(.37+i*.095),z,lift=.006)[0] for z in [.18,.14,.10]]
            if all(x is not None for x in p):details.append(tube('Dorsal foot cord '+side+str(i),p,[.002,.005,.002],M['fascia']))
    # Segmented sternum and median tendon stay visibly ivory amid raw red intercostals.
    for i in range(7):
        z=3.25-i*.082;p,n=project(0,z,lift=.025)
        if p is not None:
            o=tube('Sternal plate %02d'%i,[p+Vector((0,0,-.036)),p,p+Vector((0,0,.036))],[.012,.032-.0018*i,.013],M['bone'],[.008,.013,.008]);details.append(o)
    for i in range(13):
        z=2.25+i*.083;p,n=project(0,z,True,.011)
        if p is not None:details.append(tube('Dorsal spinous process %02d'%i,[p+Vector((0,-.01,-.03)),p+Vector((0,.025,0)),p+Vector((0,0,.025))],[.016,.024,.009],M['bone'],[.013,.018,.01]))
    # Periumbilical seam only: no mouth, head, tongue or other cranial parts below chest.
    pts=[project(.006*math.sin(i),2.22+i*.032,lift=.001)[0] for i in range(10)]
    if all(p is not None for p in pts):details.append(tube('Linea alba crease',pts,[.0013]*len(pts),M['scar']))
    log('Layered ribs, muscle ribbons, tendons and fibers complete')
    api={'smooth_tube':smooth_tube,'ell':ell,'mesh':mesh,'remesh':remesh,'apply':apply,'join':join}
    head=build_head(api,M);model=[body]+details+head['objects']
    for o in model:
        if o.type=='MESH':
            identity(o)
            if M['skin'] in list(o.data.materials) and not o.data.attributes.get('bloodflow'):attr(o,.11)
    log('Conventional neck head, jaw and tongue complete')
    # Organize authoring objects into clear collections with a hidden aligned guide.
    def group(name,objects):
        col=bpy.data.collections.new(name);author.collection.children.link(col)
        for o in objects:
            for c in list(o.users_collection):c.objects.unlink(o)
            col.objects.link(o)
        return col
    group('ANATOMY | connected dermis',[body]);group('DETAIL | rib cage, fascicles and tendons',details);group('HEAD | eyeless cranial and oral assembly',head['objects'])
    bpy.ops.object.armature_add(enter_editmode=True);rig=bpy.context.object;rig.name='RIG | Neck-mounted head - Z up -Y forward';eb=rig.data.edit_bones;eb.remove(eb[0]);bones={}
    def bone(n,h,t,parent=None):
        b=eb.new(n);b.head=h;b.tail=t;b.align_roll(Vector((0,-1,0)))
        if parent:b.parent=bones[parent]
        bones[n]=b
    bone('root',(0,0,0),(0,0,.2));bone('pelvis',(0,.04,1.90),(0,.055,2.2),'root');bone('lumbar',(0,.055,2.2),(0,.095,2.70),'pelvis');bone('thorax',(0,.095,2.7),(0,.10,3.31),'lumbar');bone('neck',(0,.10,3.31),(0,.035,3.72),'thorax')
    bone('head',head['bone_head'],head['bone_tail'],'neck');bone('jaw',head['jaw_head'],head['jaw_tail'],'head')
    for i,(a,b) in enumerate(zip(head['tongue_points'],head['tongue_points'][1:])):bone('tongue.%02d'%i,a,b,'jaw' if i==0 else 'tongue.%02d'%(i-1))
    for s,side in [(1,'L'),(-1,'R')]:
        a=rest[side];bone('clavicle.'+side,(s*.06,.085,3.32),a['shoulder'],'thorax');bone('upper_arm.'+side,a['shoulder'],a['elbow'],'clavicle.'+side);bone('forearm.'+side,a['elbow'],a['wrist'],'upper_arm.'+side);bone('hand.'+side,a['wrist'],(s*1.50,-.03,2.13),'forearm.'+side)
        for i in range(4):
            pts=a['finger'+str(i)]
            for j in range(3):bone('finger%d.%02d.%s'%(i,j,side),pts[j],pts[j+1],'hand.'+side if j==0 else 'finger%d.%02d.%s'%(i,j-1,side))
        pts=a['thumb'];bone('thumb.00.'+side,pts[0],pts[1],'hand.'+side);bone('thumb.01.'+side,pts[1],pts[2],'thumb.00.'+side)
        bone('thigh.'+side,a['hip'],a['knee'],'pelvis');bone('shin.'+side,a['knee'],a['ankle'],'thigh.'+side);bone('foot.'+side,a['ankle'],(s*.47,-.38,.09),'shin.'+side);bone('toes.'+side,(s*.47,-.38,.09),(s*.47,-.72,.04),'foot.'+side)
    bpy.ops.object.mode_set(mode='OBJECT');rig.show_in_front=True;rig.hide_render=True;rig.hide_set(True);rig['status']='Aligned unweighted guide; show from Outliner for rigging. Not skinned.';group('RIG | unhide to begin weighting',[rig])
    def setup(scene):
        scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB'
        try:
            prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
            for d in prefs.devices:d.use=d.type=='OPTIX'
            scene.cycles.device='GPU' if any(d.type=='OPTIX' for d in prefs.devices) else 'CPU'
        except Exception:pass
        scene.world=bpy.data.worlds.new(scene.name+' atmosphere');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.023,.03,.04,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.15
    def camera(name,loc,target,lens=55,ortho=None):
        bpy.ops.object.camera_add(location=loc);o=bpy.context.object;o.name=name;aim(o,target)
        if ortho:o.data.type='ORTHO';o.data.ortho_scale=ortho
        else:o.data.lens=lens
        return o
    def light(name,loc,target,power,size,color):
        bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;o.name=name;o.data.energy=power;o.data.shape='DISK';o.data.size=size;o.data.color=color;aim(o,target);return o
    setup(author);author.camera=camera('Neutral full-body camera',(4.3,-11,4.9),(0,-.07,2.09),ortho=4.80)
    light('Neutral key',(-3,-4,5.3),(0,0,2.4),640,3,(.86,.91,1));light('Neutral fill',(3,-1.8,2.4),(0,0,2.3),235,2.5,(1,.84,.74));light('Neutral rim',(1,2.5,4),(0,0,2.5),650,2,(.62,.75,1))
    author.render.resolution_x=1300;author.render.resolution_y=1600
    # A second scene presents the same editable geometry; no fake pose or hidden substitutes.
    cinematic=bpy.data.scenes.new('02 | Sewer flashlight portrait');set_scene(cinematic);setup(cinematic)
    for o in model:cinematic.collection.objects.link(o)
    concrete=H['mat']('Sewer concrete',(.025,.03,.031),.78);n=concrete.node_tree.nodes;l=concrete.node_tree.links;tc=n.new('ShaderNodeTexCoord');ns=n.new('ShaderNodeTexNoise');ns.inputs['Scale'].default_value=5;ns.inputs['Detail'].default_value=5;l.new(tc.outputs['Object'],ns.inputs['Vector']);bump=n.new('ShaderNodeBump');bump.inputs['Distance'].default_value=.022;bump.inputs['Strength'].default_value=.6;l.new(ns.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs[0],n.get('Principled BSDF').inputs['Normal'])
    def cube(name,loc,scale,mat):
        bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=name;o.scale=scale;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(mat);return o
    cube('Wet corridor floor',(0,3,-.105),(7,20,.2),concrete);cube('Left wall',(-2.75,3,2),(.3,20,4.4),concrete);cube('Right wall',(2.75,3,2),(.3,20,4.4),concrete)
    iron=H['mat']('Oxidised iron',(.04,.033,.021),.65)
    for s in [-1,1]:
        for z in [.7,1.1]:tube('Sewer pipe',[(s*2.48,-5,z),(s*2.48,10,z)],[.09,.09],iron)
    for y in [1.5,4.5,7.5]:
        for s in [-1,1]:cube('Reinforcement',(s*2.53,y,2),(.18,.18,4.2),iron)
    water=H['mat']('Black shallow water',(.008,.012,.016),.13);water.node_tree.nodes.get('Principled BSDF').inputs['Metallic'].default_value=.2
    for i in range(13):
        x=random.uniform(-2.2,2.2);y=random.uniform(-2,6);rx=random.uniform(.15,.75);ry=random.uniform(.2,.9);ph=random.random()*6.28;v=[(x,y,-.002)]
        for j in range(48):
            a=j*math.tau/48;r=1+.16*math.sin(3*a+ph)+.10*math.sin(7*a-ph);v.append((x+rx*r*math.cos(a),y+ry*r*math.sin(a),-.002))
        mesh('Irregular puddle',v,[(0,j+1,(j+1)%48+1) for j in range(48)],water)
    cinematic.camera=camera('Flashlight portrait',(1.9,-7.2,2.85),(0,-.04,2.15),lens=43)
    bpy.ops.object.light_add(type='SPOT',location=(1,-4,2.7));flash=bpy.context.object;flash.name='Flickering flashlight';flash.data.energy=1300;flash.data.color=(.83,.91,1);flash.data.spot_size=math.radians(59);flash.data.spot_blend=.45;flash.data.shadow_soft_size=.09;aim(flash,(0,0,2.3))
    for f,e in [(1,1300),(5,1210),(6,250),(7,1380),(14,1110),(15,120),(16,1300),(24,1280)]:flash.data.energy=e;flash.data.keyframe_insert(data_path='energy',frame=f)
    cinematic.frame_set(1);cinematic.frame_end=24;cinematic.render.fps=24
    light('Cold sewer bounce',(-2,2,3.5),(0,0,2.3),180,1.5,(.21,.42,.57));light('Faint frontal return',(-2,-2,2),(0,0,2.3),55,2,(.44,.50,.59))
    cinematic.render.resolution_x=1600;cinematic.render.resolution_y=1800;cinematic.view_settings.exposure=-.20
    set_scene(author);bpy.ops.object.select_all(action='DESELECT');body.select_set(True);bpy.context.view_layer.objects.active=body
    for screen in bpy.data.screens:
        for a in screen.areas:
            if a.type=='VIEW_3D':
                a.spaces.active.shading.type='MATERIAL';r=a.spaces.active.region_3d;r.view_rotation=Quaternion((1,0,0),math.pi/2);r.view_location=(0,0,2.1);r.view_distance=6.5;r.view_perspective='ORTHO'
    info={'head_parent':'neck','head_min_z':min(v.co.z for o in head['objects'] if o.type=='MESH' for v in o.data.vertices),'pelvis_top_z':2.2,'forward':'-Y','up':'+Z','rig_bones':len(rig.data.bones),'rig_weighted':False,'anatomy_vertices':len(body.data.vertices),'mesh_objects':len(model),'total_vertices':sum(len(o.data.vertices) for o in model if o.type=='MESH'),'exposed_ribs':12,'sternal_plates':7,'no_eyes':True}
    (OUT/'Validation.json').write_text(json.dumps(info,indent=2))
    text=bpy.data.texts.new('READ ME - sculpt status');text.write('Pale Stalker: neck-mounted eyeless head; no abdominal or pelvic mouth. Neutral A-pose sculpt, pale center/red extremities, detailed rib cage and muscle fibers. RIG collection contains hidden aligned unweighted guide (+Z up, -Y forward), head parent neck. Not production topology, UV-unwrapped, baked or skinned. Scene02 uses the SAME unposed geometry in a sewer flashlight portrait. Earlier abdominal version is preserved separately.')
    author.render.filepath=str(OUT/'Neutral_Inspection.png');bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'PaleStalker.blend'));log('Saved native asset')
    bpy.ops.render.render(write_still=True);log('Neutral render complete')
    # Isolate the new chest/head details under neutral inspection light.
    oldcam=author.camera;close=camera('Head and thorax detail camera',(1.5,-5.3,3.74),(0,-.07,3.15),ortho=2.42);author.camera=close;author.render.resolution_x=1600;author.render.resolution_y=1600;author.render.filepath=str(OUT/'Head_Chest_Detail.png');bpy.ops.render.render(write_still=True);author.camera=oldcam;author.render.resolution_x=1300;author.render.resolution_y=1600;log('Head chest detail render complete')
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'PaleStalker.blend'))
    set_scene(cinematic);cinematic.render.filepath=str(OUT/'Sewer_Portrait.png');bpy.ops.render.render(write_still=True);log('Sewer render complete')
    (OUT/'Complete.txt').write_text('Native asset, neutral anatomy, chest closeup and sewer portrait completed.')
try:build()
except Exception:(OUT/'Error.txt').write_text(traceback.format_exc());raise
