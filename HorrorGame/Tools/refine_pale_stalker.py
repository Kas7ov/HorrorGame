"""Render-driven organic tissue refinement for the saved neck-mounted sculpt."""
import bpy, math, random, traceback, json, sys
from pathlib import Path
from mathutils import Vector, noise
from mathutils.kdtree import KDTree
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parent.parent;OUT=ROOT/'Assets/Models/PaleStalker'
sys.path.insert(0,str(ROOT/'Tools'))
H={'__file__':str(ROOT/'Tools/build_abdominal_cryptid.py')}
exec((ROOT/'Tools/build_abdominal_cryptid.py').read_text().split('\ntry:build()')[0],H)
from cryptid_materials import refine_materials_existing
from refine_cryptid_cranium import refine_head
tube,mesh,apply,join,aim=H['smooth_tube'],H['H']['mesh'],H['apply'],H['join'],H['aim']
random.seed(943)
def log(s):
    with (OUT/'RefinementStatus.txt').open('a') as f:f.write(s+'\n')
def step(a,b,x):
    t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)
def att(o,name,values):
    a=o.data.attributes.get(name) or o.data.attributes.new(name=name,type='FLOAT',domain='POINT')
    if isinstance(values,(float,int)):
        for d in a.data:d.value=values
    else:
        for d,v in zip(a.data,values):d.value=v
