# Jarvis Manor

Open **jarvis scenes/Jarvis_Manor.unity** when you are ready to try it. This is a standalone first-pass horror mansion, built directly in Unity with editable mesh pieces and HDRP materials. It does not replace any existing level, change the shared render pipeline, or add itself to build settings.

## Layout

Two storeys, a central hall and staircase, upstairs gallery, library, parlour/fireplace, dining room, kitchen, and four upstairs bedrooms. Outside: gravel approach, boundary fencing, gate pillars, dead trees and warm lamps. HDRP includes a cloudy dusk sky and fog. This is a blockout with simple furnishing, not final production art.

## Controls

Play this scene on its own. WASD to walk, mouse to look, Shift to run, E to open/close nearby doors, F for the flashlight, Escape to release the cursor; click to capture it again.

## Organization

- `jarvis scenes`: the mansion scene
- `jarvis scripts`: isolated player and door scripts, with the one-time generator in Editor
- `jarvis materials`: HDRP materials and atmosphere profile
- `jarvis models`: generated editable architectural meshes
- `jarvis textures`: procedural tiling surfaces and cloud field
- `jarvis previews`: reserved for future screenshots
- `jarvis docs`: this guide and verification reports

## Compatibility and verification

Built against the installed Unity **6000.5.1f1** and HDRP **17.5.0** (the project files differ from the version mentioned in the request). Uses HDRP Cloud Layer; volumetric cloud support remains unchanged in the shared pipeline. Fog depends on the selected HDRP quality asset's existing volumetric support.

The first automated preview attempt hit a D3D12 graphics-driver crash after the scene was saved. Automatic GPU preview rendering has been disabled. Do not treat the initial preview files as successful verification. Static checks are recorded separately; a full interactive play-through remains necessary.

The generator refuses to overwrite an existing mansion scene, so later edits to this level are preserved.
