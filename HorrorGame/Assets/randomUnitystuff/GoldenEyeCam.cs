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

    [Tooltip("Base multiplier used when converting input to camera angular velocity.")]
    public float cameraFollowSpeed = 1f;

    [Tooltip("Minimum camera rotation speed (when input is small).")]
    public float minCameraSpeed = 0.6f;

    [Tooltip("Maximum camera rotation speed (when input is large).")]
    public float maxCameraSpeed = 3.2f;

    [Tooltip("How quickly camera angular velocity ramps up/down (units per second).")]
    public float cameraAcceleration = 1.5f;

    [Tooltip("Maximum cursor return speed factor (higher = faster initial return).")]
    public float cursorReturnSpeed = 12f;

    [Tooltip("Delay (seconds) before the cursor begins returning to center after input stops.")]
    public float cursorReturnDelay = 0.15f;

    [Header("Cursor behaviour")]
    [Tooltip("How strongly the camera rotation is visualized by the virtual cursor (pixels per normalized camera speed).")]
    public float aimFactor = 1f;

    [Tooltip("How fast the virtual cursor follows camera motion (pixels/sec).")]
    public float aimFollowSpeed = 1200f;

    [Tooltip("Max fraction of screen size cursor may drift from center (X and Y applied independently).")]
    [Range(0.05f, 0.9f)]
    public float maxDriftPercentage = 0.35f;

    [Tooltip("Dead zone radius (percentage of screen size). Cursor must pass this to start moving the camera (unused for camera, kept for legacy tuning).")]
    [Range(0f, 0.25f)]
    public float deadZonePercentage = 0.12f;

    // Runtime trackers
    private Vector2 virtualCursorPos;
    private Vector2 screenCenter;

    private float maxDriftPixelsX;
    private float maxDriftPixelsY;
    private float maxDriftMagnitude;

    private float deadZonePixelsX;
    private float deadZonePixelsY;
    private float deadZoneMagnitude;

    private float cameraYaw;
    private float cameraPitch;

    // angular velocity state (degrees/sec like scaled units used by this script)
    private float currentYawVel = 0f;
    private float currentPitchVel = 0f;

    // cursor offset from center in pixels (this is what the visual UI uses)
    private Vector2 aimOffset = Vector2.zero;

    // return delay timer
    private float returnDelayTimer = 0f;

    void Start()
    {
        Cursor.lockState = CursorLockMode.Locked;

        screenCenter = new Vector2(Screen.width * 0.5f, Screen.height * 0.5f);
        virtualCursorPos = screenCenter;

        RecalculateDriftAndDeadzone();

        Vector3 euler = transform.localRotation.eulerAngles;
        cameraYaw = euler.y;
        cameraPitch = euler.x;
    }

    void Update()
    {
        // 1) Read raw input
        float inputX = Input.GetAxisRaw("Mouse X") * mouseSensitivity;
        float inputY = Input.GetAxisRaw("Mouse Y") * mouseSensitivity;
        bool isInputActive = !(Mathf.Approximately(inputX, 0f) && Mathf.Approximately(inputY, 0f));

        // 2) Determine camera angular velocity targets from input (camera moves independently of cursor)
        // We map input to a target angular velocity. The camera will continue to move based on currentYawVel/currentPitchVel
        float targetYawVel = inputX * cameraFollowSpeed * 100f;   // scaled factor -> tuned empirically
        float targetPitchVel = inputY * cameraFollowSpeed * 100f;

        // Ramp angular velocities smoothly so movement doesn't start at full speed
        currentYawVel = Mathf.MoveTowards(currentYawVel, targetYawVel, cameraAcceleration * 100f * Time.deltaTime);
        currentPitchVel = Mathf.MoveTowards(currentPitchVel, targetPitchVel, cameraAcceleration * 100f * Time.deltaTime);

        // 3) Apply angular velocity to camera every frame (camera now moves on its own, independent of cursor)
        cameraYaw += currentYawVel * Time.deltaTime;
        cameraPitch -= currentPitchVel * Time.deltaTime;
        cameraPitch = Mathf.Clamp(cameraPitch, -80f, 80f);
        transform.localRotation = Quaternion.Euler(cameraPitch, cameraYaw, 0f);

        // 4) Virtual cursor: it imitates camera motion.
        // Compute a target aim offset in pixels based on the current angular velocity relative to max camera speed.
        // Normalize using the configured maxCameraSpeed so cursor movement is proportional to how fast camera is turning.
        float denom = Mathf.Max(0.0001f, maxCameraSpeed * 100f); // match scale used for velocity
        float normX = Mathf.Clamp(currentYawVel / denom, -1f, 1f);
        float normY = Mathf.Clamp(currentPitchVel / denom, -1f, 1f);

        Vector2 targetAimOffset = new Vector2(normX * maxDriftPixelsX * aimFactor, -normY * maxDriftPixelsY * aimFactor);

        // When player is actively moving, reset return delay; otherwise count down
        if (isInputActive)
        {
            returnDelayTimer = cursorReturnDelay;
        }
        else
        {
            returnDelayTimer = Mathf.Max(0f, returnDelayTimer - Time.deltaTime);
        }

        // If still in delay, follow camera but do not start the "return-to-center" logic.
        if (returnDelayTimer > 0f)
        {
            // Smoothly move the cursor towards the camera-driven target
            aimOffset = Vector2.MoveTowards(aimOffset, targetAimOffset, aimFollowSpeed * Time.deltaTime);
        }
        else
        {
            // After delay: if there is input or camera still moving, follow target; otherwise return toward center.
            // If targetAimOffset is near zero (camera not moving), we apply a proportional return: fast initially, slow near center.
            if (targetAimOffset.sqrMagnitude > 0.0001f)
            {
                aimOffset = Vector2.MoveTowards(aimOffset, targetAimOffset, aimFollowSpeed * Time.deltaTime);
            }
            else
            {
                // proportional return speed based on current distance from center
                float distance = aimOffset.magnitude;
                float proportional = (maxDriftMagnitude > 0f) ? Mathf.Clamp01(distance / maxDriftMagnitude) : 0f;
                float maxReturnSpeedPixelsPerSec = cursorReturnSpeed * Mathf.Max(Screen.width, Screen.height) * 0.5f;
                float currentReturnSpeed = maxReturnSpeedPixelsPerSec * proportional;

                aimOffset = Vector2.MoveTowards(aimOffset, Vector2.zero, currentReturnSpeed * Time.deltaTime);
            }
        }

        // Clamp final aimOffset so it never exceeds configured per-axis limits
        aimOffset.x = Mathf.Clamp(aimOffset.x, -maxDriftPixelsX, maxDriftPixelsX);
        aimOffset.y = Mathf.Clamp(aimOffset.y, -maxDriftPixelsY, maxDriftPixelsY);

        // Update virtual cursor position and UI
        virtualCursorPos = screenCenter + aimOffset;
        if (virtualCursorUI != null)
            virtualCursorUI.position = virtualCursorPos;
    }

    void OnRectTransformDimensionsChange()
    {
        screenCenter = new Vector2(Screen.width * 0.5f, Screen.height * 0.5f);
        RecalculateDriftAndDeadzone();
    }

    private void RecalculateDriftAndDeadzone()
    {
        maxDriftPixelsX = Screen.width * maxDriftPercentage;
        maxDriftPixelsY = Screen.height * maxDriftPercentage;
        maxDriftMagnitude = Mathf.Sqrt(maxDriftPixelsX * maxDriftPixelsX + maxDriftPixelsY * maxDriftPixelsY);

        deadZonePixelsX = Screen.width * deadZonePercentage;
        deadZonePixelsY = Screen.height * deadZonePercentage;
        deadZoneMagnitude = Mathf.Sqrt(deadZonePixelsX * deadZonePixelsX + deadZonePixelsY * deadZonePixelsY);
    }
}