using System;
using System.Collections;
using UnityEngine;
using UnityEngine.UI;
using TMPro;

/// <summary>
/// Main UI controller that wires together APIClient, GhostPlayer, and VideoRecorder.
/// Manages the complete user flow: technique selection → AR playback → recording → results.
/// 
/// UI Hierarchy (create in Unity):
///   Canvas
///   ├── TechniquePanel (technique selection screen)
///   │   ├── TechniqueListContent (ScrollView content)
///   │   └── TechniqueButtonPrefab (prefab with TextMeshPro)
///   ├── ARPanel (ghost playback screen)
///   │   ├── PlacementHint ("Tap a surface to place the ghost")
///   │   ├── PlayPauseBtn, RestartBtn
///   │   ├── SpeedDropdown (0.5x, 1x, 2x)
///   │   └── RecordBtn ("Record My Attempt")
///   ├── RecordingPanel (recording overlay)
///   │   ├── CountdownText
///   │   ├── TimerText
///   │   └── StopRecordBtn
///   ├── ProcessingPanel (upload + waiting screen)
///   │   ├── StatusText
///   │   └── ProgressBar
///   ├── ResultsPanel (scores + feedback)
///   │   ├── ScoreText
///   │   ├── FeedbackText
///   │   ├── LanguageDropdown
///   │   └── RetryBtn
///   └── ConnectionPanel (server URL input)
///       ├── ServerUrlInput
///       └── ConnectBtn
/// </summary>
public class UIManager : MonoBehaviour
{
    [Header("Script References")]
    public APIClient apiClient;
    public GhostPlayer ghostPlayer;
    public VideoRecorder videoRecorder;

    [Header("Panels")]
    public GameObject connectionPanel;
    public GameObject techniquePanel;
    public GameObject arPanel;
    public GameObject recordingPanel;
    public GameObject processingPanel;
    public GameObject resultsPanel;

    [Header("Connection Panel")]
    public TMP_InputField serverUrlInput;
    public Button connectBtn;
    public TextMeshProUGUI connectionStatus;

    [Header("Technique Panel")]
    public Transform techniqueListContent;
    public GameObject techniqueButtonPrefab;

    [Header("AR Panel")]
    public GameObject placementHint;
    public Button playPauseBtn;
    public Button restartBtn;
    public TMP_Dropdown speedDropdown;
    public Button recordBtn;
    public TextMeshProUGUI playPauseBtnText;

    [Header("Recording Panel")]
    public TextMeshProUGUI countdownText;
    public TextMeshProUGUI timerText;
    public Button stopRecordBtn;

    [Header("Processing Panel")]
    public TextMeshProUGUI statusText;
    public Slider progressBar;

    [Header("Results Panel")]
    public TextMeshProUGUI scoreText;
    public TextMeshProUGUI feedbackText;
    public TMP_Dropdown languageDropdown;
    public Button retryBtn;
    public Button backToMenuBtn;

    // State
    private string currentTutorialId;
    private string currentTutorialName;
    private string currentSessionId;
    private APIClient.TutorialData[] tutorials;

    // ─── Lifecycle ───────────────────────────────────────────

    void Start()
    {
        // Wire button events
        if (connectBtn != null) connectBtn.onClick.AddListener(OnConnectClicked);
        if (playPauseBtn != null) playPauseBtn.onClick.AddListener(OnPlayPauseClicked);
        if (restartBtn != null) restartBtn.onClick.AddListener(OnRestartClicked);
        if (recordBtn != null) recordBtn.onClick.AddListener(OnRecordClicked);
        if (stopRecordBtn != null) stopRecordBtn.onClick.AddListener(OnStopRecordClicked);
        if (retryBtn != null) retryBtn.onClick.AddListener(OnRetryClicked);
        if (backToMenuBtn != null) backToMenuBtn.onClick.AddListener(OnBackToMenuClicked);

        // Speed dropdown
        if (speedDropdown != null)
        {
            speedDropdown.onValueChanged.AddListener(OnSpeedChanged);
        }

        // Ghost player events
        if (ghostPlayer != null)
        {
            ghostPlayer.OnPlacementChanged += OnGhostPlaced;
            ghostPlayer.OnPlayStateChanged += OnPlayStateChanged;
        }

        // Video recorder events
        if (videoRecorder != null)
        {
            videoRecorder.OnCountdownTick += OnCountdownTick;
            videoRecorder.OnRecordingStarted += OnRecordingStartedUI;
            videoRecorder.OnRecordingStopped += OnRecordingStoppedUI;
            videoRecorder.OnRecordingProgress += OnRecordingProgressUI;
        }

        // Start with connection panel
        ShowPanel(connectionPanel);

        // Pre-fill server URL
        if (serverUrlInput != null)
        {
            serverUrlInput.text = apiClient != null ? apiClient.serverBaseUrl : "http://192.168.43.100:8000";
        }
    }

