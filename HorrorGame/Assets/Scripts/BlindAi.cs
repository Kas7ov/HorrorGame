using System.Collections;
using Unity.VisualScripting;
using UnityEngine;
using UnityEngine.AI;

public class BlindAi : MonoBehaviour
{
    public GameObject player;
    public NavMeshAgent agent;
    public GameObject[] waypoints;
    public float detectionpoints;
    public float detectionPointsMax = 100f;
    public float toocloseDistance = 2f;
    public float toomidDistance = 5f;
    public float toofarDistance = 10f;

    // new tuning fields
    public float investigationRadius = 3f; // radius around player to pick a nearby point when investigating
    public float waypointTolerance = 0.5f; // distance to consider a waypoint reached
    public float walkSpeed = 3.5f;
    public float runSpeed = 6f;

    // new waypoint wait tuning
    public float waypointWaitTime = 2f; // configurable wait time at each waypoint
    private bool waitingForWaypoint = false;

    // chase improvements
    public float chasePredictionFactor = 0.5f; // how far ahead to lead the player's velocity
    public float maxPredictionDistance = 4f; // clamp predicted lead distance (EXPOSED)
    public float chaseAcceleration = 20f;
    public float chaseAngularSpeed = 120f;
    public float chaseLossTime = 2.5f; // how long without LOS before fallback
    private float timeSinceLastSeen = 0f;

    // keep chasing briefly after loss to avoid immediate drop when player crouches
    public float chaseExitDelay = 2f; // configurable grace period before leaving chase
    private float chaseExitTimer = 0f;

    private int currentWaypointIndex = 0;

    private enum AiState { Patrol, Investigate, Chase }
    private AiState state = AiState.Patrol;
    private Vector3 investigateTarget;
    private Vector3 lastPlayerPosition;

    void Start()
    {
        if (agent == null)
        {
            agent = GetComponent<NavMeshAgent>();
        }

        // ensure reasonable defaults
        agent.autoBraking = false;

        if (waypoints != null && waypoints.Length > 0)
        {
            agent.SetDestination(waypoints[currentWaypointIndex].transform.position);
        }

        if (player != null)
        {
            lastPlayerPosition = player.transform.position;
        }
    }

    void Update()
    {
        if (player == null || agent == null) return;

        if (detectionpoints > 0f)
        {
            detectionpoints -= Time.deltaTime; // Decrease detection points over time
        }

        float distanceToPlayer = Vector3.Distance(transform.position, player.transform.position);

        // accumulate detection points (preserve original logic but do not return early)
        bool crouching = Input.GetKey(KeyCode.LeftControl);

        if (distanceToPlayer < toocloseDistance)
        {
            if (!crouching)
            {
                if (Input.GetKey(KeyCode.W) || Input.GetKey(KeyCode.A) || Input.GetKey(KeyCode.S) || Input.GetKey(KeyCode.D))
                {
                    detectionpoints += Time.deltaTime * 10f;
                }

                if (Input.GetKey(KeyCode.LeftShift))
                {
                    detectionpoints += Time.deltaTime * 30f;
                }

                if (Input.GetKeyDown(KeyCode.Space))
                {
                    detectionpoints += 50f;
                }

                detectionpoints += Time.deltaTime * 5f;
            }
        }
        else if (distanceToPlayer < toomidDistance)
        {
            if (!crouching)
            {
                if (Input.GetKey(KeyCode.W) || Input.GetKey(KeyCode.A) || Input.GetKey(KeyCode.S) || Input.GetKey(KeyCode.D))
                {
                    detectionpoints += Time.deltaTime * 5f;
                }

                if (Input.GetKey(KeyCode.LeftShift))
                {
                    detectionpoints += Time.deltaTime * 10f;
                }

                if (Input.GetKeyDown(KeyCode.Space))
                {
                    detectionpoints += 10f;
                }

                detectionpoints += Time.deltaTime * 1f;
            }
        }
        else
        {
            // too far - no extra points
            detectionpoints -= Time.deltaTime * 0.5f; // slowly lose points when far away
        }
        if (crouching)
        {
            detectionpoints -= Time.deltaTime * 2f;
        }

        // clamp detectionpoints
        detectionpoints = Mathf.Clamp(detectionpoints, 0f, detectionPointsMax);

        // decide AI state (with chase-exit grace)
        AiState newState = AiState.Patrol;

        if (detectionpoints >= detectionPointsMax)
        {
            newState = AiState.Chase; // highest alert - run directly to player
        }
        else if (detectionpoints >= 50f)
        {
            newState = AiState.Investigate; // medium alert - walk to a random nearby point around player
        }

        // manage chase grace: if we were chasing, give a short delay before allowing exit
        if (state == AiState.Chase)
        {
            if (newState == AiState.Chase)
            {
                // refreshed chase, reset timer
                chaseExitTimer = chaseExitDelay;
            }
            else
            {
                // would exit chase: countdown before switching out
                chaseExitTimer -= Time.deltaTime;
                if (chaseExitTimer > 0f)
                {
                    newState = AiState.Chase; // keep chasing during grace period
                }
            }
        }
        else
        {
            // not in chase: if entering chase, start timer
            if (newState == AiState.Chase)
            {
                chaseExitTimer = chaseExitDelay;
            }
        }

        if (newState != state)
        {
            state = newState;
            OnStateEnter(state);
        }

        // state behaviour
        switch (state)
        {
            case AiState.Chase:
                agent.speed = runSpeed;
                agent.acceleration = chaseAcceleration;
                agent.angularSpeed = chaseAngularSpeed;

                // simple LOS check (helps reset "seen" timer)
                bool hasLOS = !Physics.Linecast(transform.position + Vector3.up * 0.5f, player.transform.position + Vector3.up * 0.5f);
                if (hasLOS)
                {
                    timeSinceLastSeen = 0f;
                }
                else
                {
                    timeSinceLastSeen += Time.deltaTime;
                }

                // predict player's movement to make dodging harder
                Vector3 playerPos = player.transform.position;
                Vector3 playerVelocity = (playerPos - lastPlayerPosition) / Mathf.Max(Time.deltaTime, 0.0001f);
                Vector3 predicted = playerPos + playerVelocity * chasePredictionFactor;

                // clamp prediction distance so AI doesn't wildly overshoot
                Vector3 offset = predicted - playerPos;
                if (offset.magnitude > maxPredictionDistance)
                {
                    predicted = playerPos + offset.normalized * maxPredictionDistance;
                }

                // if we've recently lost LOS for longer than allowed, move to last known position (more persistent)
                if (timeSinceLastSeen > chaseLossTime)
                {
                    agent.SetDestination(lastPlayerPosition);
                }
                else
                {
                    agent.SetDestination(predicted);
                }

                break;

            case AiState.Investigate:
                agent.speed = walkSpeed;
                // ensure we have a valid investigate target set; SetInvestigateTarget called on state enter
                if (!agent.hasPath || Vector3.Distance(agent.destination, investigateTarget) > 0.5f)
                {
                    SetInvestigateTarget();
                }
                break;

            case AiState.Patrol:
            default:
                Patrol();
                break;
        }

        // update last player position for velocity estimation
        lastPlayerPosition = player.transform.position;
    }

