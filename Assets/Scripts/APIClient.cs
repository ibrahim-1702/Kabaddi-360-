using System;
using System.Collections;
using System.Text;
using UnityEngine;
using UnityEngine.Networking;

/// <summary>
/// REST API client for communicating with the Kabaddi Ghost Trainer Django backend.
/// Attach to a persistent GameObject (e.g., GameManager).
/// </summary>
public class APIClient : MonoBehaviour
{
    [Header("Server Configuration")]
    [Tooltip("Base URL of the Django server, e.g., http://192.168.43.100:8000")]
    public string serverBaseUrl = "http://192.168.43.100:8000";

    private string ApiUrl => serverBaseUrl.TrimEnd('/') + "/api/";

    // ─── Data Classes ────────────────────────────────────────

    [Serializable]
    public class TutorialData
    {
        public string id;
        public string name;
        public string description;
        public bool has_animation;
    }

    [Serializable]
    public class TutorialListResponse
    {
        public TutorialData[] tutorials;
    }

    [Serializable]
    public class SessionResponse
    {
        public string session_id;
        public string tutorial;
        public string status;
    }

    [Serializable]
    public class UploadResponse
    {
        public string session_id;
        public string status;
        public long file_size;
    }

    [Serializable]
    public class StatusResponse
    {
        public string session_id;
        public string status;
        public string error_message;
    }

    [Serializable]
    public class ResultsResponse
    {
        public string session_id;
        public string tutorial;
        public string scores_raw;      // raw JSON string of scores
        public string feedback_text;
        public string audio_path;
    }

    // ─── Public API ──────────────────────────────────────────

    /// <summary>
    /// Fetch all available tutorials from the server.
    /// </summary>
    public void GetTutorials(Action<TutorialData[]> onSuccess, Action<string> onError)
    {
        StartCoroutine(GetRequest(ApiUrl + "tutorials/", (json) =>
        {
            var response = JsonUtility.FromJson<TutorialListResponse>(json);
            onSuccess?.Invoke(response.tutorials);
        }, onError));
    }

    /// <summary>
    /// Start a new training session for a given tutorial.
    /// </summary>
    public void StartSession(string tutorialId, Action<SessionResponse> onSuccess, Action<string> onError)
    {
        string body = $"{{\"tutorial_id\":\"{tutorialId}\"}}";
        StartCoroutine(PostRequest(ApiUrl + "session/start/", body, (json) =>
        {
            var response = JsonUtility.FromJson<SessionResponse>(json);
            onSuccess?.Invoke(response);
        }, onError));
    }

    /// <summary>
    /// Upload a recorded video file for a session.
    /// </summary>
    public void UploadVideo(string sessionId, string videoFilePath, Action<UploadResponse> onSuccess, Action<string> onError)
    {
        StartCoroutine(UploadFileRequest(sessionId, videoFilePath, onSuccess, onError));
    }

    /// <summary>
    /// Trigger the assessment pipeline for a session.
    /// </summary>
    public void TriggerAssessment(string sessionId, Action<string> onSuccess, Action<string> onError)
    {
        StartCoroutine(PostRequest(ApiUrl + $"session/{sessionId}/assess/", "{}", (json) =>
        {
            onSuccess?.Invoke(json);
        }, onError));
    }

    /// <summary>
    /// Poll session status until processing is complete.
    /// </summary>
    public void PollStatus(string sessionId, Action<StatusResponse> onUpdate, Action<StatusResponse> onComplete, Action<string> onError)
    {
        StartCoroutine(PollStatusCoroutine(sessionId, onUpdate, onComplete, onError));
    }

    /// <summary>
    /// Fetch final results for a completed session.
    /// </summary>
    public void GetResults(string sessionId, Action<string> onSuccess, Action<string> onError)
    {
        StartCoroutine(GetRequest(ApiUrl + $"session/{sessionId}/results/", onSuccess, onError));
    }

    /// <summary>
    /// Download the FBX animation file for a tutorial.
    /// Saves to Application.persistentDataPath and returns the local path.
    /// </summary>
    public void DownloadAnimation(string tutorialId, string tutorialName, Action<string> onSuccess, Action<string> onError)
    {
        StartCoroutine(DownloadFile(
            ApiUrl + $"tutorials/{tutorialId}/animation/",
            $"{tutorialName}_ghost.fbx",
            onSuccess, onError
        ));
    }

