using UnityEngine;

public class VirtualMouseUI : MonoBehaviour
{
    // Public API requested
    public Vector2 turn;
    public float sensitivity = 0.5f;
    public float speed = 1f;
    public GameObject mover;

    [Header("UI mapping & stopping")]
    public float pixelsPerUnit = 100f;
    public float stopRadius = 2f;           // snap radius (pixels)
    public float recenterSpeed = 0.5f;      // how quickly the virtual cursor decays toward center

    [Header("Camera follow")]
    public float rotationFactor = 1f;       // how much UI offset maps into camera rotation
    public float cameraRotationSpeed = 5f;  // slerp speed for camera rotation

    private RectTransform moverRT;
    private Canvas parentCanvas;
    private RectTransform canvasRT;

    void Start()
    {
        Cursor.lockState = CursorLockMode.Locked;
        if (mover != null)
        {
            moverRT = mover.GetComponent<RectTransform>();
            parentCanvas = mover.GetComponentInParent<Canvas>();
            if (parentCanvas != null)
                canvasRT = parentCanvas.GetComponent<RectTransform>();
        }
    }

    void Update()
    {
        if (moverRT == null)
            return;

        // 1) accumulate mouse delta into `turn`
        turn.x += Input.GetAxis("Mouse X") * sensitivity;
        turn.y += Input.GetAxis("Mouse Y") * sensitivity;

        // 2) automatic recenter of the virtual cursor (makes the UI drift back toward center)
        turn = Vector2.MoveTowards(turn, Vector2.zero, recenterSpeed * Time.deltaTime);

        // 3) compute target anchored position in pixels from center
        Vector2 targetAnchored = new Vector2(turn.x * pixelsPerUnit, turn.y * pixelsPerUnit);

        // 4) move the UI element toward the target smoothly
        Vector2 current = moverRT.anchoredPosition;
        float maxDelta = speed * pixelsPerUnit * Time.deltaTime;
        Vector2 next = Vector2.MoveTowards(current, targetAnchored, maxDelta);

        // 5) clamp to canvas bounds so the UI never leaves the canvas
        if (canvasRT != null)
        {
            Vector2 half = canvasRT.rect.size * 0.5f;
            next.x = Mathf.Clamp(next.x, -half.x, half.x);
            next.y = Mathf.Clamp(next.y, -half.y, half.y);
        }

        // 6) stop and snap to exact center when both UI and target are within stopRadius
        if (next.magnitude <= stopRadius && targetAnchored.magnitude <= stopRadius)
        {
            moverRT.anchoredPosition = Vector2.zero;
            turn = Vector2.zero;
        }
        else
        {
            moverRT.anchoredPosition = next;
        }

        // 7) rotate the camera smoothly toward the UI offset (so camera "moves toward" the UI)
        //    Map the UI anchored position back to turn units (inverse of pixelsPerUnit)
        Vector2 uiTurn = moverRT.anchoredPosition / Mathf.Max(0.0001f, pixelsPerUnit);
        Quaternion targetRot = Quaternion.Euler(-uiTurn.y * rotationFactor, uiTurn.x * rotationFactor, 0f);
        transform.localRotation = Quaternion.Slerp(transform.localRotation, targetRot, cameraRotationSpeed * Time.deltaTime);
    }
}