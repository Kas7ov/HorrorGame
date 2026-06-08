using UnityEngine;
using UnityEngine.UI;

public class GoldenEyeCam : MonoBehaviour
{
    [Header("UI References")]
    [Tooltip("Assign the VirtualCursor UI Image from your Canvas here.")]
    public RectTransform virtualCursorUI;

    [Header("Speeds")]
    [Tooltip("How sensitive the virtual cursor is to raw mouse movement.")]
    public float mouseSensitivity = 3f;

    [Tooltip("Base multiplier used when converting cursor offset to camera rotation.")]
    public float cameraFollowSpeed = 1f;

    [Tooltip("Minimum camera rotation speed (when cursor just passed the dead zone).")]
    public float minCameraSpeed = 0.6f;

    [Tooltip("Maximum camera rotation speed (when cursor near the drift limit).")]
    public float maxCameraSpeed = 3.2f;

    [Tooltip("Maximum cursor return speed factor (higher = faster initial return).")]
    public float cursorReturnSpeed = 12f;

    [Tooltip("How quickly camera speed ramps up/down (units per second).")]
    public float cameraAcceleration = 1.5f;

    [Tooltip("Delay (seconds) before the cursor begins returning to center after input stops.")]
    public float cursorReturnDelay = 0.15f;

    [Header("Bounding Box (Dead-zone & Limits)")]
    [Tooltip("Maximum distance (percentage of screen size) the virtual cursor may drift from center (applied independently on X and Y).")]
    [Range(0.05f, 0.9f)]
    public float maxDriftPercentage = 0.35f;

    [Tooltip("Dead zone radius (percentage of screen size). Cursor must pass this to start moving the camera.")]
    [Range(0f, 0.25f)]
    public float deadZonePercentage = 0.12f;

    // Tracker for the virtual crosshair position in screen pixel space
    private Vector2 virtualCursorPos;
    private Vector2 screenCenter;

    // Per-axis drift/deadzone in pixels
    private float maxDriftPixelsX;
    private float maxDriftPixelsY;
    private float deadZonePixelsX;
    private float deadZonePixelsY;

    // Magnitudes used for distance normalization
    private float maxDriftMagnitude;
    private float deadZoneMagnitude;

    // Camera rotation trackers
    private float cameraYaw;
    private float cameraPitch;

    // Ramped speed for camera rotation (stateful so speed does not start at full immediately)
    private float currentCameraSpeed = 0f; // in same units as min/max camera speed

    // Return delay timer
    private float returnDelayTimer = 0f;

    void Start()
    {
        // Fully lock and hide the real Windows hardware cursor
        Cursor.lockState = CursorLockMode.Locked;

        // Initialize positions to the center of your game window
        screenCenter = new Vector2(Screen.width * 0.5f, Screen.height * 0.5f);
        virtualCursorPos = screenCenter;

        RecalculateDriftAndDeadzone();

        // Sync initial rotation with current camera transform
        Vector3 euler = transform.localRotation.eulerAngles;
        cameraYaw = euler.y;
        cameraPitch = euler.x;
    }

