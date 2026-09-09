using UnityEngine;

namespace JarvisMansion
{
    public sealed class JarvisDoor : MonoBehaviour
    {
        public float openAngle = 95;
        public bool startsOpen;
        bool open;
        Quaternion closedRotation;
        void Awake() { closedRotation = transform.localRotation; open = startsOpen; }
        public void Toggle() { open = !open; }
        void Update()
        {
            Quaternion target = closedRotation * Quaternion.Euler(0, open ? openAngle : 0, 0);
            transform.localRotation = Quaternion.RotateTowards(transform.localRotation, target, 105 * Time.deltaTime);
        }
    }
}
