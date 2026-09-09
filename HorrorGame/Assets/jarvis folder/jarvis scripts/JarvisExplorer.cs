using UnityEngine;
#if ENABLE_INPUT_SYSTEM
using UnityEngine.InputSystem;
#endif

namespace JarvisMansion
{
    [RequireComponent(typeof(CharacterController))]
    public sealed class JarvisExplorer : MonoBehaviour
    {
        public Camera viewCamera;
        public Light flashlight;
        public float walkSpeed = 3.4f;
        public float sprintSpeed = 5.6f;
        public float mouseSensitivity = .12f;
        CharacterController body;
        float pitch, fallSpeed;
        void Start() { body = GetComponent<CharacterController>(); Lock(true); }
        void Lock(bool value) { Cursor.lockState = value ? CursorLockMode.Locked : CursorLockMode.None; Cursor.visible = !value; }
        void OnDisable() { Lock(false); }
        void Update()
        {
            Vector2 move = Vector2.zero, look = Vector2.zero;
            bool sprint = false, use = false, toggle = false, escape = false, click = false;
#if ENABLE_INPUT_SYSTEM
            var k = Keyboard.current; var m = Mouse.current;
            if (k != null)
            {
                move = new Vector2((k.dKey.isPressed ? 1 : 0) - (k.aKey.isPressed ? 1 : 0), (k.wKey.isPressed ? 1 : 0) - (k.sKey.isPressed ? 1 : 0));
                sprint = k.leftShiftKey.isPressed; use = k.eKey.wasPressedThisFrame; toggle = k.fKey.wasPressedThisFrame; escape = k.escapeKey.wasPressedThisFrame;
            }
            if (m != null) { look = m.delta.ReadValue() * mouseSensitivity; click = m.leftButton.wasPressedThisFrame; }
#elif ENABLE_LEGACY_INPUT_MANAGER
            move = new Vector2(Input.GetAxisRaw("Horizontal"), Input.GetAxisRaw("Vertical"));
            look = new Vector2(Input.GetAxis("Mouse X"), Input.GetAxis("Mouse Y")) * 2;
            sprint = Input.GetKey(KeyCode.LeftShift); use = Input.GetKeyDown(KeyCode.E); toggle = Input.GetKeyDown(KeyCode.F); escape = Input.GetKeyDown(KeyCode.Escape); click = Input.GetMouseButtonDown(0);
#endif
            if (escape) Lock(false);
            if (click && Cursor.lockState != CursorLockMode.Locked) Lock(true);
            if (Cursor.lockState != CursorLockMode.Locked) return;
            transform.Rotate(0, look.x, 0);
            pitch = Mathf.Clamp(pitch - look.y, -80, 80);
            viewCamera.transform.localRotation = Quaternion.Euler(pitch, 0, 0);
            Vector3 direction = transform.right * move.x + transform.forward * move.y;
            direction = Vector3.ClampMagnitude(direction, 1) * (sprint ? sprintSpeed : walkSpeed);
            if (body.isGrounded && fallSpeed < 0) fallSpeed = -2;
            fallSpeed += Physics.gravity.y * Time.deltaTime;
            body.Move((direction + Vector3.up * fallSpeed) * Time.deltaTime);
            if (toggle && flashlight) flashlight.enabled = !flashlight.enabled;
            if (use && Physics.Raycast(viewCamera.transform.position, viewCamera.transform.forward, out var hit, 2.8f))
            {
                var door = hit.collider.GetComponentInParent<JarvisDoor>();
                if (door) door.Toggle();
            }
        }
        void OnGUI()
        {
            GUI.Label(new Rect(20, 20, 720, 26), "JARVIS MANOR  |  WASD move  ·  Mouse look  ·  Shift run  ·  E doors  ·  F torch  ·  Esc cursor");
            if (Cursor.lockState == CursorLockMode.Locked) GUI.Label(new Rect(Screen.width / 2f - 3, Screen.height / 2f - 10, 20, 25), "+");
        }
    }
}
