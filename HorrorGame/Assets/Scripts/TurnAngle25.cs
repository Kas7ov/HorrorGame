using UnityEngine;

public class TurnAngle25 : MonoBehaviour
{
    public GameObject player;
    // Start is called once before the first execution of Update after the MonoBehaviour is created
    void Start()
    {
        
    }

    // Update is called once per frame
    void Update()
    {
        if (Input.GetKey(KeyCode.Q))
        {
            // Set the rotation to -25 degrees on the X axis
            var rotation = player.transform.rotation.eulerAngles;
            rotation.x = -25f;
            player.transform.rotation = Quaternion.Euler(rotation);
        }
        else if (Input.GetKey(KeyCode.E))
        {
            // Set the rotation to -25 degrees on the X axis
            var rotation = player.transform.rotation.eulerAngles;
            rotation.x = 25f;
            player.transform.rotation = Quaternion.Euler(rotation);
        }
        else
        {
            player.transform.rotation = Quaternion.Euler(0f, player.transform.rotation.eulerAngles.y, player.transform.rotation.eulerAngles.z);
        }
        
    }
}
