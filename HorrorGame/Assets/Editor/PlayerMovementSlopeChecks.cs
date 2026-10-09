using System;
using System.IO;
using System.Reflection;
using System.Text;
using UnityEditor;
using UnityEngine;

// Runs only from the menu. No scenes are saved and no background work is scheduled.
public static class PlayerMovementSlopeChecks
{
    const BindingFlags PrivateInstance = BindingFlags.Instance | BindingFlags.NonPublic;
    static readonly MethodInfo Step = typeof(PlayerMovement).GetMethod("HandleCrouchAndSlide", PrivateInstance);
    static GameObject fixtures;
    static StringBuilder trace;
    static PlayerMovement scenePlayer;

    [MenuItem("Tools/Player/Verify Slope Movement")]
    public static void Verify()
    {
        if (EditorApplication.isPlaying) throw new InvalidOperationException("Run slope checks outside Play mode.");
        string reportPath = Path.Combine(Application.dataPath, "../Tools/PlayerMovementSlopeVerification.txt");
        try
        {
            trace = new StringBuilder();
            scenePlayer = null;
            foreach (PlayerMovement candidate in UnityEngine.Object.FindObjectsByType<PlayerMovement>(FindObjectsSortMode.None))
                if (candidate.gameObject.scene == UnityEngine.SceneManagement.SceneManager.GetActiveScene()) { scenePlayer = candidate; break; }
            fixtures = new GameObject("Temporary slope verification") { hideFlags = HideFlags.HideAndDontSave };
            Vector3 origin = new Vector3(10000f, 0f, 10000f);
            GameObject ramp = new GameObject("30 degree ramp");
            ramp.transform.SetParent(fixtures.transform);
            ramp.transform.rotation = Quaternion.Euler(0f, 0f, -30f);
            ramp.transform.position = origin - ramp.transform.up * 0.5f;
            ramp.AddComponent<BoxCollider>().size = new Vector3(250f, 1f, 20f);
            GameObject flat = new GameObject("Flat runout");
            flat.transform.SetParent(fixtures.transform);
            flat.transform.position = origin + new Vector3(300f, -0.5f, 0f);
            flat.AddComponent<BoxCollider>().size = new Vector3(100f, 1f, 20f);

            PlayerMovement player = CreatePlayer(origin + Vector3.up * 1.2f);
            CharacterController controller = player.GetComponent<CharacterController>();
            Physics.SyncTransforms();
            controller.Move(Vector3.down * 0.4f);
            Set(player, "isGrounded", controller.isGrounded);
            Require(controller.isGrounded, "Character must contact the ramp.");

            Vector3 downhillWalk = Tick(player, Vector3.right, false, false, 5f, false);
            Vector3 uphillWalk = Tick(player, Vector3.left, false, false, 5f, false);
            Require(downhillWalk.magnitude > 5f && uphillWalk.magnitude < 5f, "Downhill walking must be faster and uphill walking slower.");

            const float dt = 1f / 60f;
            float maxSpeed = 0f;
            float startX = player.transform.position.x;
            for (int frame = 0; frame < 180; frame++)
            {
                Set(player, "isGrounded", controller.isGrounded);
                Vector3 velocity = Tick(player, frame == 0 ? Vector3.right : Vector3.zero, frame == 0, frame == 0, frame == 0 ? 8f : 5f, frame == 0);
                maxSpeed = Mathf.Max(maxSpeed, velocity.magnitude);
                controller.Move((velocity + Vector3.down * 2f) * dt);
                Physics.SyncTransforms();
                if (frame < 12 || frame % 30 == 0)
                    trace.AppendLine($"frame={frame} sliding={player.isSliding} grounded={controller.isGrounded} pos={player.transform.position} velocity={velocity} momentum={Get(player, "slideVelocity")} timer={Get(player, "slideTimer")} grace={Get(player, "slideGroundGraceTimer")}");
            }
            Require(player.isSliding, "Downhill slide must remain active after three seconds without movement input.");
            Require(player.transform.position.x > startX + 10f, "Character must actually travel down the ramp.");
            Require(maxSpeed <= player.moveSpeed * player.sprintMultiplier * player.maxSlideSpeedMultiplier + 0.01f, "Slide must respect the speed cap.");
            float downhillDistance = player.transform.position.x - startX;

            controller.enabled = false;
            player.transform.position = origin + new Vector3(300f, 1.1f, 0f);
            controller.enabled = true;
            Physics.SyncTransforms();
            controller.Move(Vector3.down * 0.4f);
            for (int frame = 0; frame < 240; frame++)
            {
                Set(player, "isGrounded", controller.isGrounded);
                Vector3 velocity = Tick(player, Vector3.zero, false, false, 5f, false);
                controller.Move((velocity + Vector3.down * 2f) * dt);
                Physics.SyncTransforms();
            }
            Require(!player.isSliding && ((Vector3)Get(player, "slideVelocity")).sqrMagnitude < 0.01f, "Slide must come to rest on flat ground.");

            PlayerMovement uphillPlayer = CreatePlayer(origin + new Vector3(0f, 1.2f, 4f));
            CharacterController uphillController = uphillPlayer.GetComponent<CharacterController>();
            Physics.SyncTransforms();
            uphillController.Move(Vector3.down * 0.4f);
            float uphillStartX = uphillPlayer.transform.position.x;
            for (int frame = 0; frame < 30; frame++)
            {
                Set(uphillPlayer, "isGrounded", uphillController.isGrounded);
                Vector3 velocity = Tick(uphillPlayer, frame == 0 ? Vector3.left : Vector3.zero, frame == 0, frame == 0, frame == 0 ? 8f : 5f, frame == 0);
                uphillController.Move((velocity + Vector3.down * 2f) * dt);
                Physics.SyncTransforms();
            }
            Require(!uphillPlayer.isSliding, "Uphill slide must end quickly.");
            Require(uphillStartX - uphillPlayer.transform.position.x < 2f, "Uphill slide must cover only a short distance.");

            string report = "PASS: real CharacterController on a 30-degree ramp, using " + (scenePlayer != null ? "the active scene player's settings.\n" : "default player settings.\n")
                + $"Walking: downhill {downhillWalk.magnitude:F2} m/s; uphill {uphillWalk.magnitude:F2} m/s; flat baseline 5 m/s.\n"
                + $"Downhill: slide continued for 3 seconds without input; peak {maxSpeed:F2} m/s; horizontal distance {downhillDistance:F2} m.\n"
                + "Flat: slide ended and momentum decayed to zero.\n"
                + $"Uphill: slide ended within 0.5 seconds; uphill distance {uphillStartX - uphillPlayer.transform.position.x:F2} m.\n";
            File.WriteAllText(reportPath, report);
            Debug.Log(report);
        }
        catch (Exception exception)
        {
            File.WriteAllText(reportPath, "FAIL: " + exception + "\n" + trace);
            Debug.LogException(exception);
        }
        finally
        {
            if (fixtures != null) UnityEngine.Object.DestroyImmediate(fixtures);
            Physics.SyncTransforms();
        }
    }