def main():
    bpy.ops.wm.open_mainfile(filepath=str(OUT/'PaleStalker.blend'))
    author=bpy.data.scenes['01 | Neutral A-pose - neck head'];cinema=bpy.data.scenes['02 | Sewer flashlight portrait'];bpy.context.window.scene=author;bpy.context.view_layer.update()
    if author.get('organic_refinement')==1:raise RuntimeError('Organic pass already applied; rebuild the source first before applying twice.')
    M=refine_materials_existing();log('Updated physically shaded dermis and wound palette')
    body=author.objects['BODY | continuous lean dermis'];body.data.update()
    # Remove the visual contribution of out-of-silhouette oblique ribbons, retaining originals.
    for o in list(author.objects):
        if o.name.startswith('External oblique'):
            o.hide_render=True;o.hide_set(True);o['superseded_detail']=True
    # Pair slight relaxation around connective joints with undulating dermal relief.
    vg=body.vertex_groups.new(name='Localized connective tissue relaxation')
    for v in body.data.vertices:
        p=v.co;shoulder=math.exp(-(((abs(p.x)-.39)/.13)**2+((p.z-3.33)/.14)**2))
        hip=math.exp(-(((abs(p.x)-.24)/.12)**2+((p.z-2.01)/.17)**2))
        w=max(shoulder,hip)*.75
        if w>.02:vg.add([v.index],w,'REPLACE')
    mod=body.modifiers.new('Organic shoulder and hip continuity','SMOOTH');mod.factor=.65;mod.iterations=10;mod.vertex_group=vg.name;apply(body,mod)
    body.vertex_groups.remove(vg);body.data.update();bpy.context.view_layer.update()
    surface=BVHTree.FromObject(body,bpy.context.evaluated_depsgraph_get())
    patches=[]
    for o in list(author.objects):
        if o.type=='MESH' and not o.hide_render and len(o.data.vertices)==1666 and not o.name.startswith('HEAD'):
            patches.append(o)
    log('Located %d anatomical muscle surfaces'%len(patches))
    # Compute continuous bruised wound margins on the actual underlying dermis.
    samples=[]
    for o in patches:
        for v in list(o.data.vertices)[::3]:samples.append(o.matrix_world@v.co)
    kd=KDTree(len(samples))
    for i,p in enumerate(samples):kd.insert(p,i)
    kd.balance();normals=[v.normal.copy() for v in body.data.vertices];injuries=[]
    for v,n in zip(body.data.vertices,normals):
        p=v.co.copy();_,_,distance=kd.find(p)
        grit=noise.noise(p*37+Vector((1.2,5.8,3.1)))
        stain=math.exp(-((distance/(.030+.015*(grit+.5)))**2))
        abrasion=.10*step(.11,.45,noise.noise(p*14))*step(.25,1.1,p.z)
        injury=min(1,stain*(.64+.31*step(-.3,.35,grit))+abrasion)
        injuries.append(injury)
        rough=noise.noise(p*63)*.0019+noise.noise(p*22)*.0024
        # Irregular restrained cross creases around joints, not uniform rings.
        joint=max(math.exp(-((p.z-z)/.035)**2) for z in [1.17,.31,2.40,2.91])
        crease=math.sin(p.z*310+p.x*12+noise.noise(p*50)*2)*.0018*joint
        v.co+=n*(rough*(.25+injury)+crease)
    att(body,'injury',injuries);body.data.update()
    added=[]
    # Tear and curl interrupted, thin dermal margins around major exposed fascicles.
    for patch in patches:
        if patch.name.startswith(('Intercostal','Pectoralis','Erector')):continue
        vv,ff=[],[];normals=[v.normal.copy() for v in patch.data.vertices]
        for edgecol,innercol in [(0,1),(16,15)]:
            start=len(vv)
            for row in range(5,44):
                p=patch.data.vertices[row*17+edgecol].co.copy();q=patch.data.vertices[row*17+innercol].co.copy();n=normals[row*17+edgecol]
                if n.y>0 and not patch.name.startswith(('Scapular','Trapezius','Triceps','Posterior')):n=-n
                r=noise.noise(p*71);out=(p-q)*(.8+.4*math.sin(row*2.4))
                vv.extend([q+n*.001,p+n*(.002+.002*r),p+out+n*(.005+.006*max(0,r))])
            for i in range(38):
                k=start+i*3
                if noise.noise(vv[k]*40) > -.25:
                    ff.append((k,k+1,k+4,k+3));ff.append((k+1,k+2,k+5,k+4))
        if ff:
            o=mesh('TORN DERMIS | '+patch.name,vv,ff,M['skin']);att(o,'injury',[.35+.38*step(-.3,.4,noise.noise(v.co*33)) for v in o.data.vertices]);att(o,'bloodflow',[max(step(1.03,1.50,abs(v.co.x)),1-step(.22,.69,v.co.z)) for v in o.data.vertices]);added.append(o)
    # True fascicle ridges and damaged surface relief, avoiding clean plastic leaves.
    for o in patches:
        ns=[v.normal.copy() for v in o.data.vertices]
        for v,n in zip(o.data.vertices,ns):
            p=v.co.copy();v.co+=n*(.0015*noise.noise(p*145)+.0012*noise.noise(p*53))
        o.data.update()
    # Irregularly retained fascia/blood patches break the neat ivory rib-strip rhythm.
    for o in list(author.objects):
        if not o.name.startswith(('Exposed flattened rib','Sternal plate')):continue
        o.data.materials.append(M['fascia']);fi=len(o.data.materials)-1;o.data.materials.append(M['muscle']);mi=len(o.data.materials)-1
        ns=[v.normal.copy() for v in o.data.vertices]
        for v,n in zip(o.data.vertices,ns):
            p=v.co.copy();v.co+=n*(noise.noise(p*118)*.0012)
            if o.name.startswith('Exposed flattened rib'):v.co.y+=.008*(.3+step(.04,.28,abs(p.x)))
        o.data.update()
        for f in o.data.polygons:
            p=f.center;x=abs(p.x);r=noise.noise(p*17+Vector((0,2.2,0)))
            if r>.34 or x>.28:f.material_index=mi
            elif r>.05:f.material_index=fi
    # Recessed torn abdominal fibers rather than a featureless ivory waist.
    bpy.context.view_layer.update();surface=BVHTree.FromObject(body,bpy.context.evaluated_depsgraph_get())
    for s in [-1,1]:
        for k in range(4):
            z=2.61-k*.11;vv=[];ff=[];nx,nz=18,28
            for i in range(nz+1):
                t=i/nz
                for j in range(nx+1):
                    u=-1+2*j/nx;x=s*(.058+.025*u*math.sin(math.pi*t)**.3);h=z-.092*t
                    p,n,_,_=surface.ray_cast(Vector((x,-2,h)),Vector((0,1,0)),4)
                    if p is None:p,n=Vector((x,-.15,h)),Vector((0,-1,0))
                    vv.append(p+n*(.002+.005*math.sin(math.pi*t)*math.sin(math.pi*(u+1)/2)+.0013*math.sin(u*math.pi*9)))
            for i in range(nz):
                for j in range(nx):
                    a=i*(nx+1)+j;ff.append((a,a+1,a+nx+2,a+nx+1))
            o=mesh('ABDOMEN | exposed rectus aponeurosis',vv,ff,M['fascia']);added.append(o)
        # Torn oblique cords conform to the narrow waist instead of floating outside it.
        for k in range(4):
            pts=[]
            for j in range(17):
                t=j/16;x=s*(.15+.035*math.sin(t*math.pi)+k*.007);z=2.65-.48*t
                p,n,_,_=surface.ray_cast(Vector((x,-2,z)),Vector((0,1,0)),4)
                if p is not None:pts.append(p+n*(.003+.002*math.sin(t*8+k)))
            if len(pts)>2:added.append(tube('OBLIQUE | torn tendinous cord',pts,[.0015]+[.003]*(len(pts)-2)+[.0005],None,M['fascia'] if k%3==0 else M['muscle']))
    log('Torn borders, wounded dermis and irregular rib tissue complete')
    newhead=refine_head(author,M,{'smooth_tube':tube,'mesh':mesh,'apply':apply});added+=newhead
    col=bpy.data.collections.new('REFINEMENT | torn dermis and recessed anatomy');author.collection.children.link(col)
    for o in added:
        for c in list(o.users_collection):c.objects.unlink(o)
        col.objects.link(o)
        if o.name not in cinema.objects:cinema.collection.objects.link(o)
    # Smaller side-biased key reveals the geometric relief without burying it in darkness.
    author.objects['Neutral key'].data.energy=500;author.objects['Neutral key'].data.size=1.8
    author.objects['Neutral fill'].data.energy=135;author.objects['Neutral rim'].data.energy=420
    author.view_settings.exposure=-.25
    author['organic_refinement']=1
    bpy.ops.object.select_all(action='DESELECT');body.select_set(True);bpy.context.view_layer.objects.active=body
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'PaleStalker.blend'));log('Refined native sculpt saved')
    close=author.objects['Head and thorax detail camera'];oldcam=author.camera;author.camera=close;author.render.resolution_x=1800;author.render.resolution_y=1800;author.render.filepath=str(OUT/'Head_Chest_Detail.png');bpy.ops.render.render(write_still=True);log('Refined head and chest rendered')
    author.camera=oldcam;author.render.resolution_x=1300;author.render.resolution_y=1600;author.render.filepath=str(OUT/'Neutral_Inspection.png');bpy.ops.render.render(write_still=True);log('Refined neutral rendered')
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'PaleStalker.blend'))
    bpy.context.window.scene=cinema;cinema.render.filepath=str(OUT/'Sewer_Portrait.png');bpy.ops.render.render(write_still=True);log('Refined sewer portrait rendered')
    (OUT/'RefinementComplete.txt').write_text('Organic surface pass saved; neutral, detail and sewer rendered.')
try:main()
except Exception:(OUT/'RefinementError.txt').write_text(traceback.format_exc());raise
