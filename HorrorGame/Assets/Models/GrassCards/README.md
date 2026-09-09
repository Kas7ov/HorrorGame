# Three-plane grass

Open **Grass_Triangle_3Planes.blend**. The startup scene contains only the grass. The separate Preview scene supplies the camera, lights and floor.

- Three vertical planes arranged as a triangle; 12 vertices and 6 triangles.
- 0.72 m tall, 0.80 m triangle side; pivot at ground center.
- Transparent grass cutout, double-sided material, packed texture.
- **Grass_Triangle_3Planes.fbx** contains just the grass mesh for game import.
- **Grass_Blade_Cutout.png** is the color + alpha texture.

For Unity HDRP, assign the PNG to an HDRP/Lit material's Base Map, enable Alpha Clipping (threshold 0.35) and Double-Sided, and set Smoothness to 0.2. Blender materials do not automatically become HDRP materials.

## Source and license

Grass texture: **Yughues / Nobiax — Grass Pack #01**, CC0 (public domain).
https://opengameart.org/content/grass-pack-01
https://creativecommons.org/publicdomain/zero/1.0/

The first grass texture in that pack was converted from TGA to PNG without changing its design. The three-plane mesh was constructed for this project; the pack's original model is not used.
