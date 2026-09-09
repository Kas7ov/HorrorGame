"""Restrained, physically shaded tissue palette for the anatomical cryptid.

Native Blender helper.  ``create_materials()`` has no scene side effects and
returns reusable materials.  Skin consumes FLOAT/POINT ``bloodflow`` and
``injury`` attributes (distal circulation and local flayed-patch margins).
Geometry supplies the major
muscle fibres and scars: these shaders add only millimetre-scale surface detail.
"""

import bpy


def _material(name, color, roughness, subsurface=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = (*color, 1)
    mat.roughness = roughness
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["IOR"].default_value = 1.4
    bsdf.inputs["Subsurface Weight"].default_value = subsurface
    bsdf.inputs["Subsurface Radius"].default_value = (1.0, 0.34, 0.19)
    bsdf.inputs["Subsurface Scale"].default_value = 0.008
    bsdf.inputs["Specular IOR Level"].default_value = 0.32
    tex = nodes.new("ShaderNodeTexCoord")
    tex.label = "Metre-scale skin / normalized local tissue coordinates"
    return mat, nodes, links, bsdf, tex


def _noise(nodes, links, vector, scale, detail=2.0, roughness=0.6):
    node = nodes.new("ShaderNodeTexNoise")
    node.inputs["Scale"].default_value = scale
    node.inputs["Detail"].default_value = detail
    node.inputs["Roughness"].default_value = roughness
    links.new(vector, node.inputs["Vector"])
    return node


def _ramp(nodes, links, value, colors):
    node = nodes.new("ShaderNodeValToRGB")
    ramp = node.color_ramp
    ramp.interpolation = "EASE"
    while len(ramp.elements) > 2:
        ramp.elements.remove(ramp.elements[-1])
    for element, (position, color) in zip(ramp.elements, (colors[0], colors[-1])):
        element.position = position
        element.color = (*color[:3], color[3] if len(color) > 3 else 1)
    for position, color in colors[1:-1]:
        element = ramp.elements.new(position)
        element.color = (*color[:3], color[3] if len(color) > 3 else 1)
    links.new(value, node.inputs["Fac"])
    return node.outputs["Color"]


def _math(nodes, links, operation, a, b):
    node = nodes.new("ShaderNodeMath")
    node.operation = operation
    for index, value in enumerate((a, b)):
        if isinstance(value, (float, int)):
            node.inputs[index].default_value = value
        else:
            links.new(value, node.inputs[index])
    return node.outputs[0]


def _mix(nodes, links, factor, first, second):
    node = nodes.new("ShaderNodeMixRGB")
    for index, value in enumerate((factor, first, second)):
        if isinstance(value, (float, int)):
            node.inputs[index].default_value = value
        elif isinstance(value, (tuple, list)):
            node.inputs[index].default_value = (*value[:3], 1)
        else:
            links.new(value, node.inputs[index])
    return node.outputs["Color"]


def _bump(nodes, links, bsdf, height, distance, strength, normal=None):
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Distance"].default_value = distance
    bump.inputs["Strength"].default_value = strength
    links.new(height, bump.inputs["Height"])
    if normal is not None:
        links.new(normal, bump.inputs["Normal"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return bump


def _fibres(nodes, links, tex, density=55.0):
    """Fine longitudinal irregularity, not a conspicuous stripe pattern."""
    stretch = nodes.new("ShaderNodeVectorMath")
    stretch.operation = "MULTIPLY"
    stretch.inputs[1].default_value = (density, density, 2.3)
    links.new(tex.outputs["Generated"], stretch.inputs[0])
    return _noise(nodes, links, stretch.outputs["Vector"], 4.0, 2.0)


def _skin():
    mat, n, l, bsdf, tex = _material(
        "CRYPTID | pale dermis / wine-red distal circulation",
        (0.315, 0.30, 0.28), 0.51, 0.045,
    )
    # Pallid grey-ivory, never white plastic. Injury is an anatomical mask, so
    # strong bruising is confined to flayed margins instead of covering the
    # entire body with an unrelated camouflage pattern.
    broad = _noise(n, l, tex.outputs["Object"], 4.8, 2.5)
    ivory = _ramp(n, l, broad.outputs["Fac"], [
        (0.15, (0.19, 0.18, 0.175)),
        (0.52, (0.315, 0.30, 0.28)),
        (0.85, (0.425, 0.405, 0.37)),
    ])
    wine = _ramp(n, l, broad.outputs["Fac"], [
        (0.18, (0.027, 0.006, 0.011)),
        (0.52, (0.078, 0.014, 0.022)),
        (0.85, (0.145, 0.030, 0.039)),
    ])
    flow = n.new("ShaderNodeAttribute")
    flow.attribute_name = "bloodflow"
    flow.label = "0 pale central skin / 1 red hands and feet"
    flow_clamped = _math(n, l, "MINIMUM", _math(n, l, "MAXIMUM", flow.outputs["Fac"], 0.0), 1.0)
    palette = _mix(n, l, flow_clamped, ivory, wine)

    injury = n.new("ShaderNodeAttribute")
    injury.attribute_name = "injury"
    injury.label = "Bruising concentrated around actual flayed anatomy"
    inj = _math(n, l, "MINIMUM", _math(n, l, "MAXIMUM", injury.outputs["Fac"], 0.0), 1.0)
    wound_noise = _noise(n, l, tex.outputs["Object"], 44.0, 4.0, 0.7)
    wound_noise.label = "Clotted and stippled wound margins, centimetre scale"
    ragged = _math(n, l, "ADD", _math(n, l, "MULTIPLY", wound_noise.outputs["Fac"], 0.95), 0.32)
    ragged = _math(n, l, "MINIMUM", _math(n, l, "MULTIPLY", inj, ragged), 1.0)
    bruise = _ramp(n, l, wound_noise.outputs["Fac"], [
        (0.20, (0.023, 0.009, 0.014)),
        (0.40, (0.058, 0.023, 0.032)),
        (0.58, (0.15, 0.060, 0.056)),
        (0.76, (0.245, 0.145, 0.115)),
    ])
    palette = _mix(n, l, ragged, palette, bruise)

    # Sparse, very low-contrast subdermal capillary fragments. The network is
    # masked so it cannot become a uniform cracked-stone pattern.
    vessels = n.new("ShaderNodeTexVoronoi")
    vessels.feature = "DISTANCE_TO_EDGE"
    vessels.distance = "EUCLIDEAN"
    vessels.inputs["Scale"].default_value = 24.0
    l.new(tex.outputs["Object"], vessels.inputs["Vector"])
    vessel_line = _ramp(n, l, vessels.outputs["Distance"], [
        (0.002, (1, 1, 1)), (0.024, (0, 0, 0)),
    ])
    vessels_mask = _noise(n, l, tex.outputs["Object"], 10.0, 2.0)
    sparse = _ramp(n, l, vessels_mask.outputs["Fac"], [
        (0.54, (0, 0, 0)), (0.73, (0.13, 0.13, 0.13)),
    ])
    capillary = _math(n, l, "MULTIPLY", vessel_line, sparse)
    l.new(_mix(n, l, capillary, palette, (0.073, 0.029, 0.039)), bsdf.inputs["Base Color"])

    # Two relief scales survive both a full-body render and a head close-up.
    # Explicit geometry supplies tears; this supplies desiccation and pores.
    coarse = _noise(n, l, tex.outputs["Object"], 82.0, 3.3, 0.7)
    base_relief = _bump(n, l, bsdf, coarse.outputs["Fac"], 0.0025, 0.40)
    pores = _noise(n, l, tex.outputs["Object"], 640.0, 2.0)
    _bump(n, l, bsdf, pores.outputs["Fac"], 0.00075, 0.34, base_relief.outputs["Normal"])
    rough = _ramp(n, l, broad.outputs["Fac"], [
        (0.15, (0.44, 0.44, 0.44)), (0.85, (0.65, 0.65, 0.65)),
    ])
    l.new(_mix(n, l, ragged, rough, (0.325, 0.325, 0.325)), bsdf.inputs["Roughness"])
    mat["bloodflow_attribute"] = "FLOAT POINT: 0 ivory core, 1 wine-red extremities"
    mat["injury_attribute"] = "FLOAT POINT: 0 intact dermis, 1 locally bruised flayed margin"
    return mat


def _muscle():
    mat, n, l, bsdf, tex = _material(
        "CRYPTID | exposed longitudinal muscle", (0.070, 0.010, 0.017), 0.345, 0.028,
    )
    fibres = _fibres(n, l, tex, 48.0)
    color = _ramp(n, l, fibres.outputs["Fac"], [
        (0.15, (0.023, 0.003, 0.008)),
        (0.52, (0.072, 0.012, 0.019)),
        (0.85, (0.135, 0.035, 0.041)),
    ])
    bruise = _noise(n, l, tex.outputs["Object"], 28.0, 3.0)
    clot = _ramp(n, l, bruise.outputs["Fac"], [
        (0.30, (0.016, 0.003, 0.006)), (0.75, (0.11, 0.021, 0.029)),
    ])
    l.new(_mix(n, l, 0.28, color, clot), bsdf.inputs["Base Color"])
    coarse = _bump(n, l, bsdf, bruise.outputs["Fac"], 0.0018, 0.24)
    _bump(n, l, bsdf, fibres.outputs["Fac"], 0.0012, 0.30, coarse.outputs["Normal"])
    rough = _ramp(n, l, fibres.outputs["Fac"], [
        (0.1, (0.24, 0.24, 0.24)), (0.9, (0.41, 0.41, 0.41)),
    ])
    l.new(rough, bsdf.inputs["Roughness"])
    bsdf.inputs["Coat Weight"].default_value = 0.13
    bsdf.inputs["Coat Roughness"].default_value = 0.20
    return mat


def _fascia():
    mat, n, l, bsdf, tex = _material(
        "CRYPTID | dirty ivory fascia and tendon", (0.29, 0.225, 0.205), 0.42, 0.035,
    )
    fibres = _fibres(n, l, tex, 74.0)
    color = _ramp(n, l, fibres.outputs["Fac"], [
        (0.14, (0.13, 0.070, 0.065)),
        (0.55, (0.29, 0.225, 0.205)),
        (0.86, (0.44, 0.375, 0.325)),
    ])
    l.new(color, bsdf.inputs["Base Color"])
    _bump(n, l, bsdf, fibres.outputs["Fac"], 0.00085, 0.32)
    return mat


def _organic(name, color, roughness, low, high, scale=180.0,
             subsurface=0.02, bump_distance=0.0003):
    mat, n, l, bsdf, tex = _material(name, color, roughness, subsurface)
    texnoise = _noise(n, l, tex.outputs["Object"], scale, 2.0)
    l.new(_ramp(n, l, texnoise.outputs["Fac"], [(0.16, low), (0.84, high)]), bsdf.inputs["Base Color"])
    _bump(n, l, bsdf, texnoise.outputs["Fac"], bump_distance, 0.2)
    return mat


def create_materials():
    """Return the complete eleven-material horror palette, ready to assign."""
    mats = {"skin": _skin(), "muscle": _muscle(), "fascia": _fascia()}
    mats["blood"] = _organic(
        "CRYPTID | dark congealed blood", (0.062, 0.004, 0.009), 0.245,
        (0.027, 0.0015, 0.004), (0.12, 0.011, 0.017), 95.0, 0.01, 0.00018,
    )
    mats["bone"] = _organic(
        "CRYPTID | cool aged ivory bone", (0.31, 0.295, 0.27), 0.37,
        (0.18, 0.16, 0.145), (0.445, 0.42, 0.375), 110.0, 0.015, 0.00034,
    )
    mats["horn"] = _organic(
        "CRYPTID | weathered charcoal keratin", (0.065, 0.05, 0.048), 0.37,
        (0.023, 0.018, 0.021), (0.16, 0.135, 0.12), 125.0, 0.0, 0.00034,
    )
    mats["throat"] = _organic(
        "CRYPTID | lightless pharyngeal mucosa", (0.012, 0.001, 0.003), 0.28,
        (0.004, 0.0004, 0.001), (0.033, 0.004, 0.009), 230.0, 0.02, 0.0002,
    )
    mats["tongue"] = _organic(
        "CRYPTID | congested papillary tongue", (0.105, 0.016, 0.028), 0.285,
        (0.049, 0.006, 0.016), (0.16, 0.033, 0.052), 780.0, 0.045, 0.00085,
    )
    mats["scar"] = _organic(
        "CRYPTID | fibrotic healed scar rim", (0.29, 0.12, 0.12), 0.47,
        (0.175, 0.05, 0.061), (0.40, 0.245, 0.23), 230.0, 0.035, 0.0003,
    )
    mats["vein"] = _organic(
        "CRYPTID | deep burgundy vessel", (0.052, 0.012, 0.024), 0.41,
        (0.025, 0.005, 0.013), (0.09, 0.025, 0.039), 190.0, 0.015, 0.00012,
    )
    saliva, _, _, bsdf, _ = _material(
        "CRYPTID | viscous tinted saliva", (0.075, 0.025, 0.028), 0.115,
    )
    bsdf.inputs["IOR"].default_value = 1.34
    bsdf.inputs["Transmission Weight"].default_value = 0.65
    bsdf.inputs["Specular IOR Level"].default_value = 0.5
    mats["saliva"] = saliva
    return mats


def refine_materials_existing():
    """Replace this palette in an already built scene, keeping geometry intact.

    Each old material is remapped, including numbered copies, and retained as
    unused data rather than destructively removed. Returned dict contains the
    fresh materials. Re-running this function is supported.
    """
    old = [m for m in bpy.data.materials if m.name.startswith("CRYPTID | ")]
    fresh = create_materials()
    names = {
        "skin": "CRYPTID | pale dermis / wine-red distal circulation",
        "muscle": "CRYPTID | exposed longitudinal muscle",
        "fascia": "CRYPTID | dirty ivory fascia and tendon",
        "blood": "CRYPTID | dark congealed blood",
        "bone": "CRYPTID | cool aged ivory bone",
        "horn": "CRYPTID | weathered charcoal keratin",
        "throat": "CRYPTID | lightless pharyngeal mucosa",
        "tongue": "CRYPTID | congested papillary tongue",
        "scar": "CRYPTID | fibrotic healed scar rim",
        "vein": "CRYPTID | deep burgundy vessel",
        "saliva": "CRYPTID | viscous tinted saliva",
    }
    for material in old:
        base_name = material.name
        if len(base_name) > 4 and base_name[-4] == "." and base_name[-3:].isdigit():
            base_name = base_name[:-4]
        for key, expected in names.items():
            if base_name == expected:
                material.user_remap(fresh[key])
                break
    return fresh
