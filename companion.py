import os
import re
import logging
from typing import List, Dict, Any, Tuple

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("HavenCompanion")

SYSTEM_PROMPT = """You are Haven, a voice-first, empathetic AI companion designed for a close friend who is dealing with heavy personal or family matters they cannot openly share.

CRITICAL BEHAVIORAL RULES:
1. EMPATHY FIRST: Always validate the user's feelings warmly and non-judgmentally in your very first sentence before anything else.
2. DYNAMIC LANGUAGE MIRRORING:
   - Match the user's exact language and dialect style seamlessly.
   - If the user speaks English, respond in comforting English.
   - If the user speaks Hindi (Devanagari script), respond in standard Hindi.
   - If the user speaks natural Hinglish (Roman script Hindi, e.g. "Mera din bohot heavy tha", "Ghar pe sab pareshan hain"), respond in warm, natural Hinglish.
3. CONCISENESS (PHONE CALL STYLE):
   - Keep your responses strictly between 2 to 4 sentences long.
   - Speak naturally, like a calm, warm, late-night phone call with a trusted friend.
4. GENTLE LISTENER RULE:
   - Early in heavy or emotional conversations, or when the user is sharing personal troubles, include or adapt the gentle check:
     "Do you want me to just listen and be here with you, or would you like us to think through solutions together?" (or its natural Hinglish/Hindi counterpart).
   - DO NOT give unsolicited advice or list solutions unless the user explicitly requests advice or chooses solution-oriented support.
5. NON-JUDGMENTAL PRESENCE:
   - Provide active listening, acceptance, and a safe space. Never lecture or criticize.
"""

# Emotion keyword indicators for tagging and gentle listener detection
HEAVY_EMOTION_KEYWORDS = [
    "sad", "depressed", "lonely", "overwhelmed", "stressed", "scared", "afraid",
    "crying", "hurt", "tired", "anxious", "pain", "broken", "family", "fight",
    "parents", "problem", "difficult", "heavy", "pareshan", "dukhi", "bohot",
    "ghar", "rula", "chinta", "mar", "chhod", "koi nahi", "alone", "help", "solution"
]

HINGLISH_KEYWORDS = [
    "bohot", "hai", "hain", "mujhe", "mera", "meri", "kya", "bhai", "sab", "raha",
    "rahi", "kaam", "ghar", "lag", "dil", "aaj", "kar", "ho", "nahi", "nahin",
    "samajh", "batao", "suno", "baat"
]