    // ─── Internal Coroutines ─────────────────────────────────

    private IEnumerator GetRequest(string url, Action<string> onSuccess, Action<string> onError)
    {
        using (var request = UnityWebRequest.Get(url))
        {
            request.timeout = 30;
            yield return request.SendWebRequest();

            if (request.result != UnityWebRequest.Result.Success)
            {
                onError?.Invoke($"GET {url}: {request.error}");
            }
            else
            {
                onSuccess?.Invoke(request.downloadHandler.text);
            }
        }
    }

    private IEnumerator PostRequest(string url, string jsonBody, Action<string> onSuccess, Action<string> onError)
    {
        using (var request = new UnityWebRequest(url, "POST"))
        {
            byte[] bodyRaw = Encoding.UTF8.GetBytes(jsonBody);
            request.uploadHandler = new UploadHandlerRaw(bodyRaw);
            request.downloadHandler = new DownloadHandlerBuffer();
            request.SetRequestHeader("Content-Type", "application/json");
            request.timeout = 30;

            yield return request.SendWebRequest();

            if (request.result != UnityWebRequest.Result.Success)
            {
                onError?.Invoke($"POST {url}: {request.error}");
            }
            else
            {
                onSuccess?.Invoke(request.downloadHandler.text);
            }
        }
    }

    private IEnumerator UploadFileRequest(string sessionId, string filePath, Action<UploadResponse> onSuccess, Action<string> onError)
    {
        byte[] videoData = System.IO.File.ReadAllBytes(filePath);

        WWWForm form = new WWWForm();
        form.AddBinaryData("video", videoData, "recording.mp4", "video/mp4");

        string url = ApiUrl + $"session/{sessionId}/upload-video/";
        using (var request = UnityWebRequest.Post(url, form))
        {
            request.timeout = 120; // Large file upload
            yield return request.SendWebRequest();

            if (request.result != UnityWebRequest.Result.Success)
            {
                onError?.Invoke($"Upload failed: {request.error}");
            }
            else
            {
                var response = JsonUtility.FromJson<UploadResponse>(request.downloadHandler.text);
                onSuccess?.Invoke(response);
            }
        }
    }

    private IEnumerator PollStatusCoroutine(string sessionId, Action<StatusResponse> onUpdate, Action<StatusResponse> onComplete, Action<string> onError)
    {
        string url = ApiUrl + $"session/{sessionId}/status/";
        int maxPolls = 120; // 10 minutes max (5s intervals)

        for (int i = 0; i < maxPolls; i++)
        {
            using (var request = UnityWebRequest.Get(url))
            {
                request.timeout = 10;
                yield return request.SendWebRequest();

                if (request.result != UnityWebRequest.Result.Success)
                {
                    onError?.Invoke($"Poll failed: {request.error}");
                    yield break;
                }

                var status = JsonUtility.FromJson<StatusResponse>(request.downloadHandler.text);
                onUpdate?.Invoke(status);

                if (status.status == "feedback_generated" || status.status == "scoring_complete")
                {
                    onComplete?.Invoke(status);
                    yield break;
                }

                if (status.status == "failed")
                {
                    onError?.Invoke($"Pipeline failed: {status.error_message}");
                    yield break;
                }
            }

            yield return new WaitForSeconds(5f);
        }

        onError?.Invoke("Polling timed out after 10 minutes");
    }

    private IEnumerator DownloadFile(string url, string fileName, Action<string> onSuccess, Action<string> onError)
    {
        string savePath = System.IO.Path.Combine(Application.persistentDataPath, fileName);

        using (var request = UnityWebRequest.Get(url))
        {
            request.downloadHandler = new DownloadHandlerFile(savePath);
            request.timeout = 60;
            yield return request.SendWebRequest();

            if (request.result != UnityWebRequest.Result.Success)
            {
                onError?.Invoke($"Download failed: {request.error}");
            }
            else
            {
                onSuccess?.Invoke(savePath);
            }
        }
    }
}
