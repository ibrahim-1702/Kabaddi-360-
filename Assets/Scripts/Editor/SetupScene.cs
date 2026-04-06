using UnityEngine;
using UnityEditor;
using UnityEngine.UI;
using TMPro;
using UnityEngine.XR.ARFoundation;
using Unity.XR.CoreUtils;

/// <summary>
/// One-click scene setup for Kabaddi Ghost Trainer.
/// Run from Unity menu: Kabaddi → Setup Full Scene
/// Creates all UI panels, buttons, text fields, and wires scripts automatically.
/// </summary>
public class SetupScene
{
    [MenuItem("Kabaddi/Setup Full Scene")]
    public static void Setup()
    {
        // ── 1. AR Session ────────────────────────────────────
        var arSession = new GameObject("AR Session");
        arSession.AddComponent<ARSession>();

        // ── 2. XR Origin (AR Foundation 5.x) ─────────────────
        var arOrigin = new GameObject("XR Origin");
        var xrOrigin = arOrigin.AddComponent<XROrigin>();
        var raycastMgr = arOrigin.AddComponent<ARRaycastManager>();
        var planeMgr = arOrigin.AddComponent<ARPlaneManager>();

        // AR Camera
        var arCam = new GameObject("AR Camera");
        arCam.transform.SetParent(arOrigin.transform);
        arCam.tag = "MainCamera";
        var cam = arCam.AddComponent<Camera>();
        cam.clearFlags = CameraClearFlags.SolidColor;
        cam.backgroundColor = Color.black;
        arCam.AddComponent<ARCameraManager>();
        arCam.AddComponent<ARCameraBackground>();
        xrOrigin.Camera = cam;

        // GhostPlayer on AR Origin
        var ghostPlayer = arOrigin.AddComponent<GhostPlayer>();
        ghostPlayer.arRaycastManager = raycastMgr;
        ghostPlayer.arPlaneManager = planeMgr;

        // ── 3. GameManager ───────────────────────────────────
        var gm = new GameObject("GameManager");
        var apiClient = gm.AddComponent<APIClient>();
        var recorder = gm.AddComponent<VideoRecorder>();
        recorder.maxDurationSeconds = 30;
        recorder.countdownSeconds = 3;
        var uiMgr = gm.AddComponent<UIManager>();

        // ── 4. Canvas ────────────────────────────────────────
        var canvas = CreateCanvas();

        // ── 5. Panels + UI Elements ──────────────────────────

        // --- ConnectionPanel ---
        var connPanel = CreatePanel(canvas, "ConnectionPanel", true);
        var serverInput = CreateInputField(connPanel, "ServerUrlInput", "http://192.168.43.100:8000");
        var connectBtn = CreateButton(connPanel, "ConnectBtn", "Connect to Server", new Vector2(0, -60));
        var connStatus = CreateText(connPanel, "ConnectionStatus", "Enter server URL and tap Connect", 20, new Vector2(0, -120));

        // --- TechniquePanel ---
        var techPanel = CreatePanel(canvas, "TechniquePanel", false);
        CreateText(techPanel, "TechniqueTitle", "Select Technique", 30, new Vector2(0, 140));
        var scrollView = CreateScrollView(techPanel, "TechniqueScrollView");
        var listContent = scrollView.transform.Find("Viewport/Content").gameObject;
        listContent.name = "TechniqueListContent";
        var vlg = listContent.AddComponent<VerticalLayoutGroup>();
        vlg.childControlWidth = true;
        vlg.childForceExpandWidth = true;
        vlg.spacing = 8;
        var csf = listContent.AddComponent<ContentSizeFitter>();
        csf.verticalFit = ContentSizeFitter.FitMode.PreferredSize;

        // TechniqueButtonPrefab
        var btnPrefab = CreateButtonPrefab();

        // --- ARPanel ---
        var arPanel = CreatePanel(canvas, "ARPanel", false);
        var placementHint = CreateText(arPanel, "PlacementHint", "Tap a surface to place the ghost", 24, new Vector2(0, 100));
        var playPauseBtn = CreateButton(arPanel, "PlayPauseBtn", "Play", new Vector2(-120, -100));
        var playPauseTxt = playPauseBtn.GetComponentInChildren<TextMeshProUGUI>();
        var restartBtn = CreateButton(arPanel, "RestartBtn", "Restart", new Vector2(0, -100));
        var speedDd = CreateDropdown(arPanel, "SpeedDropdown", new[] { "0.5x", "1x", "1.5x", "2x" }, 1, new Vector2(120, -100));
        var recordBtn = CreateButton(arPanel, "RecordBtn", "Record My Attempt", new Vector2(0, -180));
        recordBtn.GetComponent<RectTransform>().sizeDelta = new Vector2(300, 50);

        // --- RecordingPanel ---
        var recPanel = CreatePanel(canvas, "RecordingPanel", false);
        var countdownTxt = CreateText(recPanel, "CountdownText", "3", 80, new Vector2(0, 40));
        var timerTxt = CreateText(recPanel, "TimerText", "0.0s / 30s", 24, new Vector2(0, -60));
        var stopRecBtn = CreateButton(recPanel, "StopRecordBtn", "Stop Recording", new Vector2(0, -140));

        // --- ProcessingPanel ---
        var procPanel = CreatePanel(canvas, "ProcessingPanel", false);
        var statusTxt = CreateText(procPanel, "StatusText", "Processing...", 24, new Vector2(0, 40));
        var slider = CreateSlider(procPanel, "ProgressBar", new Vector2(0, -40));

        // --- ResultsPanel ---
        var resPanel = CreatePanel(canvas, "ResultsPanel", false);
        var scoreTxt = CreateText(resPanel, "ScoreText", "Score: --", 28, new Vector2(0, 120));
        var feedbackTxt = CreateText(resPanel, "FeedbackText", "Feedback will appear here", 20, new Vector2(0, 20));
        feedbackTxt.GetComponent<RectTransform>().sizeDelta = new Vector2(500, 150);
        var langDd = CreateDropdown(resPanel, "LanguageDropdown", new[] { "English", "Hindi", "Tamil", "Telugu", "Kannada" }, 0, new Vector2(0, -80));
        var retryBtn = CreateButton(resPanel, "RetryBtn", "Try Again", new Vector2(-100, -160));
        var backBtn = CreateButton(resPanel, "BackToMenuBtn", "Back to Menu", new Vector2(100, -160));

        // ── 6. Wire UIManager ────────────────────────────────
        uiMgr.apiClient = apiClient;
        uiMgr.ghostPlayer = ghostPlayer;
        uiMgr.videoRecorder = recorder;

        uiMgr.connectionPanel = connPanel;
        uiMgr.techniquePanel = techPanel;
        uiMgr.arPanel = arPanel;
        uiMgr.recordingPanel = recPanel;
        uiMgr.processingPanel = procPanel;
        uiMgr.resultsPanel = resPanel;

        uiMgr.serverUrlInput = serverInput.GetComponent<TMP_InputField>();
        uiMgr.connectBtn = connectBtn.GetComponent<Button>();
        uiMgr.connectionStatus = connStatus;

        uiMgr.techniqueListContent = listContent.transform;
        uiMgr.techniqueButtonPrefab = btnPrefab;

        uiMgr.placementHint = placementHint.gameObject;
        uiMgr.playPauseBtn = playPauseBtn.GetComponent<Button>();
        uiMgr.restartBtn = restartBtn.GetComponent<Button>();
        uiMgr.speedDropdown = speedDd;
        uiMgr.recordBtn = recordBtn.GetComponent<Button>();
        uiMgr.playPauseBtnText = playPauseTxt;

        uiMgr.countdownText = countdownTxt;
        uiMgr.timerText = timerTxt;
        uiMgr.stopRecordBtn = stopRecBtn.GetComponent<Button>();

        uiMgr.statusText = statusTxt;
        uiMgr.progressBar = slider.GetComponent<Slider>();

        uiMgr.scoreText = scoreTxt;
        uiMgr.feedbackText = feedbackTxt;
        uiMgr.languageDropdown = langDd;
        uiMgr.retryBtn = retryBtn.GetComponent<Button>();
        uiMgr.backToMenuBtn = backBtn.GetComponent<Button>();

        // ── 7. Delete default camera ─────────────────────────
        var defaultCam = GameObject.Find("Main Camera");
        if (defaultCam != null && defaultCam != arCam)
            Object.DestroyImmediate(defaultCam);

        Debug.Log("[Kabaddi] Full scene setup complete! Assign ghost prefab to GhostPlayer → Ghost Prefab.");
        EditorUtility.DisplayDialog("Setup Complete",
            "Scene is ready!\n\n" +
            "Next steps:\n" +
            "1. Drag your FBX character prefab into GhostPlayer → Ghost Prefab\n" +
            "2. Set your laptop IP in APIClient → Server Base Url\n" +
            "3. Build & Run on Android",
            "OK");
    }