    // ─── Panel Management ────────────────────────────────────

    private void ShowPanel(GameObject panel)
    {
        if (connectionPanel != null) connectionPanel.SetActive(panel == connectionPanel);
        if (techniquePanel != null) techniquePanel.SetActive(panel == techniquePanel);
        if (arPanel != null) arPanel.SetActive(panel == arPanel);
        if (recordingPanel != null) recordingPanel.SetActive(panel == recordingPanel);
        if (processingPanel != null) processingPanel.SetActive(panel == processingPanel);
        if (resultsPanel != null) resultsPanel.SetActive(panel == resultsPanel);
    }

    // ─── Connection Flow ─────────────────────────────────────

    private void OnConnectClicked()
    {
        if (apiClient == null || serverUrlInput == null) return;

        string url = serverUrlInput.text.Trim();
        if (string.IsNullOrEmpty(url))
        {
            SetConnectionStatus("Enter a server URL", Color.red);
            return;
        }

        apiClient.serverBaseUrl = url;
        SetConnectionStatus("Connecting...", Color.yellow);

        // Test connection by fetching tutorials
        apiClient.GetTutorials(
            onSuccess: (data) =>
            {
                tutorials = data;
                SetConnectionStatus($"Connected! {data.Length} techniques found.", Color.green);
                StartCoroutine(DelayedAction(1f, () => {
                    PopulateTechniqueList();
                    ShowPanel(techniquePanel);
                }));
            },
            onError: (err) =>
            {
                SetConnectionStatus($"Failed: {err}", Color.red);
            }
        );
    }

    private void SetConnectionStatus(string msg, Color color)
    {
        if (connectionStatus != null)
        {
            connectionStatus.text = msg;
            connectionStatus.color = color;
        }
    }

    // ─── Technique Selection ─────────────────────────────────

    private void PopulateTechniqueList()
    {
        if (techniqueListContent == null || techniqueButtonPrefab == null) return;

        // Clear existing buttons
        foreach (Transform child in techniqueListContent)
        {
            Destroy(child.gameObject);
        }

        // Create a button for each tutorial
        foreach (var tutorial in tutorials)
        {
            GameObject btnObj = Instantiate(techniqueButtonPrefab, techniqueListContent);
            
            // Set text
            var tmpText = btnObj.GetComponentInChildren<TextMeshProUGUI>();
            if (tmpText != null)
            {
                tmpText.text = $"{tutorial.name}\n<size=70%>{tutorial.description}</size>";
            }

            // Set click handler (capture tutorial in closure)
            var tutorialRef = tutorial;
            var btn = btnObj.GetComponent<Button>();
            if (btn != null)
            {
                btn.onClick.AddListener(() => OnTechniqueSelected(tutorialRef));
            }
        }
    }

    private void OnTechniqueSelected(APIClient.TutorialData tutorial)
    {
        currentTutorialId = tutorial.id;
        currentTutorialName = tutorial.name;

        Debug.Log($"[UIManager] Selected technique: {tutorial.name} ({tutorial.id})");

        // Show AR panel and set placement hint
        ShowPanel(arPanel);
        if (placementHint != null) placementHint.SetActive(true);
        if (recordBtn != null) recordBtn.interactable = false;
        if (playPauseBtn != null) playPauseBtn.interactable = false;
        if (restartBtn != null) restartBtn.interactable = false;

        // Reset ghost
        if (ghostPlayer != null) ghostPlayer.ResetPlacement();
    }

    // ─── AR Ghost Playback ───────────────────────────────────

    private void OnGhostPlaced(bool placed)
    {
        if (placementHint != null) placementHint.SetActive(!placed);
        if (playPauseBtn != null) playPauseBtn.interactable = placed;
        if (restartBtn != null) restartBtn.interactable = placed;
        if (recordBtn != null) recordBtn.interactable = placed;
    }

    private void OnPlayPauseClicked()
    {
        if (ghostPlayer != null) ghostPlayer.TogglePlayPause();
    }

    private void OnPlayStateChanged(bool playing)
    {
        if (playPauseBtnText != null)
        {
            playPauseBtnText.text = playing ? "⏸ Pause" : "▶ Play";
        }
    }

    private void OnRestartClicked()
    {
        if (ghostPlayer != null) ghostPlayer.Restart();
    }

    private void OnSpeedChanged(int index)
    {
        float[] speeds = { 0.5f, 1.0f, 1.5f, 2.0f };
        if (index >= 0 && index < speeds.Length && ghostPlayer != null)
        {
            ghostPlayer.SetSpeed(speeds[index]);
        }
    }

    // ─── Recording ───────────────────────────────────────────

    private void OnRecordClicked()
    {
        ShowPanel(recordingPanel);
        if (videoRecorder != null) videoRecorder.StartRecordingWithCountdown();
    }

