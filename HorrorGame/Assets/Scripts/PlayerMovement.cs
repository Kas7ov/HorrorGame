using UnityEngine;

[RequireComponent(typeof(CharacterController))]
public class PlayerMovement : MonoBehaviour
{
    private CharacterController controller;
    private Vector3 playerVelocity;
    private bool isGrounded;

    [Header("Movement Settings")]
    public float moveSpeed = 5.0f;
    public float gravity = -9.81f;
    public float jumpHeight = 1.5f;

    [Header("Camera Sync")]
    [Tooltip("Assign the camera (or camera rig) whose yaw the player should follow. If null, uses Camera.main.")]
    public Transform cameraTransform;
    public bool rotateOnlyWhenMoving = false;

    [Header("Run (Sprint)")]
    public KeyCode sprintKey = KeyCode.LeftShift;
    [Tooltip("Multiplier applied to base moveSpeed when sprinting.")]
    public float sprintMultiplier = 1.6f;
    [Tooltip("Field of view while running.")]
    public float runFOV = 75f;
    [Tooltip("Normal camera FOV.")]
    public float normalFOV = 60f;
    [Tooltip("How quickly FOV transitions (higher = faster).")]
    public float fovTransitionSpeed = 6f;

    [Header("Crouch & Slide")]
    [Tooltip("Hold this key to crouch. Press (down) to attempt a slide if conditions are met.")]
    public KeyCode crouchKey = KeyCode.LeftControl;
    [Tooltip("Height while crouching.")]
    public float crouchHeight = 1.0f;
    [Tooltip("Percentage of moveSpeed while crouched (0-1).")]
    [Range(0f, 1f)]
    public float crouchSpeedMultiplier = 0.5f;

    [Tooltip("Initial forward slide speed multiplier (applied to current moveSpeed).")]
    public float slideSpeedMultiplier = 1.8f;
    [Tooltip("Maximum time a slide can last in seconds (strong push phase).")]
    public float slideDuration = 0.9f;
    [Tooltip("Minimum horizontal speed required to start a slide.")]
    public float slideStartSpeed = 3.5f;
    [Tooltip("How quickly the controller height transitions (units per second).")]
    public float heightAdjustSpeed = 8f;

    [Header("Slide physics")]
    [Tooltip("How quickly the slide impulse decays (units per second). Higher = stops faster.")]
    public float slideFriction = 6f;
    [Tooltip("How much control player retains during slide (0 = no control, 1 = full control).")]
    [Range(0f, 1f)]
    public float controlDuringSlide = 0.25f;
    [Tooltip("Cooldown after a dash/slide finishes (seconds).")]
    public float slideCooldown = 1.2f;

    [Header("Slope Sliding")]
    [Tooltip("Minimum slope angle (degrees) to consider 'downhill' influence.")]
    public float slopeSlideThresholdAngle = 5f;
    [Tooltip("Downhill acceleration applied to slide velocity while on slope.")]
    public float slopeSlideAcceleration = 9f;
    [Tooltip("Extra ground raycast distance for slope detection.")]
    public float groundRaycastExtra = 0.5f;

    [Header("Forward slope sampling (capsule-friendly)")]
    [Tooltip("Distance ahead of the capsule to sample slope (helps with capsule geometry).")]
    public float forwardSlopeCheckDistance = 0.6f;
    [Tooltip("Vertical offset above sample point to start the spherecast.")]
    public float forwardSampleUp = 0.3f;

    [Header("Slope movement tuning")]
    [Tooltip("How strongly slope affects walking/running speed (positive = faster downhill, slower uphill).")]
    public float slopeSpeedFactor = 0.6f;
    [Tooltip("Minimum allowed slope speed multiplier (prevents negative or too-slow).")]
    public float minSlopeSpeedMultiplier = 0.45f;
    [Tooltip("Maximum allowed slope speed multiplier.")]
    public float maxSlopeSpeedMultiplier = 1.8f;