    // ── Helper Methods ───────────────────────────────────────

    static GameObject CreateCanvas()
    {
        var canvasObj = new GameObject("Canvas");
        var c = canvasObj.AddComponent<Canvas>();
        c.renderMode = RenderMode.ScreenSpaceOverlay;
        canvasObj.AddComponent<CanvasScaler>().uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
        canvasObj.GetComponent<CanvasScaler>().referenceResolution = new Vector2(1080, 1920);
        canvasObj.AddComponent<GraphicRaycaster>();

        // EventSystem
        if (Object.FindObjectOfType<UnityEngine.EventSystems.EventSystem>() == null)
        {
            var es = new GameObject("EventSystem");
            es.AddComponent<UnityEngine.EventSystems.EventSystem>();
            es.AddComponent<UnityEngine.EventSystems.StandaloneInputModule>();
        }

        return canvasObj;
    }

    static GameObject CreatePanel(GameObject parent, string name, bool active)
    {
        var panel = new GameObject(name, typeof(RectTransform), typeof(CanvasRenderer), typeof(Image));
        panel.transform.SetParent(parent.transform, false);
        var rt = panel.GetComponent<RectTransform>();
        rt.anchorMin = Vector2.zero;
        rt.anchorMax = Vector2.one;
        rt.offsetMin = Vector2.zero;
        rt.offsetMax = Vector2.zero;
        var img = panel.GetComponent<Image>();
        img.color = new Color(0.12f, 0.12f, 0.15f, 0.95f); // dark semi-transparent
        panel.SetActive(active);
        return panel;
    }

