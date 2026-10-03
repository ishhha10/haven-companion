import os
import io
import wave
import logging
import requests
from typing import Optional

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("HavenVoice")

# Default ElevenLabs Rachel Voice ID
RACHEL_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"
ELEVENLABS_TTS_URL = f"https://api.elevenlabs.io/v1/text-to-speech/{RACHEL_VOICE_ID}"


def transcribe_audio_bytes(audio_bytes: bytes) -> Optional[str]:
    """
    Transcribe audio bytes (WAV/OGG/WEBM format from Streamlit audio widget)
    to text using SpeechRecognition.
    Supports multi-lingual (English and Hindi) speech recognition.
    """
    if not audio_bytes:
        return None

    try:
        import speech_recognition as sr
        recognizer = sr.Recognizer()

        # Convert audio bytes into AudioFile
        audio_file_obj = io.BytesIO(audio_bytes)
        
        with sr.AudioFile(audio_file_obj) as source:
            # Adjust for ambient noise and record
            audio_data = recognizer.record(source)

        # Try recognizing in English first
        try:
            text = recognizer.recognize_google(audio_data, language="en-US")
            if text and text.strip():
                logger.info(f"Speech Recognized (en-US): {text}")
                return text.strip()
        except sr.UnknownValueError:
            pass # Try Hindi next

        # Try recognizing in Hindi next (for Hindi / Hinglish spoken audio)
        try:
            text = recognizer.recognize_google(audio_data, language="hi-IN")
            if text and text.strip():
                logger.info(f"Speech Recognized (hi-IN): {text}")
                return text.strip()
        except sr.UnknownValueError:
            logger.warning("Google Speech Recognition could not understand audio.")
            return None

    except Exception as e:
        logger.error(f"Error transcribing audio bytes: {e}")
        return None

    return None


def record_microphone_stt(timeout: int = 5) -> Optional[str]:
    """
    Fallback microphone recording STT using SpeechRecognition package.
    Returns transcribed text string or None.
    """
    try:
        import speech_recognition as sr
        recognizer = sr.Recognizer()
        
        with sr.Microphone() as source:
            logger.info("Listening from microphone...")
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=10)
            
            try:
                text = recognizer.recognize_google(audio, language="en-US")
                return text
            except sr.UnknownValueError:
                return recognizer.recognize_google(audio, language="hi-IN")

    except Exception as e:
        logger.warning(f"Microphone recording unavailable or failed: {e}")
        return None


def generate_tts_elevenlabs(
    text: str,
    api_key: Optional[str] = None,
    voice_id: str = RACHEL_VOICE_ID,
    model_id: str = "eleven_multilingual_v2"
) -> Optional[bytes]:
    """
    Generate TTS audio bytes using ElevenLabs API (multilingual Rachel voice).
    If api_key is missing or fails, gracefully return None to trigger in-app text fallback.
    """
    key = api_key or os.getenv("ELEVENLABS_API_KEY")
    if not key or key.strip() == "":
        logger.info("No ElevenLabs API key provided. Falling back to in-app text display.")
        return None

    try:
        # First attempt using official elevenlabs SDK if available
        try:
            from elevenlabs import ElevenLabs
            client = ElevenLabs(api_key=key)
            audio_generator = client.text_to_speech.convert(
                voice_id=voice_id,
                output_format="mp3_44100_128",
                text=text,
                model_id=model_id,
            )
            # Consume generator bytes
            audio_bytes = b"".join([chunk for chunk in audio_generator if isinstance(chunk, bytes)])
            if audio_bytes:
                logger.info("Successfully generated audio using ElevenLabs SDK.")
                return audio_bytes
        except Exception as sdk_err:
            logger.warning(f"ElevenLabs SDK call failed/not installed: {sdk_err}. Trying direct HTTP request.")

        # Direct HTTP API call fallback
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": key
        }
        payload = {
            "text": text,
            "model_id": model_id,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            logger.info("Successfully generated audio via ElevenLabs HTTP API.")
            return response.content
        else:
            logger.error(f"ElevenLabs HTTP API returned status {response.status_code}: {response.text}")
            return None

    except Exception as e:
        logger.error(f"ElevenLabs TTS generation failed: {e}")
        return None
