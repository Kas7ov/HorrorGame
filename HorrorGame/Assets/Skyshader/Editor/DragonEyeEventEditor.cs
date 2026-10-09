using UnityEditor;
using UnityEngine;

[CustomEditor(typeof(DragonEyeEvent))]
public sealed class DragonEyeEventEditor : Editor
{
    public override void OnInspectorGUI()
    {
        DrawDefaultInspector();
        var eye = (DragonEyeEvent)target;
        EditorGUILayout.HelpBox("Keeps your original HDRP sky. The eye renders behind fog and clouds. Move Dragon Eye Trigger to choose where the event starts.", MessageType.Info);
        if (Application.isPlaying && GUILayout.Button("Open eye (animated)")) eye.OpenEye();
        if (Application.isPlaying && GUILayout.Button("Test box-trigger crossing"))
            DragonEyeVerification.Run(eye);
        if (GUILayout.Button("Preview fully open"))
        {
            Undo.RecordObject(eye, "Preview dragon eye");
            eye.PreviewOpenEye();
            EditorUtility.SetDirty(eye);
            SceneView.RepaintAll();
        }
        if (GUILayout.Button("Reset / close eye"))
        {
            Undo.RecordObject(eye, "Close dragon eye");
            eye.ResetEye();
            EditorUtility.SetDirty(eye);
            SceneView.RepaintAll();
        }
        if (GUILayout.Button("Look toward eye in Scene view"))
        {
            var camera = Camera.main;
            var view = SceneView.lastActiveSceneView;
            if (view && camera)
            {
                var rotation = Quaternion.Euler(-eye.elevation, eye.azimuth, 0);
                Vector3 cameraPoint = camera.transform.position + Vector3.up * 16;
                view.LookAtDirect(cameraPoint + rotation * Vector3.forward, rotation, 1);
                view.Repaint();
            }
        }
    }
}