    static TextMeshProUGUI CreateText(GameObject parent, string name, string text, int fontSize, Vector2 pos)
    {
        var obj = new GameObject(name, typeof(RectTransform), typeof(TextMeshProUGUI));
        obj.transform.SetParent(parent.transform, false);
        var rt = obj.GetComponent<RectTransform>();
        rt.anchoredPosition = pos;
        rt.sizeDelta = new Vector2(500, 60);
        var tmp = obj.GetComponent<TextMeshProUGUI>();
        tmp.text = text;
        tmp.fontSize = fontSize;
        tmp.alignment = TextAlignmentOptions.Center;
        tmp.color = Color.white;
        return tmp;
    }

    static GameObject CreateButton(GameObject parent, string name, string label, Vector2 pos)
    {
        var obj = new GameObject(name, typeof(RectTransform), typeof(CanvasRenderer), typeof(Image), typeof(Button));
        obj.transform.SetParent(parent.transform, false);
        var rt = obj.GetComponent<RectTransform>();
        rt.anchoredPosition = pos;
        rt.sizeDelta = new Vector2(200, 50);
        obj.GetComponent<Image>().color = new Color(0.2f, 0.6f, 1f, 1f); // blue

        var txtObj = new GameObject("Text", typeof(RectTransform), typeof(TextMeshProUGUI));
        txtObj.transform.SetParent(obj.transform, false);
        var trt = txtObj.GetComponent<RectTransform>();
        trt.anchorMin = Vector2.zero;
        trt.anchorMax = Vector2.one;
        trt.offsetMin = Vector2.zero;
        trt.offsetMax = Vector2.zero;
        var tmp = txtObj.GetComponent<TextMeshProUGUI>();
        tmp.text = label;
        tmp.fontSize = 20;
        tmp.alignment = TextAlignmentOptions.Center;
        tmp.color = Color.white;

        return obj;
    }

