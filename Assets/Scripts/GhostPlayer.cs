using System.Collections;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.XR.ARFoundation;
using UnityEngine.XR.ARSubsystems;
using System.Collections.Generic;

/// <summary>
/// Manages the AR ghost character: placement on AR planes, animation playback,
/// speed controls, and looping. Attach to the XR Origin GameObject.
/// </summary>
public class GhostPlayer : MonoBehaviour
{
    [Header("AR Components")]
    [Tooltip("Assign the AR Raycast Manager from XR Origin")]
    public ARRaycastManager arRaycastManager;
    
    [Tooltip("Assign the AR Plane Manager from XR Origin")]
    public ARPlaneManager arPlaneManager;

    [Header("Ghost Character")]
    [Tooltip("The ghost character prefab (Humanoid rig with Animator)")]
    public GameObject ghostPrefab;

    [Tooltip("Scale multiplier for the ghost character")]
    public float ghostScale = 1.0f;

    [Header("Playback Settings")]
    [Tooltip("Initial playback speed")]
    public float playbackSpeed = 1.0f;

    [Tooltip("Whether to loop the animation")]
    public bool loopAnimation = true;

    // Runtime state
    private GameObject ghostInstance;
    private Animator ghostAnimator;
    private bool isPlaying = false;
    private bool isPlaced = false;
    private int detectedPlaneCount = 0;
    private List<ARRaycastHit> raycastHits = new List<ARRaycastHit>();

    // Events for UI binding
    public System.Action<bool> OnPlacementChanged;   // true = placed
    public System.Action<bool> OnPlayStateChanged;    // true = playing
    public System.Action<float> OnSpeedChanged;

    void Start()
    {
        Debug.Log($"[GhostPlayer] Starting. RaycastMgr={arRaycastManager != null}, PlaneMgr={arPlaneManager != null}, Prefab={ghostPrefab != null}");
        
        if (ghostPrefab == null)
            Debug.LogError("[GhostPlayer] Ghost Prefab is NOT assigned! Drag your FBX prefab into this field.");
        if (arRaycastManager == null)
            Debug.LogError("[GhostPlayer] AR Raycast Manager is NOT assigned!");

        // Track plane detection
        if (arPlaneManager != null)
            arPlaneManager.planesChanged += OnPlanesChanged;
    }

    void OnPlanesChanged(ARPlanesChangedEventArgs args)
    {
        detectedPlaneCount += args.added.Count;
        if (args.added.Count > 0)
            Debug.Log($"[GhostPlayer] Detected {args.added.Count} new planes! Total: {detectedPlaneCount}");
    }

    void Update()
    {
        // Tap to place ghost on AR plane
        if (!isPlaced && Input.touchCount > 0)
        {
            Touch touch = Input.GetTouch(0);
            if (touch.phase == TouchPhase.Began)
            {
                // Skip if touching a UI button
                if (EventSystem.current != null && EventSystem.current.IsPointerOverGameObject(touch.fingerId))
                {
                    Debug.Log("[GhostPlayer] Touch was on UI element, skipping placement.");
                    return;
                }

                Debug.Log($"[GhostPlayer] Touch at ({touch.position.x}, {touch.position.y}). Attempting AR raycast...");
                TryPlaceGhost(touch.position);
            }
        }
    }

    /// <summary>
    /// Try to place the ghost character on an AR plane at the given screen position.
    /// </summary>
    private void TryPlaceGhost(Vector2 screenPos)
    {
        if (ghostPrefab == null)
        {
            Debug.LogError("[GhostPlayer] Cannot place: Ghost Prefab is null! Assign it in Inspector.");
            return;
        }

        Vector3 placePosition;
        Quaternion placeRotation;
        bool hitPlane = false;

        // Try AR plane raycast first
        if (arRaycastManager != null && arRaycastManager.Raycast(screenPos, raycastHits, TrackableType.PlaneWithinPolygon))
        {
            Pose hitPose = raycastHits[0].pose;
            placePosition = hitPose.position;
            placeRotation = hitPose.rotation;
            hitPlane = true;
            Debug.Log($"[GhostPlayer] AR Raycast HIT plane at ({placePosition.x:F2}, {placePosition.y:F2}, {placePosition.z:F2})");
        }
        else
        {
            // FALLBACK: Place 2m in front of camera at ground level
            Camera cam = Camera.main;
            if (cam == null)
            {
                Debug.LogError("[GhostPlayer] No main camera found!");
                return;
            }

            Vector3 forward = cam.transform.forward;
            forward.y = 0; // Keep horizontal
            if (forward.sqrMagnitude < 0.01f)
                forward = cam.transform.forward; // Camera looking straight down, use raw forward

            placePosition = cam.transform.position + forward.normalized * 2.0f;
            placePosition.y = cam.transform.position.y - 1.5f; // Approximate ground level
            placeRotation = Quaternion.LookRotation(forward.normalized, Vector3.up);

            Debug.Log($"[GhostPlayer] No plane found. FALLBACK: placing 2m ahead at ({placePosition.x:F2}, {placePosition.y:F2}, {placePosition.z:F2})");
        }

        // Place or reposition
        if (ghostInstance == null)
        {
            ghostInstance = Instantiate(ghostPrefab, placePosition, placeRotation);
            ghostInstance.transform.localScale = Vector3.one * ghostScale;
            ghostAnimator = ghostInstance.GetComponent<Animator>();

            if (ghostAnimator != null)
            {
                ghostAnimator.speed = 0f;
                isPlaying = false;
                Debug.Log("[GhostPlayer] Ghost placed! Animator found. Press Play to start.");
            }
            else
            {
                Debug.LogWarning("[GhostPlayer] Ghost placed but NO Animator component found on prefab!");
            }
        }
        else
        {
            ghostInstance.transform.position = placePosition;
            ghostInstance.transform.rotation = placeRotation;
            Debug.Log("[GhostPlayer] Ghost repositioned.");
        }

        isPlaced = true;
        OnPlacementChanged?.Invoke(true);
        SetPlanesVisible(false);
    }

