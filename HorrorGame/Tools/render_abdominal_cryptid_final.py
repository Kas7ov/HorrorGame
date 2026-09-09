"""Render exact final 16:9 framing at preview or native 7680x4320 resolution."""
import bpy, sys, json, traceback
from pathlib import Path
P=Path(r'E:\EpsteinHorror\HorrorGame\Assets\Models\AbdominalCryptid')
mode=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'preview'
try:
    bpy.ops.wm.open_mainfile(filepath=str(P/'AbdominalCryptid.blend'))
    scene=bpy.data.scenes['02 | Sewer backward crawl'];bpy.context.window.scene=scene
    scene.camera.data.lens=32
    scene.view_settings.exposure=-.35
    scene.render.engine='CYCLES';scene.cycles.use_denoising=True;scene.cycles.samples=48 if mode=='8k' else 32
    prefs=bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type='OPTIX';prefs.get_devices()
    for d in prefs.devices:d.use=d.type=='OPTIX'
    scene.cycles.device='GPU' if any(d.type=='OPTIX' for d in prefs.devices) else 'CPU'
    if hasattr(scene.cycles,'use_auto_tile'):scene.cycles.use_auto_tile=True;scene.cycles.tile_size=1024
    flashlight=scene.objects['Harsh flashlight']
    for frame,energy in [(1,760),(5,720),(6,180),(7,780),(14,650),(15,90),(16,740),(24,760)]:
        flashlight.data.energy=energy;flashlight.data.keyframe_insert(data_path='energy',frame=frame)
    scene.frame_start=1;scene.frame_end=24;scene.render.fps=24;scene.frame_set(1)
    scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB';scene.render.resolution_percentage=100
    scene.render.resolution_x=7680 if mode=='8k' else 1600
    scene.render.resolution_y=4320 if mode=='8k' else 900
    scene.render.filepath=str(P/('Sewer_Crawl_8K.png' if mode=='8k' else 'Sewer_Crawl_Preview.png'))
    # Persist composition and flashlight keyframes. Keep authoring source the startup scene.
    bpy.context.window.scene=bpy.data.scenes['01 | Neutral rigging source']
    bpy.ops.wm.save_as_mainfile(filepath=str(P/'AbdominalCryptid.blend'))
    bpy.context.window.scene=scene
    (P/'FinalRenderStatus.json').write_text(json.dumps({'status':'rendering','mode':mode,'device':scene.cycles.device,'width':scene.render.resolution_x,'height':scene.render.resolution_y}))
    bpy.ops.render.render(write_still=True)
    (P/'FinalRenderStatus.json').write_text(json.dumps({'status':'complete','mode':mode,'path':scene.render.filepath,'device':scene.cycles.device,'width':scene.render.resolution_x,'height':scene.render.resolution_y}))
except Exception:
    (P/'FinalRenderError.txt').write_text(traceback.format_exc());raise