    static PlayerMovement CreatePlayer(Vector3 position)
    {
        GameObject go = new GameObject("Test character");
        go.transform.SetParent(fixtures.transform);
        go.transform.position = position;
        CharacterController controller = go.AddComponent<CharacterController>();
        controller.height = 2f;
        controller.radius = 0.5f;
        controller.center = Vector3.zero;
        // Reproduce the extra player collider used by the Ocean scene.
        go.AddComponent<CapsuleCollider>();
        PlayerMovement movement = go.AddComponent<PlayerMovement>();
        if (scenePlayer != null) EditorUtility.CopySerialized(scenePlayer, movement);
        movement.enabled = false;
        movement.isSliding = false;
        Set(movement, "controller", controller);
        Set(movement, "standingHeight", controller.height);
        Set(movement, "standingCenter", controller.center);
        Set(movement, "targetHeight", controller.height);
        Set(movement, "targetCenter", controller.center);
        return movement;
    }

    static Vector3 Tick(PlayerMovement movement, Vector3 direction, bool held, bool pressed, float speed, bool running)
        => (Vector3)Step.Invoke(movement, new object[] { direction, direction.magnitude, held, pressed, speed, running, 1f / 60f });
    static void Set(PlayerMovement movement, string field, object value)
        => typeof(PlayerMovement).GetField(field, PrivateInstance).SetValue(movement, value);
    static object Get(PlayerMovement movement, string field)
        => typeof(PlayerMovement).GetField(field, PrivateInstance).GetValue(movement);
    static void Require(bool condition, string message)
    {
        if (!condition) throw new InvalidOperationException(message);
    }
}
