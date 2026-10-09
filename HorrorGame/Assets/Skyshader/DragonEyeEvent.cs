using UnityEngine;
using UnityEngine.Events;
using UnityEngine.Rendering;
using UnityEngine.Rendering.HighDefinition;
using System.Collections.Generic;

[ExecuteAlways]
public sealed class DragonEyeEvent : MonoBehaviour
{
    [Header("Dragon eye — fixed direction, not attached to your screen")]
    public Texture2D eyeTexture;
    [Range(0, 1)] public float eyeOpenAmount;
    [Range(-180, 180)] public float azimuth;
    [Range(1, 80)] public float elevation = 18;
    [Range(10, 120)] public float angularWidth = 66;
    [Range(0.2f, 1)] public float heightRatio = 0.62f;
    [Range(0, 1)] public float opacity = 0.85f;
    [Range(0.05f, 0.7f)] public float edgeSoftness = 0.25f;
    [Min(1)] public float radiance = 3000;
    public Color eyeTint = new Color(1, 0.86f, 0.84f, 1);

    [Header("Opening and atmosphere")]
    [Min(0.1f)] public float openingSeconds = 3.5f;
    [Range(0, 1)] public float atmosphereStrength = 0.6f;
    [Min(5)] public float smokeMeanFreePath = 42;
    [Header("Focused red smoke")]
    [Tooltip("Higher values make the smoke denser without strengthening the screen tint.")]
    [Range(1, 12)] public float smokeDensityMultiplier = 6;
    public Color smokeTint = new Color(1, 0.12f, 0.08f, 1);
    public Vector3 smokeSize = new Vector3(72, 14, 72);
    [Tooltip("Keeps the localized smoke around the trigger's player, rather than across the entire terrain.")]
    public bool smokeFollowsPlayer = true;
    [Header("Sun and opening tremor (Play Mode)")]
    [Tooltip("Optional. Otherwise uses the scene sun, or its brightest directional light.")]
    public Light sunLight;
    [Range(0, 1)] public float activatedSunBrightness = 0.2f;
    [Tooltip("Fades only HDRP's visible sun disk and halo. The directional light and sky scattering remain enabled.")]
    public bool hideSunDiskWhenActive = true;
    [Tooltip("Optional. Otherwise uses the main game camera.")]
    public Camera shakeCamera;
    [Range(0, 2)] public float openingShakeDegrees = 0.8f;
    [Range(0, 0.2f)] public float openingShakeMetres = 0.035f;
    [Range(1, 30)] public float openingShakeFrequency = 14;
    public Volume redVisionVolume;
    public LocalVolumetricFog redSmoke;
    public UnityEvent onEyeOpened = new UnityEvent();

    bool opening;
    bool firedOpened;
    Transform smokePlayer;
    Light runtimeSun;
    float originalSunIntensity;
    HDAdditionalLightData runtimeSunData;
    Color originalSunSurfaceTint;
    float originalSunFlareMultiplier;
    bool capturedSun;
    Camera runtimeCamera;
    Transform shakenTransform;
    Vector3 unshakenPosition;
    Quaternion unshakenRotation;
    public bool OpeningShakeObserved { get; private set; }
    public float CurrentSunBrightness { get; private set; } = 1;
    public bool CameraShakeIsApplied => shakenTransform;
    public Light ActiveSun => runtimeSun;
    public float OriginalSunIntensity => originalSunIntensity;
    public bool SunDiskIsHidden => runtimeSunData && runtimeSunData.surfaceTint.maxColorComponent <= 0.0001f
        && runtimeSunData.flareMultiplier <= 0.0001f;
    public bool SunVisualsRestored => !runtimeSunData || (runtimeSunData.surfaceTint == originalSunSurfaceTint
        && Mathf.Approximately(runtimeSunData.flareMultiplier, originalSunFlareMultiplier));

    void OnEnable()
    {
        var trigger = GetComponentInChildren<DragonEyeTrigger>();
        smokePlayer = trigger ? trigger.playerRoot : null;
        RenderPipelineManager.beginContextRendering += BeginShakeRendering;
        RenderPipelineManager.endContextRendering += EndShakeRendering;
        ApplyAtmosphere();
    }
    void Update()
    {
        // Normally restored at the end of rendering; also recover after an interrupted render.
        RestoreCameraPose();
        if (Application.IsPlaying(gameObject) && opening)
        {
            eyeOpenAmount = Mathf.MoveTowards(eyeOpenAmount, 1, Time.deltaTime / Mathf.Max(0.1f, openingSeconds));
            if (eyeOpenAmount >= 1)
            {
                opening = false;
                if (!firedOpened) { firedOpened = true; onEyeOpened.Invoke(); }
            }
        }
        ApplyAtmosphere();
        ApplySunDimming();
    }

    public void OpenEye() { opening = true; OpeningShakeObserved = false; }
    public void ResetEye()
    {
        opening = false; firedOpened = false; eyeOpenAmount = 0;
        OpeningShakeObserved = false;
        RestoreCameraPose(); RestoreSun(); ApplyAtmosphere();
    }
    public void PreviewOpenEye()
    {
        opening = false; eyeOpenAmount = 1;
        RestoreCameraPose(); ApplyAtmosphere(); ApplySunDimming();
    }

