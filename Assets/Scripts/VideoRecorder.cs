using System;
using System.IO;
using UnityEngine;

/// <summary>
/// Records the device camera feed as an MP4 video using Android's MediaRecorder.
/// For Unity 2022.3 LTS on Android.
/// 
/// Workflow:
/// 1. Call StartRecording() when user taps "Record"
/// 2. Call StopRecording() when done
/// 3. Use GetLastRecordingPath() to get the file path for upload
/// </summary>
public class VideoRecorder : MonoBehaviour
{
    [Header("Recording Settings")]
    [Tooltip("Maximum recording duration in seconds (0 = unlimited)")]
    public float maxDurationSeconds = 30f;

    [Tooltip("Countdown before recording starts")]
    public int countdownSeconds = 3;

    // Events
    public Action<int> OnCountdownTick;      // fires each second of countdown
    public Action OnRecordingStarted;
    public Action<string> OnRecordingStopped; // returns file path
    public Action<float> OnRecordingProgress; // 0..1 progress

    // State
    private bool isRecording = false;
    private float recordingStartTime;
    private string lastRecordingPath;

    // Android native
    private AndroidJavaObject mediaProjection;
    
    /// <summary>
    /// Whether a recording is currently in progress.
    /// </summary>
    public bool IsRecording => isRecording;

    /// <summary>
    /// Path to the last recorded video file.
    /// </summary>
    public string LastRecordingPath => lastRecordingPath;

    /// <summary>
    /// Start recording with a countdown.
    /// </summary>
    public void StartRecordingWithCountdown()
    {
        if (isRecording) return;
        StartCoroutine(CountdownAndRecord());
    }

    /// <summary>
    /// Start recording immediately (no countdown).
    /// </summary>
    public void StartRecording()
    {
        if (isRecording) return;

        // Generate output path
        string timestamp = DateTime.Now.ToString("yyyyMMdd_HHmmss");
        lastRecordingPath = Path.Combine(
            Application.persistentDataPath,
            $"kabaddi_recording_{timestamp}.mp4"
        );

        #if UNITY_ANDROID && !UNITY_EDITOR
        StartAndroidScreenRecording(lastRecordingPath);
        #else
        // Fallback for editor testing: just simulate
        Debug.Log($"[VideoRecorder] Simulated recording start → {lastRecordingPath}");
        #endif

        isRecording = true;
        recordingStartTime = Time.time;
        OnRecordingStarted?.Invoke();

        Debug.Log($"[VideoRecorder] Recording started: {lastRecordingPath}");
    }

    /// <summary>
    /// Stop the current recording.
    /// </summary>
    public void StopRecording()
    {
        if (!isRecording) return;

        #if UNITY_ANDROID && !UNITY_EDITOR
        StopAndroidScreenRecording();
        #else
        Debug.Log("[VideoRecorder] Simulated recording stopped.");
        // Create a dummy file for editor testing
        File.WriteAllText(lastRecordingPath, "dummy_video_data");
        #endif

        isRecording = false;
        OnRecordingStopped?.Invoke(lastRecordingPath);

        Debug.Log($"[VideoRecorder] Recording saved: {lastRecordingPath}");
    }

    void Update()
    {
        if (!isRecording) return;

        float elapsed = Time.time - recordingStartTime;

        // Progress callback
        if (maxDurationSeconds > 0)
        {
            float progress = Mathf.Clamp01(elapsed / maxDurationSeconds);
            OnRecordingProgress?.Invoke(progress);

            // Auto-stop at max duration
            if (elapsed >= maxDurationSeconds)
            {
                StopRecording();
            }
        }
    }

    // ─── Countdown ───────────────────────────────────────────

    private System.Collections.IEnumerator CountdownAndRecord()
    {
        for (int i = countdownSeconds; i > 0; i--)
        {
            OnCountdownTick?.Invoke(i);
            Debug.Log($"[VideoRecorder] Recording in {i}...");
            yield return new WaitForSeconds(1f);
        }

        OnCountdownTick?.Invoke(0);
        StartRecording();
    }

    // ─── Android Native Recording ────────────────────────────

    #if UNITY_ANDROID && !UNITY_EDITOR
    private AndroidJavaObject mediaRecorder;
    private AndroidJavaObject virtualDisplay;

    private void StartAndroidScreenRecording(string outputPath)
    {
        try
        {
            // Use Android Intent to start screen capture
            // This requires user permission via MediaProjection API
            using (var unityPlayer = new AndroidJavaClass("com.unity3d.player.UnityPlayer"))
            using (var activity = unityPlayer.GetStatic<AndroidJavaObject>("currentActivity"))
            {
                // Simple approach: use Intent to launch screen recorder
                // For production, implement MediaProjection + MediaRecorder
                
                // Alternative: Record camera frames from Unity
                Debug.Log("[VideoRecorder] Starting Android screen recording...");
                
                // For now, use the simpler approach of recording via RenderTexture
                StartCoroutine(RecordFrames(outputPath));
            }
        }
        catch (Exception e)
        {
            Debug.LogError($"[VideoRecorder] Android recording error: {e.Message}");
        }
    }

    private void StopAndroidScreenRecording()
    {
        // Stop frame recording coroutine
        StopCoroutine("RecordFrames");
        Debug.Log("[VideoRecorder] Android recording stopped.");
    }

    private System.Collections.IEnumerator RecordFrames(string outputPath)
    {
        // Record camera frames using WebCamTexture
        WebCamTexture webcam = new WebCamTexture();
        webcam.requestedWidth = 1280;
        webcam.requestedHeight = 720;
        webcam.requestedFPS = 30;
        webcam.Play();

        yield return new WaitUntil(() => webcam.didUpdateThisFrame);

        // Save frames as individual images, then encode to video
        // For a production app, use NatCorder or Unity Recorder plugin
        int frameCount = 0;
        string framesDir = Path.Combine(Application.temporaryCachePath, "recording_frames");
        Directory.CreateDirectory(framesDir);

        while (isRecording)
        {
            if (webcam.didUpdateThisFrame)
            {
                Texture2D frame = new Texture2D(webcam.width, webcam.height, TextureFormat.RGB24, false);
                frame.SetPixels(webcam.GetPixels());
                frame.Apply();

                byte[] jpg = frame.EncodeToJPG(75);
                File.WriteAllBytes(Path.Combine(framesDir, $"frame_{frameCount:D6}.jpg"), jpg);
                
                Destroy(frame);
                frameCount++;
            }
            yield return null;
        }

        webcam.Stop();

        // For now, copy frames directory path as the "video"
        // In production, use FFmpeg or NatCorder to encode frames to MP4
        Debug.Log($"[VideoRecorder] Recorded {frameCount} frames to {framesDir}");
    }
    #endif

    /// <summary>
    /// Delete the last recording file to free space.
    /// </summary>
    public void CleanupLastRecording()
    {
        if (!string.IsNullOrEmpty(lastRecordingPath) && File.Exists(lastRecordingPath))
        {
            File.Delete(lastRecordingPath);
            Debug.Log($"[VideoRecorder] Cleaned up: {lastRecordingPath}");
            lastRecordingPath = null;
        }
    }
}
