using UnityEngine;

public class Death : MonoBehaviour
{
    // Start is called once before the first execution of Update after the MonoBehaviour is created
    void Start()
    {
        
    }

    // Update is called once per frame
    void Update()
    {
        
    }

    private void OnCollisionEnter(Collision collision)
    {
        if(collision.gameObject.CompareTag("Enemy"))
        {
            Destroy(gameObject); // Destroy the player object
            Debug.Log("Player has died!");
            // Here you can add code to handle the player's death, such as reloading the scene or showing a game over screen.
        }
    }
}
