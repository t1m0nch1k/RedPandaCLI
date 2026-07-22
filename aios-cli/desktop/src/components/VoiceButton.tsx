import { useRef, useState, useCallback } from "react";

interface Props {
  connected: boolean;
  sendBinary: (data: ArrayBufferLike) => void;
  sendJson: (method: string, params?: Record<string, unknown>) => number | undefined;
  className?: string;
}

const RECORDING_STYLE: Record<string, string | number> = {
  width: 36,
  height: 36,
  borderRadius: "50%",
  border: "none",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  cursor: "pointer",
  fontSize: 16,
  transition: "all 0.15s",
  flexShrink: 0,
  position: "relative",
};

export default function VoiceButton({ connected, sendBinary, sendJson, className }: Props) {
  const [recording, setRecording] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);

  const handleStart = useCallback(async () => {
    if (!connected) return;
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });
      streamRef.current = stream;

      const recorder = new MediaRecorder(stream, {
        mimeType: MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
          ? "audio/webm;codecs=opus"
          : "audio/webm",
      });
      mediaRecorderRef.current = recorder;
      chunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        streamRef.current = null;

        const blob = new Blob(chunksRef.current, { type: recorder.mimeType });
        chunksRef.current = [];

        try {
          const arrayBuffer = await blob.arrayBuffer();
          const audioCtx = new AudioContext({ sampleRate: 16000 });
          const audioBuf = await audioCtx.decodeAudioData(arrayBuffer);
          const channel = audioBuf.getChannelData(0);
          const pcm16 = new Int16Array(channel.length);
          for (let i = 0; i < channel.length; i++) {
            const s = Math.round(channel[i] * 32768);
            pcm16[i] = Math.max(-32768, Math.min(32767, s));
          }
          audioCtx.close();

          if (pcm16.length > 0) {
            sendBinary(pcm16.buffer);
          }
        } catch {
          // ignore decode errors
        }

        setRecording(false);
        sendJson("voice.ptt_stop");
      };

      recorder.start(100);
      setRecording(true);
      sendJson("voice.ptt_start");
    } catch (err) {
      setError(
        err instanceof DOMException && err.name === "NotAllowedError"
          ? "Microphone access denied"
          : "Microphone unavailable"
      );
    }
  }, [connected, sendBinary, sendJson]);

  const handleStop = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
    }
  }, []);

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
      {error && (
        <span style={{ fontSize: 11, color: "#f87171", maxWidth: 120 }}>{error}</span>
      )}
      <button
        className={`${className || ""}${recording ? " voice-is-recording" : ""}`}
        onMouseDown={handleStart}
        onMouseUp={handleStop}
        onMouseLeave={recording ? handleStop : undefined}
        onTouchStart={handleStart}
        onTouchEnd={handleStop}
        disabled={!connected}
        style={className ? undefined : {
          ...RECORDING_STYLE,
          background: recording
            ? "#dc2626"
            : connected
            ? "#2a2a3e"
            : "#1a1a2e",
          opacity: connected ? 1 : 0.4,
        }}
        title={recording ? "Release to send" : "Hold to record"}
      >
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke={recording ? "#fff" : "#888"}
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
          <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
          <line x1="12" y1="19" x2="12" y2="23" />
          <line x1="8" y1="23" x2="16" y2="23" />
        </svg>
        {recording && (
          <div
            style={{
              position: "absolute",
              inset: 0,
              borderRadius: className ? "10px" : "50%",
              border: "2px solid rgba(220,38,38,0.5)",
              animation: "voice-pulse 1s ease-in-out infinite",
            }}
          />
        )}
      </button>
    </div>
  );
}
