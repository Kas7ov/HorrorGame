using UnityEngine;
using UnityEngine.Rendering.HighDefinition;

public class FitToWaterSurface : MonoBehaviour
{
    [Header("Water Settings")]
    [SerializeField] private WaterSurface waterSurface;

    // Caching parameters to avoid garbage collection allocation in Update
    private WaterSearchParameters searchParameters;
    private WaterSearchResult searchResult;

    void Update()
    {
        if (waterSurface == null) return;

        // 1. Set up the query position based on the object's current X and Z coordinates
        searchParameters.startPositionWS = transform.position;

        // 2. Query the HDRP Water Surface for the projected height on the CPU
        if (waterSurface.ProjectPointOnWaterSurface(searchParameters, out searchResult))
        {
            // 3. Update the object's position to match the calculated water height
            Vector3 targetPosition = transform.position;
            targetPosition.y = searchResult.projectedPositionWS.y;

            transform.position = targetPosition;
        }
    }
}