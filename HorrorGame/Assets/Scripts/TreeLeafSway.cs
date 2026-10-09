using System.Collections.Generic;
using UnityEngine;

[ExecuteAlways, DisallowMultipleComponent, RequireComponent(typeof(MeshFilter))]
public sealed class TreeLeafSway : MonoBehaviour
{
    public Mesh sourceMesh;
    [Range(0f, 20f)] public float swayDegrees = 6f;
    [Range(0.1f, 4f)] public float speed = 1.1f;
    MeshFilter filter;
    Mesh animatedMesh;
    Vector3[] rest, moving, normals, movingNormals;
    Vector4[] tangents, movingTangents;
    readonly List<Card> cards = new List<Card>();
    double nextUpdate;
    struct Card { public int[] indices; public Vector3 pivot; public float phase; }

    void OnEnable()
    {
        filter = GetComponent<MeshFilter>();
        if (!sourceMesh) sourceMesh = filter.sharedMesh;
        var renderer = GetComponent<MeshRenderer>();
        if (renderer)
        {
            foreach (var material in renderer.sharedMaterials)
                if (material && material.shader && material.shader.name == "HorrorGame/HDRP/Leaves Wind Lit")
                {
                    if (sourceMesh) filter.sharedMesh = sourceMesh;
                    return; // GPU wind also handles individually placed trees; avoid double movement.
                }
        }
        // Keep permanent mesh references while editing and in prefab import/terrain scans.
        // Terrain-painted instances are rendered directly and do not execute this script.
        if (!Application.IsPlaying(gameObject))
        {
            if (sourceMesh) filter.sharedMesh = sourceMesh;
            return;
        }
        if (!sourceMesh || sourceMesh.subMeshCount < 2 || !sourceMesh.isReadable) return;
        animatedMesh = Instantiate(sourceMesh);
        animatedMesh.name = sourceMesh.name + " (live leaves)";
        animatedMesh.hideFlags = HideFlags.HideAndDontSave;
        animatedMesh.MarkDynamic();
        rest = sourceMesh.vertices; moving = (Vector3[])rest.Clone();
        normals = sourceMesh.normals; movingNormals = (Vector3[])normals.Clone();
        tangents = sourceMesh.tangents; movingTangents = (Vector4[])tangents.Clone();
        Vector2[] uv = sourceMesh.uv;
        int[] triangles = sourceMesh.GetTriangles(1);
        cards.Clear();
        for (int i = 0; i + 5 < triangles.Length; i += 6)
        {
            var indices = new List<int>(4);
            for (int j = 0; j < 6; j++) if (!indices.Contains(triangles[i+j])) indices.Add(triangles[i+j]);
            if (indices.Count != 4) continue;
            float lowest = float.MaxValue;
            foreach (int index in indices) lowest = Mathf.Min(lowest, uv[index].y);
            Vector3 pivot = Vector3.zero; int count = 0;
            foreach (int index in indices) if (uv[index].y <= lowest + 0.001f) { pivot += rest[index]; count++; }
            pivot /= Mathf.Max(1, count);
            cards.Add(new Card { indices = indices.ToArray(), pivot = pivot,
                phase = pivot.x * 2.13f + pivot.y * 1.47f + pivot.z * 2.71f });
        }
        Bounds bounds = animatedMesh.bounds;
        bounds.Expand(2f);
        animatedMesh.bounds = bounds;
        filter.sharedMesh = animatedMesh;
        var lod = GetComponent<LODGroup>();
        if (lod) lod.RecalculateBounds();
        nextUpdate = 0;
    }

    void Update()
    {
        if (!animatedMesh || Time.realtimeSinceStartupAsDouble < nextUpdate) return;
        nextUpdate = Time.realtimeSinceStartupAsDouble + 1.0 / 30.0;
        Animate((float)Time.realtimeSinceStartupAsDouble);
    }

    public void Animate(float time)
    {
        if (!animatedMesh) return;
        foreach (Card card in cards)
        {
            float angle = (Mathf.Sin(time * speed * 2f + card.phase)
                + 0.3f * Mathf.Sin(time * speed * 3.7f + card.phase * 1.3f)) * swayDegrees;
            Quaternion rotation = Quaternion.AngleAxis(angle, new Vector3(0.7f, 0.15f, 1f).normalized);
            foreach (int index in card.indices)
            {
                moving[index] = card.pivot + rotation * (rest[index] - card.pivot);
                if (normals.Length == rest.Length) movingNormals[index] = rotation * normals[index];
                if (tangents.Length == rest.Length)
                {
                    Vector3 tangent = rotation * new Vector3(tangents[index].x, tangents[index].y, tangents[index].z);
                    movingTangents[index] = new Vector4(tangent.x, tangent.y, tangent.z, tangents[index].w);
                }
            }
        }
        animatedMesh.vertices = moving;
        if (normals.Length == rest.Length) animatedMesh.normals = movingNormals;
        if (tangents.Length == rest.Length) animatedMesh.tangents = movingTangents;
    }

    void OnDisable()
    {
        if (filter && filter.sharedMesh == animatedMesh) filter.sharedMesh = sourceMesh;
        if (animatedMesh)
        {
            if (Application.isPlaying) Destroy(animatedMesh); else DestroyImmediate(animatedMesh);
        }
        animatedMesh = null;
        cards.Clear();
    }
}