    static GameObject CreateInputField(GameObject parent, string name, string defaultText)
    {
        // Use TMP_DefaultControls to create a proper InputField
        var obj = new GameObject(name, typeof(RectTransform), typeof(CanvasRenderer), typeof(Image), typeof(TMP_InputField));
        obj.transform.SetParent(parent.transform, false);
        var rt = obj.GetComponent<RectTransform>();
        rt.anchoredPosition = new Vector2(0, 40);
        rt.sizeDelta = new Vector2(500, 50);
        obj.GetComponent<Image>().color = new Color(0.25f, 0.25f, 0.3f, 1f);

        // Text area
        var textArea = new GameObject("Text Area", typeof(RectTransform), typeof(RectMask2D));
        textArea.transform.SetParent(obj.transform, false);
        var taRt = textArea.GetComponent<RectTransform>();
        taRt.anchorMin = Vector2.zero;
        taRt.anchorMax = Vector2.one;
        taRt.offsetMin = new Vector2(10, 0);
        taRt.offsetMax = new Vector2(-10, 0);

        // Input text
        var textObj = new GameObject("Text", typeof(RectTransform), typeof(TextMeshProUGUI));
        textObj.transform.SetParent(textArea.transform, false);
        var txtRt = textObj.GetComponent<RectTransform>();
        txtRt.anchorMin = Vector2.zero;
        txtRt.anchorMax = Vector2.one;
        txtRt.offsetMin = Vector2.zero;
        txtRt.offsetMax = Vector2.zero;
        var tmp = textObj.GetComponent<TextMeshProUGUI>();
        tmp.text = defaultText;
        tmp.fontSize = 18;
        tmp.color = Color.white;

        // Placeholder
        var phObj = new GameObject("Placeholder", typeof(RectTransform), typeof(TextMeshProUGUI));
        phObj.transform.SetParent(textArea.transform, false);
        var phRt = phObj.GetComponent<RectTransform>();
        phRt.anchorMin = Vector2.zero;
        phRt.anchorMax = Vector2.one;
        phRt.offsetMin = Vector2.zero;
        phRt.offsetMax = Vector2.zero;
        var phTmp = phObj.GetComponent<TextMeshProUGUI>();
        phTmp.text = "Enter server URL...";
        phTmp.fontSize = 18;
        phTmp.fontStyle = FontStyles.Italic;
        phTmp.color = new Color(1, 1, 1, 0.4f);

        // Wire InputField
        var input = obj.GetComponent<TMP_InputField>();
        input.textViewport = taRt;
        input.textComponent = tmp;
        input.placeholder = phTmp;
        input.text = defaultText;

        return obj;
    }

    static GameObject CreateScrollView(GameObject parent, string name)
    {
        var sv = new GameObject(name, typeof(RectTransform), typeof(CanvasRenderer), typeof(Image), typeof(ScrollRect));
        sv.transform.SetParent(parent.transform, false);
        var rt = sv.GetComponent<RectTransform>();
        rt.anchoredPosition = new Vector2(0, -20);
        rt.sizeDelta = new Vector2(500, 300);
        sv.GetComponent<Image>().color = new Color(0.15f, 0.15f, 0.2f, 0.8f);

        var viewport = new GameObject("Viewport", typeof(RectTransform), typeof(CanvasRenderer), typeof(Image), typeof(Mask));
        viewport.transform.SetParent(sv.transform, false);
        var vrt = viewport.GetComponent<RectTransform>();
        vrt.anchorMin = Vector2.zero;
        vrt.anchorMax = Vector2.one;
        vrt.offsetMin = Vector2.zero;
        vrt.offsetMax = Vector2.zero;
        viewport.GetComponent<Image>().color = new Color(1, 1, 1, 0.01f);
        viewport.GetComponent<Mask>().showMaskGraphic = false;

        var content = new GameObject("Content", typeof(RectTransform));
        content.transform.SetParent(viewport.transform, false);
        var crt = content.GetComponent<RectTransform>();
        crt.anchorMin = new Vector2(0, 1);
        crt.anchorMax = new Vector2(1, 1);
        crt.pivot = new Vector2(0.5f, 1);
        crt.sizeDelta = new Vector2(0, 600);

        var scroll = sv.GetComponent<ScrollRect>();
        scroll.viewport = vrt;
        scroll.content = crt;
        scroll.horizontal = false;
        scroll.vertical = true;

        return sv;
    }