class HavenCompanion:
    def __init__(
        self,
        mode: str = "ollama", # "ollama" or "remote"
        model_name: str = "gemma2:2b",
        remote_base_url: str = None,
        remote_api_key: str = None
    ):
        self.mode = mode.lower()
        self.model_name = model_name or "gemma2:2b"
        self.remote_base_url = remote_base_url or os.getenv("OPENAI_BASE_URL", os.getenv("REMOTE_MODEL_URL"))
        self.remote_api_key = remote_api_key or os.getenv("OPENAI_API_KEY", "dummy-key")

    def detect_language_and_emotion(self, text: str) -> Tuple[str, str, bool]:
        """
        Detect language type ('english', 'hinglish', 'hindi'),
        perceived emotion tag ('sad', 'anxious', 'overwhelmed', 'neutral'),
        and whether gentle listener prompt should be triggered.
        """
        text_lower = text.lower()
        
        # 1. Language detection
        contains_hindi_script = bool(re.search(r'[\u0900-\u097F]', text))
        
        if contains_hindi_script:
            lang = "hindi"
        else:
            words = set(re.findall(r'\b\w+\b', text_lower))
            hinglish_count = sum(1 for w in words if w in HINGLISH_KEYWORDS)
            if hinglish_count >= 1 or any(k in text_lower for k in ["mera", "bohot", "pareshan", "nahi"]):
                lang = "hinglish"
            else:
                lang = "english"

        # 2. Emotion tagging
        emotion = "neutral"
        if any(w in text_lower for w in ["sad", "crying", "hurt", "dukhi", "rula", "broken"]):
            emotion = "sad"
        elif any(w in text_lower for w in ["overwhelmed", "heavy", "bohot", "tired", "thak"]):
            emotion = "overwhelmed"
        elif any(w in text_lower for w in ["scared", "afraid", "anxious", "chinta", "darr"]):
            emotion = "anxious"
        elif any(w in text_lower for w in ["family", "fight", "ghar", "parents"]):
            emotion = "family_matter"

        # 3. Gentle listener check trigger
        is_heavy = any(k in text_lower for k in HEAVY_EMOTION_KEYWORDS)
        
        return lang, emotion, is_heavy

    def generate_response(self, user_input: str, conversation_history: List[Dict[str, Any]] = None) -> Tuple[str, str]:
        """
        Generate response from Gemma 2 (via Ollama or Remote API).
        Returns (response_text, emotion_tag).
        """
        lang, emotion_tag, is_heavy = self.detect_language_and_emotion(user_input)
        
        # Format chat history into messages array
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        
        if conversation_history:
            for item in conversation_history[-6:]:  # Last 6 context turns
                speaker_role = "user" if item.get("speaker") == "User" else "assistant"
                messages.append({"role": speaker_role, "content": item.get("text", "")})
        
        # Add current user message
        messages.append({"role": "user", "content": user_input})
        
        # Execute model call based on mode
        response_text = ""
        if self.mode == "remote" and self.remote_base_url:
            response_text = self._call_remote_openai(messages)
        else:
            response_text = self._call_ollama(messages)

        # Fallback if inference failed or returned empty
        if not response_text:
            response_text = self._get_fallback_response(lang, is_heavy)

        # Post-check: ensure Gentle Listener rule is respected if early heavy exchange and model missed it
        response_text = self._ensure_gentle_listener_rule(user_input, response_text, lang, is_heavy, conversation_history)

        return response_text, emotion_tag

    def _call_ollama(self, messages: List[Dict[str, str]]) -> str:
        """Call local Ollama instance running gemma2:2b."""
        try:
            import ollama
            response = ollama.chat(
                model=self.model_name,
                messages=messages,
                options={"temperature": 0.7}
            )
            if response and "message" in response and "content" in response["message"]:
                return response["message"]["content"].strip()
        except Exception as e:
            logger.warning(f"Ollama local inference error: {e}. Trying remote or fallback.")
            # If remote endpoint exists, attempt fallback call
            if self.remote_base_url:
                return self._call_remote_openai(messages)
        return ""

    def _call_remote_openai(self, messages: List[Dict[str, str]]) -> str:
        """Call OpenAI / Hugging Face compatible remote endpoint."""
        try:
            from openai import OpenAI
            client = OpenAI(
                base_url=self.remote_base_url,
                api_key=self.remote_api_key or "dummy"
            )
            response = client.chat.completions.create(
                model=self.model_name if self.model_name != "gemma2:2b" else "gemma-2-9b-it",
                messages=messages,
                temperature=0.7,
                max_tokens=300
            )
            if response.choices and len(response.choices) > 0:
                return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Remote endpoint API error: {e}")
        return ""

    def _ensure_gentle_listener_rule(
        self,
        user_input: str,
        response_text: str,
        lang: str,
        is_heavy: bool,
        history: List[Dict[str, Any]]
    ) -> str:
        """
        Enforce the Gentle Listener Rule if the conversation is heavy and early on.
        "Do you want me to just listen and be here with you, or would you like us to think through solutions together?"
        """
        turn_count = len(history) if history else 0
        
        # Check if question was already asked recently
        question_already_asked = False
        if history:
            for item in history[-4:]:
                if "just listen" in item.get("text", "").lower() or "bas sunoon" in item.get("text", "").lower():
                    question_already_asked = True
                    break

        # Ask gentle listener prompt if heavy emotion detected, early turn, and hasn't been asked yet
        if is_heavy and turn_count <= 4 and not question_already_asked:
            gentle_phrase = ""
            if lang == "hinglish":
                gentle_phrase = " Kya aap chahte hain ki main bas aapki baat sunoon aur saath rahoon, ya hum milkar solution dhoondhein?"
            elif lang == "hindi":
                gentle_phrase = " क्या आप चाहते हैं कि मैं बस आपकी बात सुनूं और आपके साथ रहूं, या हम मिलकर इसका समाधान सोचें?"
            else:
                gentle_phrase = " Do you want me to just listen and be here with you, or would you like us to think through solutions together?"

            # Append if not already present in response text
            if "listen" not in response_text.lower() and "sunoon" not in response_text.lower() and "सुनूं" not in response_text:
                response_text += gentle_phrase

        return response_text

    def _get_fallback_response(self, lang: str, is_heavy: bool) -> str:
        """Fallback responses when model server is not reachable."""
        if lang == "hinglish":
            return "Main samajh sakta hoon ki aap bohot heavy feel kar rahe hain. Main yahan hoon aapki baat sunne ke liye. Kya aap chahte hain ki main bas sunoon, ya hum solution dhoondhein?"
        elif lang == "hindi":
            return "मैं समझ सकता हूँ कि आप बहुत परेशान महसूस कर रहे हैं। मैं यहाँ आपकी बात सुनने के लिए हूँ। क्या आप चाहते हैं कि मैं बस सुनूं, या हम समाधान ढूंढें?"
        else:
            return "I can hear how much weight you're carrying right now. I'm right here with you. Do you want me to just listen and be here, or would you like to think through solutions together?"