    // runtime state
    private bool isCrouching = false;
    public bool isSliding = false;
    private float slideTimer = 0f;
    private float slideCooldownTimer = 0f;

    // physics-ish slide velocity (can contain vertical component when projected on slope)
    private Vector3 slideVelocity = Vector3.zero;

    // to restore standing height
    private float standingHeight;
    private Vector3 standingCenter;
    private float targetHeight;
    private Vector3 targetCenter;

    // cached camera component for fov changes
    private Camera cam;

    void Start()
    {
        controller = GetComponent<CharacterController>();

        if (cameraTransform == null && Camera.main != null)
            cameraTransform = Camera.main.transform;

        if (cameraTransform != null)
            cam = cameraTransform.GetComponent<Camera>();
        if (cam == null)
            cam = Camera.main;

        standingHeight = controller.height;
        standingCenter = controller.center;
        targetHeight = standingHeight;
        targetCenter = standingCenter;

        if (cam != null)
            cam.fieldOfView = normalFOV;
    }

    void Update()
    {
        // Cooldown timer decrement
        if (slideCooldownTimer > 0f)
            slideCooldownTimer = Mathf.Max(0f, slideCooldownTimer - Time.deltaTime);

        // Ground check
        isGrounded = controller.isGrounded;
        if (isGrounded && playerVelocity.y < 0)
            playerVelocity.y = -2f;

        // Input
        float moveX = Input.GetAxis("Horizontal");
        float moveZ = Input.GetAxis("Vertical");
        Vector2 rawInput = new Vector2(moveX, moveZ);
        float inputMagnitude = rawInput.magnitude;

        // Move direction relative to camera yaw
        Vector3 moveDirection = Vector3.zero;
        if (cameraTransform != null)
        {
            Vector3 camForward = Vector3.ProjectOnPlane(cameraTransform.forward, Vector3.up).normalized;
            Vector3 camRight = Vector3.ProjectOnPlane(cameraTransform.right, Vector3.up).normalized;
            moveDirection = camRight * moveX + camForward * moveZ;
            if (moveDirection.sqrMagnitude > 1f) moveDirection = moveDirection.normalized;
        }
        else
        {
            moveDirection = transform.right * moveX + transform.forward * moveZ;
            if (moveDirection.sqrMagnitude > 1f) moveDirection = moveDirection.normalized;
        }

        // Rotate player to camera yaw (kept behavior from before)
        if (cameraTransform != null)
        {
            bool shouldRotate = !rotateOnlyWhenMoving || inputMagnitude > 0.01f;
            if (shouldRotate)
            {
                Vector3 flatCamForward = Vector3.ProjectOnPlane(cameraTransform.forward, Vector3.up);
                if (flatCamForward.sqrMagnitude > 0.0001f)
                {
                    Quaternion targetRotation = Quaternion.LookRotation(flatCamForward.normalized, Vector3.up);
                    transform.rotation = Quaternion.RotateTowards(transform.rotation, targetRotation, 0);
                }
            }
        }

        // Running state
        bool runInput = Input.GetKey(sprintKey) && inputMagnitude > 0.01f && !isCrouching && !isSliding;
        float currentBaseSpeed = moveSpeed * (runInput ? sprintMultiplier : 1f);

        // FOV change
        if (cam != null)
        {
            float targetFOV = runInput ? runFOV : normalFOV;
            cam.fieldOfView = Mathf.Lerp(cam.fieldOfView, targetFOV, fovTransitionSpeed * Time.deltaTime);
        }

        // Crouch / slide input
        bool crouchHeld = Input.GetKey(crouchKey);
        bool crouchPressedDown = Input.GetKeyDown(crouchKey);

        // Use centralized handler (slope-aware; slide can start on slope if raycast detects sufficient steepness)
        Vector3 horizontalMove = HandleCrouchAndSlide(moveDirection, inputMagnitude, crouchHeld, crouchPressedDown, currentBaseSpeed, runInput);

        // Apply horizontal and vertical movement
        controller.Move(horizontalMove * Time.deltaTime);

        // Jump (cancels slide)
        if (Input.GetButtonDown("Jump") && isGrounded)
        {
            playerVelocity.y = Mathf.Sqrt(jumpHeight * -2f * gravity);
            if (isSliding)
            {
                isSliding = false;
                isCrouching = false;
                targetHeight = standingHeight;
                targetCenter = standingCenter;
                slideCooldownTimer = slideCooldown;
            }
        }

        // Gravity
        playerVelocity.y += gravity * Time.deltaTime;
        controller.Move(playerVelocity * Time.deltaTime);
    }

