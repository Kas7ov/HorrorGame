# Dragon eye horizon

Only the dragon event is implemented; portal and cutscene plans are not changed.

In the Ocean scene, **Dragon Eye Horizon** owns the effect. Your original Sky and Fog volume/profile is untouched. The repaired **DragonEyeSkyShader** is an HDRP fullscreen graph, drawn after the original sky and before HDRP fog/clouds, so the eye lives behind the clouds rather than replacing them. Depth masks stop it drawing over terrain, trees or buildings.

- Move/resize its child **Dragon Eye Trigger** (Box Collider) to choose where it opens. The player must walk into it in Play Mode. It fires once per play session.
- **Eye Open Amount**: 0 closed/off, 1 fully open. Animation takes **Opening Seconds**.
- **Azimuth / Elevation** set a fixed compass direction and height. **Angular Width / Height Ratio** set its apparent size. It does not follow camera rotation.
- **Radiance** controls brightness for HDRP exposure. **Opacity / Edge Softness** blend the photographed artwork into the sky.
- **Atmosphere Strength** controls the slight red vision tint plus slowly drifting, density-masked HDRP red smoke. Both fade with the eye and are off when closed.
- The event profile enables HDRP volumetric fog only while the eye is open; the original sky profile has Fog inactive. **Smoke Density Multiplier** controls smoke visibility independently of the screen tint (default 6). **Smoke Size** concentrates the moving wisps into a 72 x 14 x 72 metre region around the trigger's assigned player. **Smoke Tint** is brighter crimson for visible light scattering. Lower density for more transparency. The density mask and soft edges leave gaps instead of a solid red wall.
- Inspector buttons **Preview fully open** and **Reset / close eye** provide a reversible edit-time preview. Reset before saving the normal starting state.
- **Look toward eye in Scene view** frames an elevated view without moving your player or game camera. In Play Mode, **Test box-trigger crossing** is a one-shot collider test that restores the trigger position afterward.
- Call `DragonEyeEvent.OpenEye()` from a future gameplay action or Timeline UnityEvent if you change the trigger later.
- In Play Mode the existing sun fades to **Activated Sun Brightness** (default 20%) as the eye opens, and stays dim until reset. Closing/disabling the event or stopping Play Mode restores the exact original light intensity. Assign **Sun Light** to override automatic scene-sun selection; the original HDRP sky profile is still untouched.
- **Hide Sun Disk When Active** (on by default) fades out HDRP's sun disk and its halo as the dragon appears, without disabling the directional light, atmospheric scattering or changing shadow softness. The previous 20% illumination remains. Reset/disable/stop restores the original disk tint and halo too.
- The main camera trembles only during the animated opening: **Opening Shake Degrees / Metres / Frequency** adjust it, and either strength can be set to zero. The shake ramps in and out smoothly and is applied only during rendering, so mouse look/player movement never accumulate the shake. Edit-time full-open previews intentionally do not modify the sun or shake the camera.

All effect assets and scripts are in this folder. The eye shader is self-contained: its custom function is embedded directly in **DragonEyeSkyShader**, with no separate imported HLSL file. The removed include has a recovery copy at **Tools/Backups/DragonEyeHorizon.before-inline.txt**, outside Assets and the game build. The original graph is backed up as **OriginalDragonSkyGraph.txt**. The original eye photograph is unchanged; its beige border is cropped in the shader.

This uses HDRP 17.5's AfterOpaqueAndSky injection point (your installed Unity 6000.5.1). Porting to older HDRP versions requires adapting that pass timing. The JPG is 516px, so very large closeups are limited by the supplied artwork resolution.

Verified in the running Ocean scene: an actual physics overlap triggered progressive opening to 1, smoke enabled, red vision weight reached 0.6, and the shader reported no errors. The scene is saved with Eye Open Amount 0. Test output: Tools/DragonEyeVerification.txt.
