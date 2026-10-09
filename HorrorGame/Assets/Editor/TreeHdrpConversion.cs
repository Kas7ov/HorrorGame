using System;
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering.HighDefinition;

public static class TreeHdrpConversion
{
    const string Folder = "Assets/Tree_HDRP";

    [MenuItem("Tools/Trees/Convert Selected Tree to HDRP")]
    public static void ConvertSelected()
    {
        GameObject source = Selection.activeGameObject;
        if (source == null || source.GetComponent<Tree>() == null)
            throw new InvalidOperationException("Select the original Tree Creator tree in the scene first.");
        Mesh sourceMesh = source.GetComponent<MeshFilter>()?.sharedMesh;
        if (sourceMesh == null || sourceMesh.subMeshCount != 2)
            throw new InvalidOperationException("Expected the original tree's bark and leaf submeshes.");
        Shader shader = Shader.Find("HDRP/Lit");
        Texture2D leafImage = AssetDatabase.LoadAssetAtPath<Texture2D>("Assets/Green-Leaves-Transparent-PNG.png");
        if (shader == null || leafImage == null) throw new InvalidOperationException("HDRP/Lit or the leaf image is missing.");
        if (!AssetDatabase.IsValidFolder(Folder)) AssetDatabase.CreateFolder("Assets", "Tree_HDRP");

        Mesh mesh = UnityEngine.Object.Instantiate(sourceMesh);
        mesh.name = "Tree_HDRP_Mesh";
        Vector2[] uv = mesh.uv;
        int[] triangles = mesh.GetTriangles(1);
        // Tree Creator packed these cards into a blank atlas because materialLeaf was null.
        // Restore each card's UV rectangle and sample the large sprig in the supplied image.
        for (int i = 0; i < triangles.Length; i += 6)
        {
            if (i + 5 >= triangles.Length) throw new InvalidOperationException("Leaf geometry is not a set of quads.");
            int[] corners = new int[4];
            int count = 0;
            for (int j = 0; j < 6; j++)
            {
                int index = triangles[i + j];
                bool seen = false;
                for (int k = 0; k < count; k++) seen |= corners[k] == index;
                if (!seen)
                {
                    if (count == 4) throw new InvalidOperationException("Unexpected leaf topology.");
                    corners[count++] = index;
                }
            }
            if (count != 4) throw new InvalidOperationException("Expected four leaf-card vertices.");
            Vector2 min = uv[corners[0]], max = min;
            foreach (int corner in corners) { min = Vector2.Min(min, uv[corner]); max = Vector2.Max(max, uv[corner]); }
            for (int j = 0; j < 4; j++)
            {
                int corner = corners[j];
                Vector2 cardUV = max.x - min.x > 0.00001f && max.y - min.y > 0.00001f
                    ? new Vector2(Mathf.InverseLerp(min.x, max.x, uv[corner].x), Mathf.InverseLerp(min.y, max.y, uv[corner].y))
                    : new[] { Vector2.zero, Vector2.right, Vector2.one, Vector2.up }[j];
                uv[corner] = new Vector2(cardUV.x * 0.61f, cardUV.y);
            }
        }
        mesh.uv = uv;
        mesh.RecalculateTangents();
        string meshPath = AssetDatabase.GenerateUniqueAssetPath(Folder + "/Tree_HDRP_Mesh.asset");
        AssetDatabase.CreateAsset(mesh, meshPath);

        Material bark = new Material(shader) { name = "Tree_Bark_HDRP" };
        bark.SetColor("_BaseColor", new Color(0.24f, 0.13f, 0.065f, 1f));
        bark.SetFloat("_Metallic", 0f);
        bark.SetFloat("_Smoothness", 0.2f);
        bark.SetFloat("_SurfaceType", 0f);
        HDMaterial.ValidateMaterial(bark);
        AssetDatabase.CreateAsset(bark, AssetDatabase.GenerateUniqueAssetPath(Folder + "/Tree_Bark_HDRP.mat"));

        Material leaves = new Material(shader) { name = "Tree_Leaves_HDRP" };
        leaves.SetTexture("_BaseColorMap", leafImage);
        leaves.SetColor("_BaseColor", Color.white);
        leaves.SetFloat("_SurfaceType", 0f);
        leaves.SetFloat("_AlphaCutoffEnable", 1f);
        leaves.SetFloat("_AlphaCutoff", 0.35f);
        leaves.SetFloat("_AlphaCutoffShadow", 0.35f);
        leaves.SetFloat("_DoubleSidedEnable", 1f);
        leaves.SetFloat("_DoubleSidedNormalMode", 1f);
        leaves.SetFloat("_Metallic", 0f);
        leaves.SetFloat("_Smoothness", 0.25f);
        HDMaterial.ValidateMaterial(leaves);
        AssetDatabase.CreateAsset(leaves, AssetDatabase.GenerateUniqueAssetPath(Folder + "/Tree_Leaves_HDRP.mat"));

        GameObject tree = new GameObject("Tree_HDRP");
        Undo.RegisterCreatedObjectUndo(tree, "Convert tree to HDRP");
        tree.transform.SetParent(source.transform.parent, false);
        tree.transform.localPosition = source.transform.localPosition;
        tree.transform.localRotation = source.transform.localRotation;
        tree.transform.localScale = source.transform.localScale;
        tree.AddComponent<MeshFilter>().sharedMesh = mesh;
        MeshRenderer renderer = tree.AddComponent<MeshRenderer>();
        renderer.sharedMaterials = new[] { bark, leaves };
        LODGroup lod = tree.AddComponent<LODGroup>();
        lod.SetLODs(new[] { new LOD(0.01f, new Renderer[] { renderer }) });
        lod.RecalculateBounds();
        string prefabPath = AssetDatabase.GenerateUniqueAssetPath(Folder + "/Tree_HDRP.prefab");
        PrefabUtility.SaveAsPrefabAssetAndConnect(tree, prefabPath, InteractionMode.AutomatedAction);
        // Retain the authoring object and its TreeData; the HDRP copy displays in its place.
        Undo.RecordObject(source, "Keep original tree as authoring source");
        source.SetActive(false);
        EditorSceneManager.MarkSceneDirty(tree.scene);
        AssetDatabase.SaveAssets();
        Selection.activeGameObject = tree;
        if (renderer.sharedMaterials.Length != mesh.subMeshCount || !leaves.IsKeywordEnabled("_ALPHATEST_ON"))
            throw new InvalidOperationException("Converted tree material validation failed.");
        File.WriteAllText(Path.Combine(Application.dataPath, "../Tools/TreeHdrpConversion.txt"),
            $"PASS: {prefabPath}\nMesh: {mesh.vertexCount} vertices, {mesh.subMeshCount} submeshes; original geometry preserved.\n"
            + "HDRP/Lit bark and double-sided alpha-clipped leaves.\nOriginal Tree Creator object retained, inactive.\n");
        Debug.Log("Tree converted to HDRP: " + prefabPath);
    }
}