    /// <summary>
    /// Returns world-space bottom center position of the character (capsule).
    /// This is used as a reliable start for ground sampling.
    /// </summary>
    private Vector3 GetFeetPosition()
    {
        // controller.center is local; transform.TransformPoint gives world
        Vector3 worldCenter = transform.TransformPoint(controller.center);
        float halfHeight = Mathf.Max(0f, controller.height * 0.5f - controller.radius);
        return worldCenter - Vector3.up * halfHeight;
    }

    /// <summary>
    /// Spherecasts down from a sample origin and returns whether we hit ground,
    /// plus the hit normal and hitInfo. This function is tolerant to capsule shape
    /// because we start near the feet and use the controller radius for the sphere.
    /// </summary>
    private bool SampleGroundAt(Vector3 sampleOrigin, out Vector3 normal, out RaycastHit hitInfo)
    {
        hitInfo = default;
        normal = Vector3.up;

        float radius = Mathf.Max(0.01f, controller.radius * 0.9f);
        float maxDist = controller.height * 0.5f + groundRaycastExtra;
        if (Physics.SphereCast(sampleOrigin + Vector3.up * forwardSampleUp, radius, Vector3.down, out hitInfo, maxDist, ~0, QueryTriggerInteraction.Ignore))
        {
            normal = hitInfo.normal;
            return true;
        }

        return false;
    }

    /// <summary>
    /// Samples ground under center and slightly forward in movement direction (capsule-friendly).
    /// Returns the most relevant ground normal and hit based on movement direction.
    /// </summary>
    private bool SampleGroundForward(Vector3 moveDirection, float forwardDistance, out Vector3 groundNormal, out RaycastHit forwardHit)
    {
        groundNormal = Vector3.up;
        forwardHit = default;

        Vector3 feet = GetFeetPosition();

        // center sample
        Vector3 centerOrigin = feet + Vector3.up * 0.05f;
        Vector3 centerNormal;
        RaycastHit centerHit;
        bool center = SampleGroundAt(centerOrigin, out centerNormal, out centerHit);

        // forward sample
        Vector3 forwardOffset = (moveDirection.sqrMagnitude > 0.001f) ? moveDirection.normalized * forwardDistance : transform.forward * forwardDistance;
        Vector3 forwardOrigin = feet + forwardOffset + Vector3.up * 0.05f;
        Vector3 fNormal;
        RaycastHit fHit;
        bool forward = SampleGroundAt(forwardOrigin, out fNormal, out fHit);

        // choose forward sample if it exists and is steeper or if player is moving forward
        if (forward)
        {
            groundNormal = fNormal;
            forwardHit = fHit;
            return true;
        }

        if (center)
        {
            groundNormal = centerNormal;
            forwardHit = centerHit;
            return true;
        }

        return false;
    }

