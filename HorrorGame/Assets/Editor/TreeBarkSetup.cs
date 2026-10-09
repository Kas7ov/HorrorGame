using System;
using System.IO;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering.HighDefinition;

public static class TreeBarkSetup
{
    const string Folder = "Assets/Tree_HDRP/BarkTextures/";
    [MenuItem("Tools/Trees/Apply Realistic Bark")]
    static void Setup()
    {
        Texture2D diffuse = Import("diff", false);
        Texture2D normal = Import("nor_gl", true);
        Texture2D ao = ReadImage("ao");
        Texture2D rough = ReadImage("rough");
        Texture2D packed = null;
        try
        {
            if (ao.width != rough.width || ao.height != rough.height) throw new Exception("Bark mask sizes differ.");
            Color32[] occlusion = ao.GetPixels32(), roughness = rough.GetPixels32();
            for (int i = 0; i < occlusion.Length; i++)
                occlusion[i] = new Color32(0, occlusion[i].r, 255, (byte)(255 - roughness[i].r));
            packed = new Texture2D(ao.width, ao.height, TextureFormat.RGBA32, false, true);
            packed.SetPixels32(occlusion);
            packed.Apply();
            File.WriteAllBytes(Folder + "Bark_HDRP_Mask.png", packed.EncodeToPNG());
        }
        finally
        {
            UnityEngine.Object.DestroyImmediate(ao);
            UnityEngine.Object.DestroyImmediate(rough);
            if (packed) UnityEngine.Object.DestroyImmediate(packed);
        }
        string maskPath = Folder + "Bark_HDRP_Mask.png";
        AssetDatabase.ImportAsset(maskPath, ImportAssetOptions.ForceSynchronousImport);
        var maskImporter = (TextureImporter)AssetImporter.GetAtPath(maskPath);
        maskImporter.sRGBTexture = false;
        maskImporter.wrapMode = TextureWrapMode.Repeat;
        maskImporter.maxTextureSize = 2048;
        maskImporter.SaveAndReimport();
        string path = "Assets/Tree_HDRP/Tree_Bark_HDRP.mat";
        if (!AssetDatabase.LoadAssetAtPath<Material>(Folder + "Original_Plain_Bark.mat"))
            AssetDatabase.CopyAsset(path, Folder + "Original_Plain_Bark.mat");
        Material material = AssetDatabase.LoadAssetAtPath<Material>(path);
        Undo.RecordObject(material, "Apply realistic bark");
        material.SetTexture("_BaseColorMap", diffuse);
        material.SetColor("_BaseColor", new Color(0.8f, 0.8f, 0.78f, 1f));
        material.SetTexture("_NormalMap", normal);
        material.SetFloat("_NormalScale", 0.8f);
        material.SetTexture("_MaskMap", AssetDatabase.LoadAssetAtPath<Texture2D>(maskPath));
        material.SetFloat("_Metallic", 0f);
        material.SetFloat("_SmoothnessRemapMin", 0f);
        material.SetFloat("_SmoothnessRemapMax", 0.5f);
        material.SetFloat("_AORemapMin", 0.3f);
        material.SetFloat("_AORemapMax", 1f);
        // Legacy Tree Creator's UVs target its blank atlas; projection avoids stretching.
        material.SetFloat("_UVBase", 5f);
        material.SetFloat("_ObjectSpaceUVMapping", 1f);
        material.SetFloat("_TexWorldScale", 0.7f);
        HDMaterial.ValidateMaterial(material);
        EditorUtility.SetDirty(material);
        AssetDatabase.SaveAssets();
        if (!material.IsKeywordEnabled("_NORMALMAP") || !material.IsKeywordEnabled("_MASKMAP")
            || !material.IsKeywordEnabled("_MAPPING_TRIPLANAR")) throw new Exception("HDRP bark keywords failed validation.");
        File.WriteAllText("Tools/TreeBarkVerification.txt", "PASS: 2K Poly Haven Bark Brown 02: diffuse, normal and HDRP packed AO/roughness mask assigned.\nTriplanar mapping enabled; existing tree bark material updated, leaves unchanged.\n");
        Selection.activeObject = material;
        Debug.Log("Realistic HDRP tree bark ready.");
    }
    static Texture2D Import(string suffix, bool normal)
    {
        string path = Folder + "bark_brown_02_" + suffix + "_2k.jpg";
        AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceSynchronousImport);
        var importer = (TextureImporter)AssetImporter.GetAtPath(path);
        importer.textureType = normal ? TextureImporterType.NormalMap : TextureImporterType.Default;
        importer.sRGBTexture = !normal;
        importer.wrapMode = TextureWrapMode.Repeat;
        importer.maxTextureSize = 2048;
        importer.SaveAndReimport();
        return AssetDatabase.LoadAssetAtPath<Texture2D>(path);
    }
    static Texture2D ReadImage(string suffix)
    {
        var image = new Texture2D(2, 2, TextureFormat.RGB24, false, true);
        if (!image.LoadImage(File.ReadAllBytes(Folder + "bark_brown_02_" + suffix + "_2k.jpg")))
            throw new Exception("Unable to read bark image: " + suffix);
        return image;
    }
}
