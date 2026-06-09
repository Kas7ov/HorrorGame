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

    private int currentWaypointIndex = 0;

    private enum AiState { Patrol, Investigate, Chase }
    private AiState state = AiState.Patrol;
    private Vector3 investigateTarget;

    void Start()
    {
        if (agent == null)
        {
            agent = GetComponent<NavMeshAgent>();
        }

        if (waypoints != null && waypoints.Length > 0)
        {
            agent.SetDestination(waypoints[currentWaypointIndex].transform.position);
        }
    }

    void Update()
    {
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
        }

        // clamp detectionpoints
        detectionpoints = Mathf.Clamp(detectionpoints, 0f, detectionPointsMax);

        // decide AI state
        AiState newState = AiState.Patrol;
        if (detectionpoints >= detectionPointsMax)
        {
            newState = AiState.Chase; // highest alert - run directly to player
        }
        else if (detectionpoints >= 50f)
        {
            newState = AiState.Investigate; // medium alert - walk to a random nearby point around player
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
                agent.SetDestination(player.transform.position);
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

        if (!agent.pathPending && agent.remainingDistance < waypointTolerance)
        {
            currentWaypointIndex = (currentWaypointIndex + 1) % waypoints.Length;
            agent.SetDestination(waypoints[currentWaypointIndex].transform.position);
        }
    }
}
