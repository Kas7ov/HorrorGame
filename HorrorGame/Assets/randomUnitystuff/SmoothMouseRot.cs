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
        //Cursor.visible = ;
        virtualMouse = Vector2.zero;
    }

    void LateUpdate()
    {
        // 1. Read physical cursor in normalized screen space (-1..1)
        float mouseXNormalized = (Input.mousePosition.x / Screen.width) * 2f - 1f;
        float mouseYNormalized = (Input.mousePosition.y / Screen.height) * 2f - 1f;
        Vector2 target = new Vector2(mouseXNormalized, mouseYNormalized);

        // 2. Update virtual mouse: follow physical cursor + recenter toward (0,0)
        Vector2 followDelta = (target - virtualMouse) * mouseFollowSpeed;
        Vector2 recenterDelta = -virtualMouse * recenterSpeed;
        Vector2 netDelta = followDelta + recenterDelta;
        virtualMouse += netDelta * Time.deltaTime;

        // 3. Apply deadzone to prevent jitter
        if (virtualMouse.magnitude < deadzone) virtualMouse = Vector2.zero;

        // 4. Convert virtual mouse to rotation input
        float turnX = virtualMouse.x * rotationSpeed * Time.deltaTime * 50f;
        float turnY = virtualMouse.y * rotationSpeed * Time.deltaTime * 50f;

        // 5. Apply rotation with vertical clamp
        Vector3 currentRotation = transform.localEulerAngles;
        float newPitch = currentRotation.x;
        if (newPitch > 180f) newPitch -= 360f;
        newPitch -= turnY;
        newPitch = Mathf.Clamp(newPitch, -80f, 80f);
        float newYaw = currentRotation.y + turnX;
        transform.localRotation = Quaternion.Euler(newPitch, newYaw, 0f);
    }
}