    private void OnCountdownTick(int secondsLeft)
    {
        if (countdownText != null)
        {
            countdownText.text = secondsLeft > 0 ? secondsLeft.ToString() : "GO!";
            countdownText.gameObject.SetActive(secondsLeft > 0);
        }
    }

    private void OnRecordingStartedUI()
    {
        if (countdownText != null) countdownText.gameObject.SetActive(false);
        if (stopRecordBtn != null) stopRecordBtn.interactable = true;
    }

    private void OnRecordingStoppedUI(string filePath)
    {
        Debug.Log($"[UIManager] Recording saved: {filePath}");
        StartUploadAndProcess(filePath);
    }

    private void OnRecordingProgressUI(float progress)
    {
        if (timerText != null)
        {
            float elapsed = progress * videoRecorder.maxDurationSeconds;
            timerText.text = $"{elapsed:F1}s / {videoRecorder.maxDurationSeconds:F0}s";
        }
    }

    private void OnStopRecordClicked()
    {
        if (videoRecorder != null) videoRecorder.StopRecording();
    }

    // ─── Upload & Processing ─────────────────────────────────

    private void StartUploadAndProcess(string videoPath)
    {
        ShowPanel(processingPanel);
        SetStatus("Starting session...", 0.1f);

        // Step 1: Start session
        apiClient.StartSession(currentTutorialId,
            onSuccess: (session) =>
            {
                currentSessionId = session.session_id;
                SetStatus("Uploading video...", 0.2f);

                // Step 2: Upload video
                apiClient.UploadVideo(currentSessionId, videoPath,
                    onSuccess: (upload) =>
                    {
                        SetStatus("Triggering analysis...", 0.4f);

                        // Step 3: Trigger assessment
                        apiClient.TriggerAssessment(currentSessionId,
                            onSuccess: (json) =>
                            {
                                SetStatus("Processing... This may take a minute.", 0.5f);

                                // Step 4: Poll for completion
                                apiClient.PollStatus(currentSessionId,
                                    onUpdate: (s) => SetStatus($"Status: {s.status}", 0.6f),
                                    onComplete: (s) =>
                                    {
                                        SetStatus("Fetching results...", 0.9f);
                                        FetchResults();
                                    },
                                    onError: (err) => ShowError(err)
                                );
                            },
                            onError: ShowError);
                    },
                    onError: ShowError);
            },
            onError: ShowError);
    }

    private void FetchResults()
    {
        apiClient.GetResults(currentSessionId,
            onSuccess: (json) =>
            {
                Debug.Log($"[UIManager] Results: {json}");
                DisplayResults(json);
            },
            onError: ShowError);
    }

    private void SetStatus(string msg, float progress)
    {
        if (statusText != null) statusText.text = msg;
        if (progressBar != null) progressBar.value = progress;
    }

    private void ShowError(string error)
    {
        SetStatus($"Error: {error}", 0f);
        Debug.LogError($"[UIManager] {error}");
    }

    // ─── Results Display ─────────────────────────────────────

    private void DisplayResults(string rawJson)
    {
        ShowPanel(resultsPanel);

        // Parse scores from the raw JSON
        // The ResultsView returns: { scores: {...}, error_metrics: {...}, feedback: {...} }
        try
        {
            var result = JsonUtility.FromJson<ResultsJSON>(rawJson);

            if (scoreText != null)
            {
                scoreText.text = $"Overall Score: {result.overall_score:F1}/100\n" +
                                 $"Structural: {result.structural_score:F1}/100\n" +
                                 $"Temporal: {result.temporal_score:F1}/100";
            }

            if (feedbackText != null)
            {
                feedbackText.text = !string.IsNullOrEmpty(result.feedback_text)
                    ? result.feedback_text
                    : "No detailed feedback available.";
            }
        }
        catch (Exception e)
        {
            // Fallback: show raw JSON
            if (scoreText != null) scoreText.text = "Results received";
            if (feedbackText != null) feedbackText.text = rawJson;
            Debug.LogWarning($"[UIManager] JSON parse issue: {e.Message}");
        }
    }

    [Serializable]
    private class ResultsJSON
    {
        public float overall_score;
        public float structural_score;
        public float temporal_score;
        public string feedback_text;
    }

    // ─── Retry / Back ────────────────────────────────────────

    private void OnRetryClicked()
    {
        // Go back to AR panel for another attempt
        ShowPanel(arPanel);
        if (ghostPlayer != null) ghostPlayer.Restart();
    }

    private void OnBackToMenuClicked()
    {
        if (ghostPlayer != null) ghostPlayer.ResetPlacement();
        ShowPanel(techniquePanel);
    }

    // ─── Utility ─────────────────────────────────────────────

    private IEnumerator DelayedAction(float delay, Action action)
    {
        yield return new WaitForSeconds(delay);
        action?.Invoke();
    }
}
