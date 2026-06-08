using UnityEngine;
using TMPro;
using System;

public class VHSTime : MonoBehaviour
{
    [SerializeField] private TextMeshProUGUI timeText;
    [SerializeField] private bool startOnAwake = true;

    private double elapsedSeconds;
    private bool isRecording;

    private void Awake()
    {
        if (timeText == null)
        {
            timeText = GetComponentInChildren<TextMeshProUGUI>();
            if (timeText == null)
                Debug.LogWarning("VHSTime: No TextMeshProUGUI assigned or found in children.");
        }
    }

    private void Start()
    {
        ResetRecording();
        if (startOnAwake)
            StartRecording();
        else
            UpdateDisplay();
    }

    private void Update()
    {
        if (!isRecording) return;
        elapsedSeconds += Time.deltaTime;
        UpdateDisplay();
    }

    private void UpdateDisplay()
    {
        if (timeText == null) return;
        var ts = TimeSpan.FromSeconds(elapsedSeconds);
        int hours = (int)ts.TotalHours;
        int minutes = ts.Minutes;
        int seconds = ts.Seconds;
        timeText.text = string.Format("{0:D2}:{1:D2}:{2:D2}", hours, minutes, seconds);
    }

    // Public controls
    public void StartRecording()
    {
        isRecording = true;
    }

    public void StopRecording()
    {
        isRecording = false;
    }

    public void ResetRecording()
    {
        elapsedSeconds = 0.0;
        UpdateDisplay();
    }

    public void SetTimeSeconds(double seconds)
    {
        elapsedSeconds = Math.Max(0.0, seconds);
        UpdateDisplay();
    }
}