    static TMP_Dropdown CreateDropdown(GameObject parent, string name, string[] options, int defaultIndex, Vector2 pos)
    {
        var obj = new GameObject(name, typeof(RectTransform), typeof(CanvasRenderer), typeof(Image), typeof(TMP_Dropdown));
        obj.transform.SetParent(parent.transform, false);
        var rt = obj.GetComponent<RectTransform>();
        rt.anchoredPosition = pos;
        rt.sizeDelta = new Vector2(160, 40);
        obj.GetComponent<Image>().color = new Color(0.25f, 0.25f, 0.3f, 1f);

        // Label
        var label = new GameObject("Label", typeof(RectTransform), typeof(TextMeshProUGUI));
        label.transform.SetParent(obj.transform, false);
        var lrt = label.GetComponent<RectTransform>();
        lrt.anchorMin = Vector2.zero;
        lrt.anchorMax = Vector2.one;
        lrt.offsetMin = new Vector2(10, 0);
        lrt.offsetMax = new Vector2(-25, 0);
        var ltmp = label.GetComponent<TextMeshProUGUI>();
        ltmp.fontSize = 16;
        ltmp.color = Color.white;
        ltmp.alignment = TextAlignmentOptions.Left;

        var dd = obj.GetComponent<TMP_Dropdown>();
        dd.captionText = ltmp;

        // Template (minimal)
        var template = new GameObject("Template", typeof(RectTransform), typeof(CanvasRenderer), typeof(Image), typeof(ScrollRect));
        template.transform.SetParent(obj.transform, false);
        var trt = template.GetComponent<RectTransform>();
        trt.anchoredPosition = new Vector2(0, -40);
        trt.sizeDelta = new Vector2(160, 150);
        template.GetComponent<Image>().color = new Color(0.2f, 0.2f, 0.25f, 1f);
        template.SetActive(false);

        var viewport = new GameObject("Viewport", typeof(RectTransform), typeof(Mask), typeof(Image));
        viewport.transform.SetParent(template.transform, false);
        var vprt = viewport.GetComponent<RectTransform>();
        vprt.anchorMin = Vector2.zero;
        vprt.anchorMax = Vector2.one;
        vprt.offsetMin = Vector2.zero;
        vprt.offsetMax = Vector2.zero;
        viewport.GetComponent<Image>().color = Color.white;
        viewport.GetComponent<Mask>().showMaskGraphic = false;

        var content = new GameObject("Content", typeof(RectTransform));
        content.transform.SetParent(viewport.transform, false);
        var ccrt = content.GetComponent<RectTransform>();
        ccrt.anchorMin = new Vector2(0, 1);
        ccrt.anchorMax = new Vector2(1, 1);
        ccrt.pivot = new Vector2(0.5f, 1);

        var item = new GameObject("Item", typeof(RectTransform), typeof(Toggle));
        item.transform.SetParent(content.transform, false);
        var irt = item.GetComponent<RectTransform>();
        irt.sizeDelta = new Vector2(0, 30);

        var itemLabel = new GameObject("Item Label", typeof(RectTransform), typeof(TextMeshProUGUI));
        itemLabel.transform.SetParent(item.transform, false);
        var ilrt = itemLabel.GetComponent<RectTransform>();
        ilrt.anchorMin = Vector2.zero;
        ilrt.anchorMax = Vector2.one;
        ilrt.offsetMin = Vector2.zero;
        ilrt.offsetMax = Vector2.zero;
        var iltmp = itemLabel.GetComponent<TextMeshProUGUI>();
        iltmp.fontSize = 16;
        iltmp.color = Color.white;

        dd.itemText = iltmp;

        template.GetComponent<ScrollRect>().viewport = vprt;
        template.GetComponent<ScrollRect>().content = ccrt;

        dd.template = trt;

        // Add options
        dd.options.Clear();
        foreach (var opt in options)
            dd.options.Add(new TMP_Dropdown.OptionData(opt));
        dd.value = defaultIndex;
        dd.RefreshShownValue();

        return dd;
    }