    void Update()
    {
        // 1. Fetch raw physical mouse movement
        float inputX = Input.GetAxisRaw("Mouse X") * mouseSensitivity;
        float inputY = Input.GetAxisRaw("Mouse Y") * mouseSensitivity;

        bool isInputActive = !(Mathf.Approximately(inputX, 0f) && Mathf.Approximately(inputY, 0f));

        // When input is active, reset the return delay so return only starts after the delay elapses
        if (isInputActive)
        {
            returnDelayTimer = cursorReturnDelay;
        }
        else
        {
            // Countdown the delay timer when input is not active
            returnDelayTimer = Mathf.Max(0f, returnDelayTimer - Time.deltaTime);
        }

        // 2. Move the virtual cursor freely based on mouse input
        virtualCursorPos.x += inputX;
        virtualCursorPos.y += inputY;

        // Clamp the cursor inside the boundary box so it can't exit the screen space
        Vector2 offsetFromCenter = virtualCursorPos - screenCenter;
        offsetFromCenter.x = Mathf.Clamp(offsetFromCenter.x, -maxDriftPixelsX, maxDriftPixelsX);
        offsetFromCenter.y = Mathf.Clamp(offsetFromCenter.y, -maxDriftPixelsY, maxDriftPixelsY);
        virtualCursorPos = screenCenter + offsetFromCenter;

        // 3. Move the visual UI element to follow our tracked coordinates
        if (virtualCursorUI != null)
        {
            virtualCursorUI.position = virtualCursorPos;
        }

        // 4. Calculate camera rotation only when cursor passes the dead zone
        float distance = offsetFromCenter.magnitude;

        // Determine target camera speed
        float targetCameraSpeed = 0f;
        if (distance > deadZoneMagnitude)
        {
            // Normalized 0..1 where 0 is at dead zone edge and 1 is at max drift edge (using magnitudes)
            float normalized = Mathf.InverseLerp(deadZoneMagnitude, maxDriftMagnitude, distance);

            // Smooth scaling so small pushes are much slower and larger pushes accelerate
            float speedScale = Mathf.SmoothStep(0f, 1f, normalized * normalized);

            // Target speed between min and max, then apply follow multiplier
            targetCameraSpeed = Mathf.Lerp(minCameraSpeed, maxCameraSpeed, speedScale) * cameraFollowSpeed;
        }

        // Ramp current camera speed toward targetCameraSpeed so it doesn't instantly jump
        currentCameraSpeed = Mathf.MoveTowards(currentCameraSpeed, targetCameraSpeed, cameraAcceleration * Time.deltaTime);

        if (currentCameraSpeed > 0f)
        {
            // Directional influence (-1..1) using per-axis max drift
            float dirX = (maxDriftPixelsX > 0f) ? Mathf.Clamp(offsetFromCenter.x / maxDriftPixelsX, -1f, 1f) : 0f;
            float dirY = (maxDriftPixelsY > 0f) ? Mathf.Clamp(offsetFromCenter.y / maxDriftPixelsY, -1f, 1f) : 0f;

            // Apply rotation scaled by current (ramped) speed.
            cameraYaw += dirX * currentCameraSpeed * Time.deltaTime * 100f;
            cameraPitch -= dirY * currentCameraSpeed * Time.deltaTime * 100f;
            cameraPitch = Mathf.Clamp(cameraPitch, -80f, 80f);
        }

        // Apply rotation to the camera
        transform.localRotation = Quaternion.Euler(cameraPitch, cameraYaw, 0f);

        // 5. THE RETURN: If the player isn't forcing mouse movement and the delay expired, glide the cursor back to center
        // Use a speed that is highest when far from center and reduces as it gets closer:
        if (!isInputActive && returnDelayTimer <= 0f)
        {
            // Max return speed in pixels/sec (resolution independent)
            float maxReturnSpeedPixelsPerSec = cursorReturnSpeed * Mathf.Max(Screen.width, Screen.height) * 0.5f;

            // Scale speed proportionally to distance so return starts fast and eases as it approaches center.
            // Use maxDriftMagnitude so X/Y scaling is consistent.
            float proportional = (maxDriftMagnitude > 0f) ? Mathf.Clamp01(distance / maxDriftMagnitude) : 0f;
            float currentReturnSpeed = maxReturnSpeedPixelsPerSec * proportional;

            virtualCursorPos = Vector2.MoveTowards(virtualCursorPos, screenCenter, currentReturnSpeed * Time.deltaTime);

            // Ensure UI follows updated position
            if (virtualCursorUI != null)
                virtualCursorUI.position = virtualCursorPos;
        }
    }

    // Keep screen variables accurate if player resizes or changes resolution
    void OnRectTransformDimensionsChange()
    {
        screenCenter = new Vector2(Screen.width * 0.5f, Screen.height * 0.5f);
        RecalculateDriftAndDeadzone();
    }

    // Recompute per-axis drift/deadzone values and their magnitudes
    private void RecalculateDriftAndDeadzone()
    {
        maxDriftPixelsX = Screen.width * maxDriftPercentage;
        maxDriftPixelsY = Screen.height * maxDriftPercentage;

        deadZonePixelsX = Screen.width * deadZonePercentage;
        deadZonePixelsY = Screen.height * deadZonePercentage;

        maxDriftMagnitude = Mathf.Sqrt(maxDriftPixelsX * maxDriftPixelsX + maxDriftPixelsY * maxDriftPixelsY);
        deadZoneMagnitude = Mathf.Sqrt(deadZonePixelsX * deadZonePixelsX + deadZonePixelsY * deadZonePixelsY);
    }
}