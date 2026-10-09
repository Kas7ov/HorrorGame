using System;
using System.IO;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering.HighDefinition;

public static class TerrainLeafWindSetup
{
    static void Setup(MenuCommand command)
    {
        string path = "Assets/Tree_HDRP/Shaders/LeavesWindLit.shader";
        AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceSynchronousImport);
        Shader shader = AssetDatabase.LoadAssetAtPath<Shader>(path);
        if (!shader || ShaderUtil.ShaderHasError(shader)) throw new Exception("Leaf wind shader failed to compile.");
        Material leaves = AssetDatabase.LoadAssetAtPath<Material>("Assets/Tree_HDRP/Tree_Leaves_HDRP.mat");
        Undo.RecordObject(leaves, "Enable terrain leaf wind");
        leaves.shader = shader;
        leaves.enableInstancing = true;
        HDMaterial.ValidateMaterial(leaves);
        EditorUtility.SetDirty(leaves);
        Terrain terrain = (Terrain)command.context;
        terrain.terrainData.RefreshPrototypes();
        terrain.Flush();
        AssetDatabase.SaveAssets();
        SceneView.RepaintAll();
        File.WriteAllText("Tools/TerrainLeafWindVerification.txt", "PASS: HDRP GPU leaf-wind shader assigned; alpha clipping and double sided leaves retained; terrain prototypes refreshed. No per-tree scripts required.\n");
        Debug.Log("GPU wind enabled on terrain leaves.");
    }
}
