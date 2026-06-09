using UnityEngine;

public class TurnAngle25 : MonoBehaviour
{
    public GameObject player;
    [Range(0f, 45f)]
    public float angle = 25f;
    [Tooltip("Degrees per second")]
    public float rotationSpeed = 120f;

    void Update()
    {
        if (player == null) return;

        // Determine target X rotation based on input
        float targetX = 0f;
        if (Input.GetKey(KeyCode.Q))
        {
            targetX = angle;
        }
        else if (Input.GetKey(KeyCode.E))
        {
            targetX = -angle;
        }

        // Keep current Y and Z so other rotations are preserved
        var current = player.transform.rotation;
        var targetEuler = new Vector3(player.transform.rotation.eulerAngles.x, player.transform.rotation.eulerAngles.y,targetX);
        var target = Quaternion.Euler(targetEuler);

        // Smoothly rotate towards target
        player.transform.rotation = Quaternion.RotateTowards(current, target, rotationSpeed * Time.deltaTime);
    }
}