    /// <summary>
    /// Handles crouch + slide logic.
    /// - Slide starts when sprint+crouch pressed while moving OR when sprint+crouch pressed while a forward raycast detects a slope >= threshold.
    /// - If sliding and the raycast detects a downhill slope, slope will accelerate the slide (so slide continues down slopes).
    /// - If sliding wasn't started, slopes only modify walking speed (downhill faster, uphill slower).
    /// This version samples forward ground to work with capsule colliders.
    /// </summary>
    private Vector3 HandleCrouchAndSlide(Vector3 moveDirection, float inputMagnitude, bool crouchHeld, bool crouchPressedDown, float baseMoveSpeed, bool isRunning)
    {
        // Manage crouch state (hold to crouch) - do not override if sliding
        if (crouchHeld && !isSliding)
        {
            isCrouching = true;
            targetHeight = crouchHeight;
            targetCenter = new Vector3(standingCenter.x, crouchHeight / 2f, standingCenter.z);
        }
        else if (!isSliding)
        {
            isCrouching = false;
            targetHeight = standingHeight;
            targetCenter = standingCenter;
        }

        // Smoothly adjust controller height/center
        if (Mathf.Abs(controller.height - targetHeight) > 0.001f)
        {
            controller.height = Mathf.MoveTowards(controller.height, targetHeight, heightAdjustSpeed * Time.deltaTime);
            controller.center = Vector3.MoveTowards(controller.center, targetCenter, heightAdjustSpeed * Time.deltaTime);
        }

        // Sample forward ground (capsule-friendly)
        Vector3 groundNormal = Vector3.up;
        RaycastHit forwardHit;
        bool groundFound = isGrounded && SampleGroundForward(moveDirection, forwardSlopeCheckDistance, out groundNormal, out forwardHit);
        float slopeAngle = Vector3.Angle(groundNormal, Vector3.up);
        Vector3 downhill = Vector3.zero;
        if (groundFound && slopeAngle > slopeSlideThresholdAngle)
            downhill = Vector3.ProjectOnPlane(Vector3.down, groundNormal).normalized;

        // Compute current horizontal speed estimate (used for slide-start tests)
        float currentHorizontalSpeed = baseMoveSpeed * inputMagnitude * (isCrouching ? crouchSpeedMultiplier : 1f);
        bool hasMovementInput = inputMagnitude > 0.01f;
        bool slopeAllowsStart = groundFound && slopeAngle >= slopeSlideThresholdAngle;

        // Slide start condition:
        // - sprint + crouch pressed while moving (existing behavior), OR
        // - sprint + crouch pressed while standing on a sufficiently steep downhill slope (forward sample detects slope)
        if (crouchPressedDown && !isSliding && isRunning && slideCooldownTimer <= 0f && (hasMovementInput || slopeAllowsStart) && isGrounded)
        {
            isSliding = true;
            slideTimer = slideDuration;

            // slide direction: prefer downhill when forward sample shows slope, otherwise player input direction
            Vector3 slideDir;
            if (slopeAllowsStart && downhill.sqrMagnitude > 0.001f && !hasMovementInput)
                slideDir = downhill; // start sliding down the slope even if player isn't pressing forward
            else
                slideDir = moveDirection.sqrMagnitude > 0.001f ? moveDirection.normalized : transform.forward;

            slideVelocity = slideDir * (baseMoveSpeed * slideSpeedMultiplier);

            // Project initial velocity onto slope plane so movement follows the surface (keeps vertical component)
            slideVelocity = Vector3.ProjectOnPlane(slideVelocity, groundNormal);

            // enforce crouch visually
            isCrouching = true;
            targetHeight = crouchHeight;
            targetCenter = new Vector3(standingCenter.x, crouchHeight / 2f, standingCenter.z);
        }

        // Apply slide or normal movement
        Vector3 horizontalMove = Vector3.zero;
        if (isSliding)
        {
            // Player retains limited control during slide (adds to slideVelocity)
            Vector3 inputContribution = moveDirection * baseMoveSpeed * controlDuringSlide;

            // If forward sample indicates downhill, accelerate along downhill direction so slide continues down
            if (downhill.sqrMagnitude > 0.001f)
            {
                slideVelocity += downhill * slopeSlideAcceleration * Time.deltaTime;
                slideVelocity = Vector3.ProjectOnPlane(slideVelocity, groundNormal);

                // avoid giving slide an uphill component
                float dot = Vector3.Dot(slideVelocity, downhill);
                if (dot < 0f)
                    slideVelocity -= downhill * dot;
            }
            else
            {
                // even without downhill, keep movement projected to ground to avoid climbing tiny bumps
                slideVelocity = Vector3.ProjectOnPlane(slideVelocity, Vector3.up);
            }

            horizontalMove = slideVelocity + inputContribution;

            // strong-push phase timer
            slideTimer -= Time.deltaTime;
            if (slideTimer <= 0f || !isGrounded)
            {
                // exit strong push phase; start cooldown
                isSliding = false;
                slideCooldownTimer = slideCooldown;
            }

            // decay slide impulse due to friction every frame
            slideVelocity = Vector3.MoveTowards(slideVelocity, Vector3.zero, slideFriction * Time.deltaTime);
        }
        else
        {
            // Normal movement: apply slope speed adjustment so uphill slower, downhill faster.
            Vector3 inputMove = moveDirection * baseMoveSpeed * (isCrouching ? crouchSpeedMultiplier : 1f);

            if (moveDirection.sqrMagnitude > 0.001f && downhill.sqrMagnitude > 0.001f)
            {
                Vector3 moveDirNorm = moveDirection.normalized;
                float slopeDot = Vector3.Dot(moveDirNorm, downhill); // +1 when moving downhill, -1 uphill
                float speedAdjustment = 1f + slopeDot * slopeSpeedFactor;
                speedAdjustment = Mathf.Clamp(speedAdjustment, minSlopeSpeedMultiplier, maxSlopeSpeedMultiplier);
                inputMove *= speedAdjustment;
            }

            // residual slide momentum still applies
            horizontalMove = inputMove + slideVelocity;

            // slope influence for residual momentum
            if (downhill.sqrMagnitude > 0.001f && slideVelocity.sqrMagnitude > 0.001f)
            {
                slideVelocity += downhill * slopeSlideAcceleration * Time.deltaTime;
                slideVelocity = Vector3.ProjectOnPlane(slideVelocity, groundNormal);
            }

            slideVelocity = Vector3.MoveTowards(slideVelocity, Vector3.zero, slideFriction * Time.deltaTime);

            // If slideVelocity is nearly zero, clear it to avoid tiny drift
            if (slideVelocity.sqrMagnitude < 0.01f)
                slideVelocity = Vector3.zero;
        }

        // When slide fully finished and player not holding crouch, restore height
        if (!isSliding && slideVelocity == Vector3.zero && !crouchHeld)
        {
            isCrouching = false;
            targetHeight = standingHeight;
            targetCenter = standingCenter;
        }

        return horizontalMove;
    }

