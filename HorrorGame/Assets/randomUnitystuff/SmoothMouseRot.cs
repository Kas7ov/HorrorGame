using UnityEngine;

public class SmoothMouseRot : MonoBehaviour
{
    [Header("Sensitivity Settings")]
    [Tooltip("How fast the camera rotates toward the mouse.")]
    public float rotationSpeed = 2.0f;

    [Tooltip("Deadzone fraction (0 to 1). Mouse must move past this % of the screen center to trigger movement.")]
    public float deadzone = 0.05f;

    [Header("Virtual cursor smoothing & recenter")]
    [Tooltip("How quickly the virtual mouse follows the physical cursor (higher = snappier follow).")]
    public float mouseFollowSpeed = 20f;

    [Tooltip("How quickly the virtual mouse drifts back toward center (higher = faster recentering).")]
    public float recenterSpeed = 5f;

    // Virtual mouse position in normalized screen space (-1..1)
    public Vector2 virtualMouse = Vector2.zero;

    private void Start()
    {
        Cursor.lockState = CursorLockMode.Confined;
        virtualMouse = Vector2.zero;
    }

    void LateUpdate()
    {
        // 1. Read physical cursor in normalized screen space (-1..1)
        float mouseXNormalized = (Input.mousePosition.x / Screen.width) * 2f - 1f;
        float mouseYNormalized = (Input.mousePosition.y / Screen.height) * 2f - 1f;
        Vector2 target = new Vector2(mouseXNormalized, mouseYNormalized);

        // 2. If the physical cursor is inside the deadzone, don't pull virtual mouse toward it.
        //    This lets recentering dominate and causes the virtual mouse to slowly drift back to center.
        Vector2 followDelta = Vector2.zero;
        if (target.magnitude > deadzone)
        {
            followDelta = (target - virtualMouse) * mouseFollowSpeed;
        }

        // 3. Recenter force always pulls virtual mouse toward zero (slower feel).
        Vector2 recenterDelta = -virtualMouse * recenterSpeed;

        // 4. Combine and integrate
        Vector2 netDelta = followDelta + recenterDelta;
        virtualMouse += netDelta * Time.deltaTime;

        // 5. Keep virtual mouse within -1..1 range and allow it to slowly decay to zero (no hard snap).
        virtualMouse = Vector2.ClampMagnitude(virtualMouse, 1f);

        // 6. Convert virtual mouse to rotation input
        float turnX = virtualMouse.x * rotationSpeed * Time.deltaTime * 50f;
        float turnY = virtualMouse.y * rotationSpeed * Time.deltaTime * 50f;

        // 7. Apply rotation with vertical clamp
        Vector3 currentRotation = transform.localEulerAngles;
        float newPitch = currentRotation.x;
        if (newPitch > 180f) newPitch -= 360f;
        newPitch -= turnY;
        newPitch = Mathf.Clamp(newPitch, -80f, 80f);
        float newYaw = currentRotation.y + turnX;
        transform.localRotation = Quaternion.Euler(newPitch, newYaw, 0f);
    }
}