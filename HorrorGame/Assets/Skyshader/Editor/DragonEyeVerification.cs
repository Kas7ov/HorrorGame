using System.IO;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.HighDefinition;

// Explicit one-shot test, never auto-started. Restores the box and unsubscribes.
public static class DragonEyeVerification
{
    static DragonEyeEvent eye;
    static DragonEyeTrigger trigger;
    static Vector3 originalPosition;
    static double started;
    static bool overlapped, restored;
    static bool hadOpeningProgress;

    public static void Run(DragonEyeEvent target)
    {
        if (!Application.isPlaying || eye) return;
        trigger = target.GetComponentInChildren<DragonEyeTrigger>();
        if (!trigger || !trigger.playerRoot) { Debug.LogError("Test needs a player-bound trigger."); return; }
        eye = target; eye.ResetEye();
        originalPosition = trigger.transform.position;
        // First separate the box, then introduce a real collider overlap on a physics step.
        trigger.transform.position = originalPosition + Vector3.up * 1000;
        Physics.SyncTransforms();
        started = EditorApplication.timeSinceStartup;
        overlapped = restored = hadOpeningProgress = false;
        EditorApplication.update += Tick;
        EditorApplication.playModeStateChanged += StopOnExit;
    }

    static void Tick()
    {
        if (!eye || !trigger || !Application.isPlaying) { Stop(); return; }
        double elapsed = EditorApplication.timeSinceStartup - started;
        if (elapsed > 0.25 && !overlapped)
        {
            trigger.transform.position = trigger.playerRoot.position;
            Physics.SyncTransforms(); overlapped = true;
        }
        if (elapsed > 0.8 && !restored)
        {
            trigger.transform.position = originalPosition;
            Physics.SyncTransforms(); restored = true;
        }
        if (eye.eyeOpenAmount > 0 && eye.eyeOpenAmount < 1) hadOpeningProgress = true;
        if (elapsed > eye.openingSeconds + 2)
        {
            var pass = eye.GetComponent<UnityEngine.Rendering.HighDefinition.CustomPassVolume>();
            var skyPass = (DragonEyeSkyPass)pass.customPasses[0];
            bool shaderOK = skyPass.eyeMaterial && !ShaderUtil.ShaderHasError(skyPass.eyeMaterial.shader);
            bool selfContainedShader = !File.Exists("Assets/Skyshader/DragonEyeHorizon.hlsl")
                && !System.Array.Exists(AssetDatabase.GetDependencies("Assets/Skyshader/DragonEyeSkyShader.shadergraph", true),
                    path => path.EndsWith("DragonEyeHorizon.hlsl"));
            var hdCamera = HDCamera.GetOrCreate(Camera.main);
            var fog = hdCamera.volumeStack.GetComponent<Fog>();
            bool fogOK = fog.enabled.value && fog.enableVolumetricFog.value
                && hdCamera.frameSettings.IsEnabled(FrameSettingsField.Volumetrics)
                && hdCamera.frameSettings.IsEnabled(FrameSettingsField.AtmosphericScattering);
            var p = eye.redSmoke.parameters;
            bool smokeOK = eye.redSmoke.enabled && p.volumeMask && p.meanFreePath <= 10
                && (eye.redSmoke.transform.position - trigger.playerRoot.position).magnitude < 10;
            bool sunOK = eye.ActiveSun && Mathf.Approximately(eye.ActiveSun.intensity,
                eye.OriginalSunIntensity * eye.activatedSunBrightness);
            bool diskOK = !eye.hideSunDiskWhenActive || eye.SunDiskIsHidden;
            bool lightStillOn = eye.ActiveSun && eye.ActiveSun.isActiveAndEnabled && eye.ActiveSun.intensity > 0;
            bool shakeOK = eye.OpeningShakeObserved && !eye.CameraShakeIsApplied;
            float sunBrightness = eye.CurrentSunBrightness;
            var sun = eye.ActiveSun;
            float originalSun = eye.OriginalSunIntensity;
            bool passOK = hadOpeningProgress && eye.eyeOpenAmount >= 0.999f
                && eye.redSmoke && smokeOK && fogOK && eye.redVisionVolume.weight > 0 && shaderOK && selfContainedShader && sunOK && shakeOK && diskOK && lightStillOn;
            string result = (passOK ? "PASS" : "FAIL") +
                ": real box collider overlap " + (hadOpeningProgress ? "started animated opening" : "did not start opening") +
                "; eye=" + eye.eyeOpenAmount + "; smoke enabled=" + eye.redSmoke.enabled +
                "; red vision weight=" + eye.redVisionVolume.weight + "; shader errors=" + !shaderOK +
                "; self-contained shader=" + selfContainedShader + "; HDRP fog rendering=" + fogOK + "; smoke attenuation metres=" + p.meanFreePath +
                "; smoke region=" + p.size + "; masked smoke near player=" + smokeOK +
                "; sun brightness=" + sunBrightness + "; sun disk hidden=" + eye.SunDiskIsHidden +
                "; sun illumination still on=" + lightStillOn + "; opening shake rendered and settled=" + shakeOK;
            eye.ResetEye();
            bool resetOK = sun && Mathf.Approximately(sun.intensity, originalSun)
                && eye.SunVisualsRestored && !eye.CameraShakeIsApplied && !eye.redSmoke.enabled && eye.redVisionVolume.weight == 0;
            if (!resetOK) result = result.Replace("PASS:", "FAIL:");
            result += "; reset restored sun/camera/atmosphere=" + resetOK +
                ". Trigger restored to original location. Original sky profile untouched.\n";
            File.WriteAllText("Tools/DragonEyeVerification.txt", result);
            Debug.Log(result);
            Stop();
        }
    }
    static void StopOnExit(PlayModeStateChange state)
    {
        if (state == PlayModeStateChange.ExitingPlayMode) Stop();
    }
    static void Stop()
    {
        if (trigger && !restored) trigger.transform.position = originalPosition;
        EditorApplication.update -= Tick;
        EditorApplication.playModeStateChanged -= StopOnExit;
        eye = null; trigger = null;
    }
}
