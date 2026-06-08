using UnityEngine;

public class HorrorCameraLook : MonoBehaviour
{
    [Header("Sensitivity & Cursor")]
    [Tooltip("Multiplier applied to the angular speed computed from cursor distance.")]
    public float mouseSensitivity = 1f;
    public bool invertY = false;
    public bool lockCursor = false; // keep false so cursor is free

    [Header("Center / Threshold")]
    [Tooltip("Fraction of screen radius (0..1). Cursor must pass this distance from center to start rotating.")]
    [Range(0f, 1f)]
    public float centerThreshold = 0.15f;

    [Header("Angular speed (degrees/sec)")]
    [Tooltip("Angular speed when cursor is just past the threshold.")]
    public float minAngularSpeed = 15f;
    [Tooltip("Angular speed when cursor is at the edge of the screen.")]
    public float maxAngularSpeed = 90f;
    [Tooltip("Exponent used to shape the speed interpolation (>=1). Higher = slower near threshold, faster near edge.")]
    public float speedExponent = 2f;

    [Header("Return to center")]
    [Tooltip("Degrees per second the camera returns to the base orientation when cursor is inside threshold.")]
    public float returnSpeed = 60f;

    [Header("Pitch limits")]
    [Tooltip("Maximum angle up/down from base pitch.")]
    public float maxLookAngle = 45f;

    // base orientation captured at start (signed angles)
    private float baseYaw;
    private float basePitch;

    // offsets applied on top of base orientation (yaw unbounded; pitch clamped)
    private float yawOffset = 0f;
    private float pitchOffset = 0f;

    void Start()
    {
        if (lockCursor)
        {
            Cursor.lockState = CursorLockMode.Locked;
            Cursor.visible = false;
        }
        else
        {
            Cursor.lockState = CursorLockMode.None;
            Cursor.visible = true;
        }

        Vector3 e = transform.localEulerAngles;
        baseYaw = e.y;
        basePitch = e.x;
        if (basePitch > 180f) basePitch -= 360f; // convert to signed angle
    }

    void Update()
    {
        // compute cursor offset from screen center in normalized -1..1 space for each axis
        Vector2 screenCenter = new Vector2(Screen.width * 0.5f, Screen.height * 0.5f);
        Vector2 mousePos = new Vector2(Input.mousePosition.x, Input.mousePosition.y);
        Vector2 offsetPixels = mousePos - screenCenter;

        // convert to normalized radius where x/y separately map -1..1 at screen edges
        Vector2 norm = new Vector2(
            offsetPixels.x / (Screen.width * 0.5f),
            offsetPixels.y / (Screen.height * 0.5f)
        );

        // distance from center in normalized units (0..~1)
        float dist = norm.magnitude;

        if (dist > centerThreshold)
        {
            // normalized distance 0..1 representing how far beyond the threshold the cursor is
            float t = Mathf.Clamp01((dist - centerThreshold) / (1f - centerThreshold));
            // shape the response so it's slow near threshold and accelerates toward edge
            float shaped = Mathf.Pow(t, speedExponent);

            // compute angular speed (deg/sec) for this frame, scaled by sensitivity
            float angularSpeed = Mathf.Lerp(minAngularSpeed, maxAngularSpeed, shaped) * Mathf.Clamp01(mouseSensitivity);

            // direction: x controls yaw, y controls pitch. Invert Y if requested.
            float dirX = norm.x; // left/right
            float dirY = invertY ? norm.y : -norm.y; // up/down (negate so cursor up looks up)

            // integrate offsets (degrees)
            yawOffset += angularSpeed * dirX * Time.deltaTime;
            pitchOffset += angularSpeed * dirY * Time.deltaTime;

            // clamp pitch offset to allowed range
            pitchOffset = Mathf.Clamp(pitchOffset, -maxLookAngle, maxLookAngle);
        }
        else
        {
            // inside threshold: smoothly return offsets toward zero (base orientation)
            yawOffset = Mathf.MoveTowards(yawOffset, 0f, returnSpeed * Time.deltaTime);
            pitchOffset = Mathf.MoveTowards(pitchOffset, 0f, returnSpeed * Time.deltaTime);
        }

        // apply final rotation: base + offsets (yaw unbounded so 360+ allowed)
        float appliedPitch = basePitch + pitchOffset;
        float appliedYaw = baseYaw + yawOffset;
        transform.localRotation = Quaternion.Euler(appliedPitch, appliedYaw, 0f);
    }
}