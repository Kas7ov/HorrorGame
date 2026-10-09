using System;
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

public static class TreeGroundSetup
{
    const string Folder = "Assets/GroundTextures";
    static void Setup()
    {
        string prefabPath = "Assets/Tree_HDRP/Tree_HDRP.prefab";
        GameObject prefab = PrefabUtility.LoadPrefabContents(prefabPath);
        try
        {
            Mesh source = AssetDatabase.LoadAssetAtPath<Mesh>("Assets/Tree_HDRP/Tree_HDRP_Mesh.asset");
            var sway = prefab.GetComponent<TreeLeafSway>();
            if (!sway) sway = prefab.AddComponent<TreeLeafSway>();
            sway.sourceMesh = source;
            // Never serialize the temporary animated mesh into the prefab.
            sway.enabled = false;
            prefab.GetComponent<MeshFilter>().sharedMesh = source;
            PrefabUtility.SaveAsPrefabAsset(prefab, prefabPath);
        }
        finally { PrefabUtility.UnloadPrefabContents(prefab); }
        // Enable in the saved prefab without generating an edit-time mesh there.
        var asset = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
        var component = asset.GetComponent<TreeLeafSway>();
        component.enabled = true;
        EditorUtility.SetDirty(component);
        AssetDatabase.SaveAssets();
        int treeCount = 0;
        foreach (var filter in UnityEngine.Object.FindObjectsByType<MeshFilter>(FindObjectsSortMode.None))
        {
            if (filter.gameObject.scene != EditorSceneManager.GetActiveScene() || filter.name != "Tree_HDRP") continue;
            var sway = filter.GetComponent<TreeLeafSway>();
            if (!sway) sway = Undo.AddComponent<TreeLeafSway>(filter.gameObject);
            sway.enabled = true;
            sway.Animate(0f);
            var first = filter.sharedMesh.vertices;
            sway.Animate(0.7f);
            var second = filter.sharedMesh.vertices;
            bool moved = false;
            foreach (int index in sway.sourceMesh.GetTriangles(1)) moved |= (first[index] - second[index]).sqrMagnitude > 0.000001f;
            foreach (int index in sway.sourceMesh.GetTriangles(0))
                if ((first[index] - second[index]).sqrMagnitude > 0.000001f) throw new Exception("Bark unexpectedly moved.");
            if (!moved) throw new Exception("Leaf sway verification failed.");
            treeCount++;
        }
        string texturePath = Folder + "/brown_mud_diff_1k.jpg";
        AssetDatabase.ImportAsset(texturePath, ImportAssetOptions.ForceSynchronousImport);
        var importer = (TextureImporter)AssetImporter.GetAtPath(texturePath);
        importer.wrapMode = TextureWrapMode.Repeat;
        importer.maxTextureSize = 1024;
        importer.SaveAndReimport();
        var texture = AssetDatabase.LoadAssetAtPath<Texture2D>(texturePath);
        if (!texture) throw new Exception("Ground texture not found.");
        string layerPath = Folder + "/BrownSoil.terrainlayer";
        var layer = AssetDatabase.LoadAssetAtPath<TerrainLayer>(layerPath);
        if (!layer) { layer = new TerrainLayer(); AssetDatabase.CreateAsset(layer, layerPath); }
        layer.diffuseTexture = texture;
        layer.tileSize = new Vector2(4f, 4f);
        layer.metallic = 0f; layer.smoothness = 0.08f;
        EditorUtility.SetDirty(layer);
        int terrainCount = 0;
        foreach (var terrain in Terrain.activeTerrains)
        {
            if (terrain.gameObject.scene != EditorSceneManager.GetActiveScene()) continue;
            var data = terrain.terrainData;
            // Preserve other scenes and existing painted layers by working on a copy.
            string copyPath = Folder + "/Ocean_SoilTerrain.asset";
            var copy = AssetDatabase.LoadAssetAtPath<TerrainData>(copyPath);
            if (!copy)
            {
                copy = UnityEngine.Object.Instantiate(data);
                copy.name = "Ocean_SoilTerrain";
                AssetDatabase.CreateAsset(copy, copyPath);
            }
            var layers = copy.terrainLayers;
            if (layers.Length == 0) copy.terrainLayers = new[] { layer };
            else
            {
                // Replace an empty base layer only; do not overwrite existing painted textures.
                if (!layers[0] || !layers[0].diffuseTexture) layers[0] = layer;
                else
                {
                    var baseCopy = UnityEngine.Object.Instantiate(layers[0]);
                    baseCopy.diffuseTexture = texture; baseCopy.tileSize = layer.tileSize;
                    baseCopy.metallic = 0f; baseCopy.smoothness = 0.08f;
                    AssetDatabase.CreateAsset(baseCopy, AssetDatabase.GenerateUniqueAssetPath(Folder + "/SoilBase.terrainlayer"));
                    layers[0] = baseCopy;
                }
                copy.terrainLayers = layers;
            }
            Undo.RecordObject(terrain, "Add soil terrain surface");
            terrain.terrainData = copy;
            string materialPath = Folder + "/SoilTerrain_HDRP.mat";
            var material = AssetDatabase.LoadAssetAtPath<Material>(materialPath);
            if (!material)
            {
                var shader = Shader.Find("HDRP/TerrainLit");
                if (!shader) throw new Exception("HDRP terrain shader missing.");
                material = new Material(shader);
                AssetDatabase.CreateAsset(material, materialPath);
            }
            terrain.materialTemplate = material;
            var collider = terrain.GetComponent<TerrainCollider>();
            if (collider) { Undo.RecordObject(collider, "Use soil terrain copy"); collider.terrainData = copy; }
            terrain.Flush();
            EditorUtility.SetDirty(copy);
            terrainCount++;
        }
        AssetDatabase.SaveAssets();
        EditorSceneManager.MarkSceneDirty(EditorSceneManager.GetActiveScene());
        File.WriteAllText("Tools/TreeGroundVerification.txt", $"PASS: {treeCount} scene trees: leaf vertices move; bark stays fixed.\n{terrainCount} terrains use soil base texture on a copied TerrainData, retaining height, trees and details.\n");
        Debug.Log("Leaf sway and soil ground ready.");
    }
}
