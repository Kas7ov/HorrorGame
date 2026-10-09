using UnityEngine;

[RequireComponent(typeof(BoxCollider), typeof(Rigidbody))]
public sealed class DragonEyeTrigger : MonoBehaviour
{
    public DragonEyeEvent dragonEye;
    [Tooltip("Only this player or its child colliders can activate the event.")]
    public Transform playerRoot;
    public bool triggerOnce = true;
    bool activated;

    void Reset()
    {
        GetComponent<BoxCollider>().isTrigger = true;
        var body = GetComponent<Rigidbody>();
        body.isKinematic = true;
        body.useGravity = false;
    }

    void OnTriggerEnter(Collider other)
    {
        if (activated && triggerOnce || !dragonEye) return;
        bool isPlayer = playerRoot
            ? other.transform == playerRoot || other.transform.IsChildOf(playerRoot)
            : other.GetComponentInParent<CharacterController>() != null;
        if (!isPlayer) return;
        activated = true;
        dragonEye.OpenEye();
        Debug.Log("Dragon eye awakened by player entering the trigger.", this);
    }

    void OnDrawGizmos()
    {
        var box = GetComponent<BoxCollider>();
        Gizmos.color = new Color(0.9f, 0.05f, 0.05f, 0.25f);
        Gizmos.matrix = transform.localToWorldMatrix;
        Gizmos.DrawWireCube(box.center, box.size);
    }
}