    static Slider CreateSlider(GameObject parent, string name, Vector2 pos)
    {
        var obj = new GameObject(name, typeof(RectTransform), typeof(Slider));
        obj.transform.SetParent(parent.transform, false);
        var rt = obj.GetComponent<RectTransform>();
        rt.anchoredPosition = pos;
        rt.sizeDelta = new Vector2(400, 20);

        // Background
        var bg = new GameObject("Background", typeof(RectTransform), typeof(CanvasRenderer), typeof(Image));
        bg.transform.SetParent(obj.transform, false);
        var bgrt = bg.GetComponent<RectTransform>();
        bgrt.anchorMin = Vector2.zero;
        bgrt.anchorMax = Vector2.one;
        bgrt.offsetMin = Vector2.zero;
        bgrt.offsetMax = Vector2.zero;
        bg.GetComponent<Image>().color = new Color(0.3f, 0.3f, 0.35f, 1f);

        // Fill Area
        var fillArea = new GameObject("Fill Area", typeof(RectTransform));
        fillArea.transform.SetParent(obj.transform, false);
        var fart = fillArea.GetComponent<RectTransform>();
        fart.anchorMin = Vector2.zero;
        fart.anchorMax = Vector2.one;
        fart.offsetMin = Vector2.zero;
        fart.offsetMax = Vector2.zero;

        var fill = new GameObject("Fill", typeof(RectTransform), typeof(CanvasRenderer), typeof(Image));
        fill.transform.SetParent(fillArea.transform, false);
        var frt = fill.GetComponent<RectTransform>();
        frt.anchorMin = Vector2.zero;
        frt.anchorMax = new Vector2(0, 1);
        frt.offsetMin = Vector2.zero;
        frt.offsetMax = Vector2.zero;
        fill.GetComponent<Image>().color = new Color(0.2f, 0.7f, 1f, 1f);

        var slider = obj.GetComponent<Slider>();
        slider.fillRect = frt;
        slider.minValue = 0;
        slider.maxValue = 1;
        slider.value = 0;
        slider.interactable = false;

        return slider;
    }

    static GameObject CreateButtonPrefab()
    {
        var obj = new GameObject("TechniqueButtonPrefab", typeof(RectTransform), typeof(CanvasRenderer), typeof(Image), typeof(Button));
        var rt = obj.GetComponent<RectTransform>();
        rt.sizeDelta = new Vector2(480, 80);
        obj.GetComponent<Image>().color = new Color(0.2f, 0.5f, 0.8f, 1f);

        var txt = new GameObject("Text", typeof(RectTransform), typeof(TextMeshProUGUI));
        txt.transform.SetParent(obj.transform, false);
        var trt = txt.GetComponent<RectTransform>();
        trt.anchorMin = Vector2.zero;
        trt.anchorMax = Vector2.one;
        trt.offsetMin = new Vector2(10, 5);
        trt.offsetMax = new Vector2(-10, -5);
        var tmp = txt.GetComponent<TextMeshProUGUI>();
        tmp.text = "Technique Name";
        tmp.fontSize = 20;
        tmp.alignment = TextAlignmentOptions.Left;
        tmp.color = Color.white;

        // Save as prefab
        string prefabDir = "Assets/Prefabs";
        if (!AssetDatabase.IsValidFolder(prefabDir))
            AssetDatabase.CreateFolder("Assets", "Prefabs");

        string path = prefabDir + "/TechniqueButtonPrefab.prefab";
        var prefab = PrefabUtility.SaveAsPrefabAsset(obj, path);
        Object.DestroyImmediate(obj);

        Debug.Log($"[Kabaddi] Button prefab saved: {path}");
        return prefab;
    }
}
