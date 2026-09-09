# Pale Stalker — neck-mounted redesign

Open **PaleStalker.blend**. This is the new design, with the head and mouth on the neck above the chest. The rejected abdominal-head version is preserved separately; it is not the current design.

## Inside Blender

- **01 | Neutral A-pose - neck head**: editable sculpt source with a pale central body, wine-red hands and feet, exposed rib cage and sternum, longitudinal muscle fibers, tendons, an eyeless head, angular open jaw, irregular teeth and a long tongue.
- **02 | Sewer flashlight portrait**: the same geometry under dark sewer lighting. The flashlight has a short flicker animation. The character is still in its neutral pose, not an animated crawl.
- **RIG | unhide to begin weighting**: hidden armature guide, aligned with the model. Blender +Z is up and -Y is forward. The head is parented to the neck, not the pelvis. Reveal the armature in the Outliner to begin rigging.

## Production status

This is a detailed sculpt source, **not a finished game-ready character**. The guide is unweighted. The body is voxel-fused sculpt geometry and the muscles, bones and oral details are separate editable assemblies. Retopology, UVs, material baking and skin weights remain necessary before reliable game animation. The Blender procedural materials need baking or recreation for Unity. The sewer is a presentation scene, not part of the gameplay character.

## Rendered inspections

- `Neutral_Inspection.png` — full body under neutral lighting
- `Head_Chest_Detail.png` — close inspection of the new head and layered chest anatomy
- `Sewer_Portrait.png` — flashlight-lit horror presentation
- `Validation.json` — construction metadata

The earlier assets have not been deleted or overwritten.
