import asyncio
import logging

logger = logging.getLogger(__name__)

class SpeechToTextEngine:
    def __init__(self, model_size: str = "base", device: str = "cpu", language: str = "en"):
        self.model_size = model_size
        self.device = device
        self.language = language if language and language != "auto" else None
        self._model = None

    def _get_model(self):
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
                logger.info("Loading Whisper model '%s' on %s...", self.model_size, self.device)
                self._model = WhisperModel(self.model_size, device=self.device, compute_type="int8")
                logger.info("Whisper model loaded successfully.")
            except ImportError as err:
                logger.error("faster-whisper is not installed. Please run `uv pip install -e .[voice]`.")
                raise RuntimeError("faster-whisper is not installed") from err
        return self._model

    def transcribe_sync(self, audio_bytes: bytes) -> str:
        if not audio_bytes:
            return ""
        try:
            import numpy as np
            
            # The audio from frontend is PCM16 16000Hz mono.
            # Convert bytes to numpy float32 array in range [-1.0, 1.0]
            audio_data = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            
            model = self._get_model()
            
            kwargs = {"beam_size": 5}
            if self.language:
                kwargs["language"] = self.language
                
            segments, info = model.transcribe(audio_data, **kwargs)
            
            text = "".join([segment.text for segment in segments])
            return text.strip()
        except Exception as e:
            logger.error("STT Error: %s", e)
            return ""

    async def transcribe(self, audio_bytes: bytes) -> str:
        """Transcribe raw PCM16 audio bytes asynchronously."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.transcribe_sync, audio_bytes)