    // ─── Public Controls (called by UIManager) ───────────────

    /// <summary>
    /// Toggle play/pause of the ghost animation.
    /// </summary>
    public void TogglePlayPause()
    {
        if (ghostAnimator == null)
        {
            Debug.LogError("[GhostPlayer] TogglePlayPause: ghostAnimator is NULL!");
            return;
        }

        // Check if Animator has a controller
        if (ghostAnimator.runtimeAnimatorController == null)
        {
            Debug.LogError("[GhostPlayer] Animator has NO Controller! Create an Animator Controller, add the animation clip, and assign it to the prefab.");
            return;
        }

        isPlaying = !isPlaying;
        ghostAnimator.speed = isPlaying ? playbackSpeed : 0f;
        Debug.Log($"[GhostPlayer] TogglePlayPause: isPlaying={isPlaying}, speed={ghostAnimator.speed}, controller={ghostAnimator.runtimeAnimatorController.name}");
        OnPlayStateChanged?.Invoke(isPlaying);
    }

    /// <summary>
    /// Play the ghost animation from the beginning.
    /// </summary>
    public void Play()
    {
        if (ghostAnimator == null) return;

        ghostAnimator.Play(0, -1, 0f); // Reset to start
        ghostAnimator.speed = playbackSpeed;
        isPlaying = true;
        OnPlayStateChanged?.Invoke(true);
    }

    /// <summary>
    /// Pause the ghost animation.
    /// </summary>
    public void Pause()
    {
        if (ghostAnimator == null) return;

        ghostAnimator.speed = 0f;
        isPlaying = false;
        OnPlayStateChanged?.Invoke(false);
    }

    /// <summary>
    /// Restart the animation from the beginning.
    /// </summary>
    public void Restart()
    {
        if (ghostAnimator == null) return;

        ghostAnimator.Play(0, -1, 0f);
        ghostAnimator.speed = playbackSpeed;
        isPlaying = true;
        OnPlayStateChanged?.Invoke(true);
    }

    /// <summary>
    /// Set playback speed (0.25x, 0.5x, 1.0x, 2.0x).
    /// </summary>
    public void SetSpeed(float speed)
    {
        playbackSpeed = Mathf.Clamp(speed, 0.25f, 3.0f);
        if (ghostAnimator != null && isPlaying)
        {
            ghostAnimator.speed = playbackSpeed;
        }
        OnSpeedChanged?.Invoke(playbackSpeed);
    }

    /// <summary>
    /// Remove the ghost from the scene and allow re-placement.
    /// </summary>
    public void ResetPlacement()
    {
        if (ghostInstance != null)
        {
            Destroy(ghostInstance);
            ghostInstance = null;
            ghostAnimator = null;
        }

        isPlaced = false;
        isPlaying = false;
        SetPlanesVisible(true);
        OnPlacementChanged?.Invoke(false);
    }

    /// <summary>
    /// Returns whether the ghost is currently placed in AR.
    /// </summary>
    public bool IsPlaced => isPlaced;

    /// <summary>
    /// Returns whether the animation is currently playing.
    /// </summary>
    public bool IsPlaying => isPlaying;

    /// <summary>
    /// Returns the current playback speed.
    /// </summary>
    public float CurrentSpeed => playbackSpeed;

    // ─── AR Plane Visibility ─────────────────────────────────

    private void SetPlanesVisible(bool visible)
    {
        if (arPlaneManager == null) return;

        foreach (var plane in arPlaneManager.trackables)
        {
            plane.gameObject.SetActive(visible);
        }

        arPlaneManager.enabled = visible;
    }
}
