using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.HighDefinition;

public static class DragonEyeSetup
{
    const string Folder = "Assets/Skyshader/";

    static void Setup(MenuCommand command)
    {
        if (Application.isPlaying) throw new System.InvalidOperationException("Stop Play Mode before installing.");
        var terrain = (Terrain)command.context;
        foreach (var existing in Object.FindObjectsByType<DragonEyeEvent>(FindObjectsSortMode.None))
            if (existing.gameObject.scene == terrain.gameObject.scene)
            {
                Selection.activeGameObject = existing.gameObject;
                return;
            }
        AssetDatabase.ImportAsset(Folder + "DragonEyeSkyShader.shadergraph", ImportAssetOptions.ForceSynchronousImport);
        var shader = AssetDatabase.LoadAssetAtPath<Shader>(Folder + "DragonEyeSkyShader.shadergraph");
        if (!shader || ShaderUtil.ShaderHasError(shader))
        {
            if (shader) foreach (var error in ShaderUtil.GetShaderMessages(shader)) Debug.LogError(error.message);
            throw new System.InvalidOperationException("Dragon eye graph has shader errors; scene was not changed.");
        }
        var material = AssetDatabase.LoadAssetAtPath<Material>(Folder + "DragonEyeSky.mat");
        if (!material)
        {
            material = new Material(shader);
            AssetDatabase.CreateAsset(material, Folder + "DragonEyeSky.mat");
        }
        else { material.shader = shader; EditorUtility.SetDirty(material); }
        var texture = AssetDatabase.LoadAssetAtPath<Texture2D>(Folder + "EyeOfADragon.jpg");

        var profile = AssetDatabase.LoadAssetAtPath<VolumeProfile>(Folder + "DragonRedVision.asset");
        if (!profile)
        {
            profile = ScriptableObject.CreateInstance<VolumeProfile>();
            AssetDatabase.CreateAsset(profile, Folder + "DragonRedVision.asset");
            var color = profile.Add<ColorAdjustments>(false);
            color.colorFilter.Override(new Color(1, 0.83f, 0.8f, 1));
            AssetDatabase.AddObjectToAsset(color, profile);
            EditorUtility.SetDirty(profile);
        }
        var density = AssetDatabase.LoadAssetAtPath<Texture3D>(Folder + "DriftingSmokeDensity.asset");
        if (!density)
        {
            const int n = 32;
            density = new Texture3D(n, n, n, TextureFormat.RGBA32, false) { name = "Drifting crimson smoke", wrapMode = TextureWrapMode.Repeat, filterMode = FilterMode.Trilinear };
            var colors = new Color[n * n * n];
            for (int z = 0; z < n; z++) for (int y = 0; y < n; y++) for (int x = 0; x < n; x++)
            {
                // Periodic trigonometric density, seamless in all three axes.
                float a = x * Mathf.PI * 2 / n, b = y * Mathf.PI * 2 / n, c = z * Mathf.PI * 2 / n;
                float noise = 0.5f + 0.18f * Mathf.Sin(a + 2 * Mathf.Sin(c))
                    + 0.16f * Mathf.Cos(b + Mathf.Sin(a)) + 0.12f * Mathf.Sin(c * 2 + b);
                float d = Mathf.SmoothStep(0, 1, Mathf.InverseLerp(0.38f, 0.85f, noise));
                colors[x + n * (y + n * z)] = new Color(d, d, d, d);
            }
            density.SetPixels(colors); density.Apply();
            AssetDatabase.CreateAsset(density, Folder + "DriftingSmokeDensity.asset");
        }

        var player = Object.FindFirstObjectByType<PlayerMovement>();
        var camera = Camera.main;
        var root = new GameObject("Dragon Eye Horizon");
        Undo.RegisterCreatedObjectUndo(root, "Install dragon eye event");
        var eye = root.AddComponent<DragonEyeEvent>();
        eye.eyeTexture = texture;
        Vector3 direction = camera ? camera.transform.forward : Vector3.forward;
        eye.azimuth = Mathf.Atan2(direction.x, direction.z) * Mathf.Rad2Deg;
        var passVolume = root.AddComponent<CustomPassVolume>();
        passVolume.isGlobal = true;
        passVolume.injectionPoint = CustomPassInjectionPoint.AfterOpaqueAndSky;
        passVolume.customPasses.Add(new DragonEyeSkyPass {
            name = "Dragon eye behind HDRP clouds", controller = eye, eyeMaterial = material,
            targetColorBuffer = CustomPass.TargetBuffer.Camera,
            targetDepthBuffer = CustomPass.TargetBuffer.Camera
        });

        var visionObject = new GameObject("Dragon Red Vision");
        visionObject.transform.SetParent(root.transform);
        eye.redVisionVolume = visionObject.AddComponent<Volume>();
        eye.redVisionVolume.isGlobal = true;
        eye.redVisionVolume.priority = 100;
        eye.redVisionVolume.sharedProfile = profile;
        eye.redVisionVolume.weight = 0;
        if (camera && camera.TryGetComponent<HDAdditionalCameraData>(out var hdCamera))
            for (int i = 0; i < 32; i++) if ((hdCamera.volumeLayerMask.value & (1 << i)) != 0) { visionObject.layer = i; break; }

        var smokeObject = new GameObject("Dragon Drifting Red Smoke");
        smokeObject.transform.SetParent(root.transform);
        smokeObject.transform.position = terrain.transform.TransformPoint(terrain.terrainData.size * 0.5f);
        smokeObject.transform.position = new Vector3(smokeObject.transform.position.x,
            player ? player.transform.position.y + 3 : terrain.transform.position.y + 8, smokeObject.transform.position.z);
        eye.redSmoke = smokeObject.AddComponent<LocalVolumetricFog>();
        eye.redSmoke.parameters = new LocalVolumetricFogArtistParameters(new Color(0.65f, 0.016f, 0.025f), 42, 0) {
            size = new Vector3(terrain.terrainData.size.x, 24, terrain.terrainData.size.z),
            volumeMask = density, textureTiling = new Vector3(6, 2, 6),
            textureScrollingSpeed = new Vector3(0.025f, 0.008f, 0.013f),
            positiveFade = new Vector3(0.15f, 0.4f, 0.15f),
            negativeFade = new Vector3(0.15f, 0.15f, 0.15f)
        };
        eye.redSmoke.enabled = false;

        var triggerObject = new GameObject("Dragon Eye Trigger");
        triggerObject.transform.SetParent(root.transform);
        triggerObject.transform.position = player ? player.transform.position + Vector3.ProjectOnPlane(direction, Vector3.up).normalized * 12 : Vector3.zero;
        var trigger = triggerObject.AddComponent<DragonEyeTrigger>();
        trigger.dragonEye = eye;
        trigger.playerRoot = player ? player.transform : null;
        var box = triggerObject.GetComponent<BoxCollider>();
        box.isTrigger = true; box.size = new Vector3(10, 12, 5);
        var body = triggerObject.GetComponent<Rigidbody>();
        body.isKinematic = true; body.useGravity = false;
        eye.ResetEye();
        // Prefab is reusable; reassign its playerRoot if used in another scene.
        PrefabUtility.SaveAsPrefabAsset(root, Folder + "DragonEyeHorizon.prefab");
        AssetDatabase.SaveAssets();
        EditorSceneManager.MarkSceneDirty(root.scene);
        Selection.activeGameObject = root;
        SceneView.RepaintAll();
        File.WriteAllText("Tools/DragonEyeVerification.txt", "Installed: shader graph compiled; original sky profile untouched; pass runs AfterOpaqueAndSky before fog/clouds; box trigger assigned to player; red vision and 32-cubed scrolling smoke included. Runtime/visual test pending.\n");
        Debug.Log("Dragon eye installed. Move Dragon Eye Trigger to choose the event location. Original HDRP sky retained.");
    }
}
