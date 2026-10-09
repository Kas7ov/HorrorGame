using System;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.HighDefinition;

[Serializable]
public sealed class DragonEyeSkyPass : CustomPass
{
    public DragonEyeEvent controller;
    public Material eyeMaterial;

    protected override void Execute(CustomPassContext ctx)
    {
        if (!controller || !eyeMaterial || !controller.eyeTexture || controller.eyeOpenAmount <= 0)
            return;
        if (ctx.hdCamera.camera.cameraType != CameraType.Game &&
            ctx.hdCamera.camera.cameraType != CameraType.SceneView) return;
        var rotation = Quaternion.Euler(-controller.elevation, controller.azimuth, 0);
        ctx.cmd.SetGlobalTexture("_DragonEyeTexture", controller.eyeTexture);
        ctx.cmd.SetGlobalVector("_DragonEyeForward", rotation * Vector3.forward);
        ctx.cmd.SetGlobalVector("_DragonEyeRight", rotation * Vector3.right);
        ctx.cmd.SetGlobalVector("_DragonEyeUp", rotation * Vector3.up);
        float width = Mathf.Tan(controller.angularWidth * Mathf.Deg2Rad * 0.5f);
        ctx.cmd.SetGlobalVector("_DragonEyeShape", new Vector4(width, width * controller.heightRatio,
            controller.eyeOpenAmount, controller.opacity));
        ctx.cmd.SetGlobalVector("_DragonEyeLook", new Vector4(controller.edgeSoftness,
            controller.radiance, Time.realtimeSinceStartup, 0.08f));
        ctx.cmd.SetGlobalColor("_DragonEyeTint", controller.eyeTint);
        int index = eyeMaterial.FindPass("DrawProcedural");
        CoreUtils.DrawFullScreen(ctx.cmd, eyeMaterial, shaderPassId: index >= 0 ? index : 0);
    }
}