    private void OnStateEnter(AiState s)
    {
        if (s == AiState.Investigate)
        {
            SetInvestigateTarget();
        }
        else if (s == AiState.Patrol)
        {
            // resume patrol destination
            if (waypoints != null && waypoints.Length > 0)
            {
                agent.isStopped = false;
                agent.SetDestination(waypoints[currentWaypointIndex].transform.position);
            }
        }
    }

    private void SetInvestigateTarget()
    {
        // pick a random point around the player then snap to NavMesh
        Vector3 randomOffset = Random.insideUnitSphere * investigationRadius;
        Vector3 samplePos = player.transform.position + new Vector3(randomOffset.x, 0f, randomOffset.z);

        NavMeshHit hit;
        if (NavMesh.SamplePosition(samplePos, out hit, investigationRadius, NavMesh.AllAreas))
        {
            investigateTarget = hit.position;
            agent.SetDestination(investigateTarget);
        }
        else
        {
            // fallback to player's position if sampling failed
            investigateTarget = player.transform.position;
            agent.SetDestination(investigateTarget);
        }
    }

    private void Patrol()
    {
        agent.speed = walkSpeed;

        if (waypoints == null || waypoints.Length == 0)
        {
            return;
        }

        if (!agent.pathPending && agent.remainingDistance < waypointTolerance && !waitingForWaypoint)
        {
            // start waiting coroutine instead of instantly switching to next waypoint
            StartCoroutine(WaitAtWaypoint());
        }
    }

    private IEnumerator WaitAtWaypoint()
    {
        waitingForWaypoint = true;
        agent.isStopped = true;
        yield return new WaitForSeconds(waypointWaitTime);

        // advance to next waypoint and resume
        currentWaypointIndex = (currentWaypointIndex + 1) % waypoints.Length;
        agent.isStopped = false;
        agent.SetDestination(waypoints[currentWaypointIndex].transform.position);
        waitingForWaypoint = false;
    }

    // Draw detection ranges and useful debug info in the Scene view when the object is selected.
    private void OnDrawGizmosSelected()
    {
        // draw concentric spheres for detection distances (transparent fill)
        Gizmos.color = new Color(1f, 0f, 0f, 0.12f); // red: too close
        Gizmos.DrawSphere(transform.position, toocloseDistance);

        Gizmos.color = new Color(1f, 0.92f, 0f, 0.08f); // yellow: mid
        Gizmos.DrawSphere(transform.position, toomidDistance);

        Gizmos.color = new Color(0f, 0.6f, 1f, 0.06f); // cyan: far
        Gizmos.DrawSphere(transform.position, toofarDistance);

        // draw investigate radius around player
        if (player != null)
        {
            Gizmos.color = new Color(0f, 1f, 0f, 0.12f);
            Gizmos.DrawWireSphere(player.transform.position, investigationRadius);
        }

        // draw current agent destination and a line to it
        if (agent != null)
        {
            Gizmos.color = Color.magenta;
            Vector3 dest = agent.destination;
            Gizmos.DrawLine(transform.position, dest);
            Gizmos.DrawSphere(dest, 0.15f);
        }
    }
}