    void ApplySunDimming()
    {
        // Never serialize a dimmed sun into the user's edit-time scene.
        if (!Application.IsPlaying(gameObject)) return;
        if (eyeOpenAmount <= 0) { RestoreSun(); return; }
        if (!capturedSun)
        {
            runtimeSun = sunLight ? sunLight : RenderSettings.sun;
            if (!runtimeSun)
                foreach (var light in Object.FindObjectsByType<Light>(FindObjectsSortMode.None))
                    if (light.gameObject.scene == gameObject.scene && light.isActiveAndEnabled
                        && light.type == LightType.Directional
                        && (!runtimeSun || light.intensity > runtimeSun.intensity)) runtimeSun = light;
            if (!runtimeSun) return;
            originalSunIntensity = runtimeSun.intensity;
            runtimeSunData = runtimeSun.GetComponent<HDAdditionalLightData>();
            if (runtimeSunData)
            {
                originalSunSurfaceTint = runtimeSunData.surfaceTint;
                originalSunFlareMultiplier = runtimeSunData.flareMultiplier;
            }
            capturedSun = true;
        }
        float activation = Mathf.SmoothStep(0, 1, Mathf.Clamp01(eyeOpenAmount));
        CurrentSunBrightness = Mathf.Lerp(1, activatedSunBrightness, activation);
        if (runtimeSun) runtimeSun.intensity = originalSunIntensity * CurrentSunBrightness;
        if (runtimeSunData)
        {
            // These affect celestial-body appearance only, not direct/volumetric lighting,
            // sky scattering, light direction or the shadow's angular diameter.
            float diskVisibility = hideSunDiskWhenActive ? 1 - activation : 1;
            runtimeSunData.surfaceTint = originalSunSurfaceTint * diskVisibility;
            runtimeSunData.flareMultiplier = originalSunFlareMultiplier * diskVisibility;
        }
    }

    void RestoreSun()
    {
        if (capturedSun && runtimeSun) runtimeSun.intensity = originalSunIntensity;
        if (capturedSun && runtimeSunData)
        {
            runtimeSunData.surfaceTint = originalSunSurfaceTint;
            runtimeSunData.flareMultiplier = originalSunFlareMultiplier;
        }
        capturedSun = false;
        CurrentSunBrightness = 1;
    }

    void BeginShakeRendering(ScriptableRenderContext context, List<Camera> cameras)
    {
        RestoreCameraPose();
        if (!Application.IsPlaying(gameObject) || !opening || eyeOpenAmount <= 0 || eyeOpenAmount >= 1) return;
        if (!runtimeCamera) runtimeCamera = shakeCamera ? shakeCamera : Camera.main;
        if (!runtimeCamera || runtimeCamera.cameraType != CameraType.Game || !cameras.Contains(runtimeCamera)) return;
        float envelope = Mathf.Sin(Mathf.PI * Mathf.Clamp01(eyeOpenAmount));
        float time = Time.time * openingShakeFrequency;
        var noise = new Vector3(Mathf.PerlinNoise(time, 11.3f),
            Mathf.PerlinNoise(time, 37.7f), Mathf.PerlinNoise(time, 71.1f)) * 2 - Vector3.one;
        shakenTransform = runtimeCamera.transform;
        unshakenPosition = shakenTransform.localPosition;
        unshakenRotation = shakenTransform.localRotation;
        // Apply only for rendering, after mouse look and before HDRP caches/culls the camera.
        shakenTransform.localPosition = unshakenPosition + unshakenRotation * (noise * (openingShakeMetres * envelope));
        shakenTransform.localRotation = unshakenRotation * Quaternion.Euler(noise * (openingShakeDegrees * envelope));
        if (openingShakeMetres > 0 || openingShakeDegrees > 0) OpeningShakeObserved = true;
    }

    void EndShakeRendering(ScriptableRenderContext context, List<Camera> cameras) { RestoreCameraPose(); }

    void RestoreCameraPose()
    {
        if (!shakenTransform) return;
        shakenTransform.localPosition = unshakenPosition;
        shakenTransform.localRotation = unshakenRotation;
        shakenTransform = null;
    }

    void ApplyAtmosphere()
    {
        float openingAmount = Mathf.SmoothStep(0, 1, Mathf.Clamp01(eyeOpenAmount));
        float amount = openingAmount * atmosphereStrength;
        if (redVisionVolume) redVisionVolume.weight = amount;
        if (redSmoke)
        {
            redSmoke.enabled = amount > 0.001f;
            if (smokeFollowsPlayer && smokePlayer)
                redSmoke.transform.position = smokePlayer.position + Vector3.up * 3;
            var p = redSmoke.parameters;
            p.meanFreePath = smokeMeanFreePath / Mathf.Max(0.001f, openingAmount * smokeDensityMultiplier);
            p.albedo = smokeTint;
            p.size = new Vector3(Mathf.Max(1, smokeSize.x), Mathf.Max(1, smokeSize.y), Mathf.Max(1, smokeSize.z));
            p.textureTiling = new Vector3(6, 2, 6);
            p.textureScrollingSpeed = new Vector3(0.055f, 0.018f, 0.035f);
            p.positiveFade = new Vector3(0.25f, 0.45f, 0.25f);
            p.negativeFade = new Vector3(0.25f, 0.2f, 0.25f);
            redSmoke.parameters = p;
        }
    }

    void OnDisable()
    {
        RenderPipelineManager.beginContextRendering -= BeginShakeRendering;
        RenderPipelineManager.endContextRendering -= EndShakeRendering;
        RestoreCameraPose(); RestoreSun();
        if (redVisionVolume) redVisionVolume.weight = 0;
        if (redSmoke) redSmoke.enabled = false;
    }
}
