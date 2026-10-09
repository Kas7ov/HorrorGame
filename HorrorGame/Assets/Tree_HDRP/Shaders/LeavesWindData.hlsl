// HDRP Lit shading is unchanged; extend its raster vertex displacement hook.
#define ApplyVertexModification ApplyOriginalLitVertexModification
#include "Packages/com.unity.render-pipelines.high-definition/Runtime/Material/Lit/LitData.hlsl"
#undef ApplyVertexModification

#if !defined(SHADER_STAGE_RAY_TRACING)
void ApplyVertexModification(AttributesMesh input, float3 normalWS,
    inout float3 positionRWS, float3 timeParameters)
{
    ApplyOriginalLitVertexModification(input, normalWS, positionRWS, timeParameters);
    #ifdef ATTRIBUTES_NEED_TEXCOORD0
        // Bottom of each card stays anchored; tips move most. Leaf material only.
        float weight = saturate(input.uv0.y);
        float3 absolutePosition = GetAbsolutePositionWS(positionRWS);
        float phase = dot(absolutePosition.xz, float2(0.73, 1.17)) + absolutePosition.y * 0.35;
        float flutter = sin(timeParameters.x * 2.2 + phase)
            + 0.3 * sin(timeParameters.x * 4.07 + phase * 1.3);
        float gust = 0.8 + 0.2 * sin(timeParameters.x * 0.43 + phase * 0.2);
        positionRWS += float3(0.8, 0.06, 0.5) * (0.15 * weight * flutter * gust);
    #endif
}
#endif