    // Editor gizmos to visualize ground sampling used for sliding (center + forward)
    void OnDrawGizmosSelected()
    {
        if (controller == null)
            controller = GetComponent<CharacterController>();
        if (controller == null)
            return;

        Gizmos.color = Color.yellow;
        Vector3 feet = GetFeetPosition();
        Gizmos.DrawWireSphere(feet + Vector3.up * forwardSampleUp, Mathf.Max(0.01f, controller.radius * 0.9f));
        Gizmos.DrawLine(feet + Vector3.up * forwardSampleUp, feet + Vector3.up * forwardSampleUp + Vector3.down * (controller.height * 0.5f + groundRaycastExtra));

        Vector3 forwardOrigin = feet + transform.forward * forwardSlopeCheckDistance + Vector3.up * forwardSampleUp;
        Gizmos.color = Color.blue;
        Gizmos.DrawWireSphere(forwardOrigin, Mathf.Max(0.01f, controller.radius * 0.9f));
        Gizmos.DrawLine(forwardOrigin, forwardOrigin + Vector3.down * (controller.height * 0.5f + groundRaycastExtra));

        // draw a small forward direction marker
        Gizmos.color = Color.white;
        Gizmos.DrawLine(transform.position, transform.position + transform.forward * 0.5f);
    }
}