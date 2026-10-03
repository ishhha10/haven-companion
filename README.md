# 🕯️ Haven — Voice-First Empathetic AI Companion

> Built for the **Hacktoberfest DEV Weekend Challenge ("Build for a Friend")**.

**Haven** is a voice-first, empathetic AI companion designed for a friend dealing with heavy personal or family matters they cannot openly share. It focuses on 100% privacy, non-judgmental presence, and active listening rather than unsolicited advice.

---

## 🌟 Prize Track Architecture Coverage

| Prize Track | Implementation Details |
| :--- | :--- |
| 🤖 **Gemma Track ($200)** | Core Intelligence defaults to **Google Gemma 2 (2B)** running 100% locally via Ollama (`gemma2:2b`) for zero data leakage. Features a dual-execution fallback to connect to remote OpenAI/Hugging Face-compatible endpoints for cloud setups. |
| 🎙️ **ElevenLabs Track ($100)** | Converts Haven's responses into comforting audio streams using ElevenLabs API (`eleven_multilingual_v2`, voice: "Rachel"). If no API key is provided, gracefully falls back to in-app text display with zero crashes. |
| 💾 **MongoDB Atlas Track ($100)** | Dynamic hybrid persistent memory in `database.py`. Automatically uses MongoDB Atlas when `MONGODB_URI` is provided, and auto-falls back to an offline local SQLite database (`companion_memory.db`) if missing or offline. |
| 🚀 **Render Track ($200)** | Fully containerized with `Dockerfile` and `render.yaml` blueprint ready for 1-click cloud deployment on Render. |

---

## ✨ Key Features & Rules

1. **Dynamic Language Mirroring**:
   - Seamlessly switches between English, Hindi (Devanagari), and natural conversational **Hinglish** (Roman script Hindi like *"Mera din bohot heavy tha"*) based on user speech/text input.
2. **The Gentle Listener Rule**:
   - Early in heavy or emotional exchanges, Haven gently offers:
     > *"Do you want me to just listen and be here with you, or would you like us to think through solutions together?"* (or its natural Hinglish/Hindi counterpart).
3. **Phone Call Style Conciseness**:
   - Validates user feelings warmly first, keeping responses concise (**2 to 4 sentences**) to simulate a calm, intimate late-night phone call.
4. **Voice & Audio Input/Output**:
   - Microphone/Browser audio capture via Speech-to-Text (`speech_recognition`) with manual text input fallback.
   - ElevenLabs multilingual TTS voice audio streaming.
5. **Intimate Dark-Mode Interface**:
   - Minimalist late-night phone call styling in Streamlit with ambient glassmorphism cards, glowing call status indicator, live feed, and expandable history drawer.

---

## 📁 Repository Structure

```
haven/
├── app.py              # Main Streamlit user interface & call control
├── companion.py        # Gemma 2 orchestration, Ollama/OpenAI API fallback, language mirroring & persona logic
├── database.py         # MongoDB Atlas + SQLite auto-fallback CRUD logic
├── voice.py            # Speech-to-Text audio transcription & ElevenLabs TTS generation
├── requirements.txt    # Pinned Python dependencies
├── Dockerfile          # Container build setup for deployment
├── render.yaml         # Render cloud deployment blueprint specification
└── README.md           # Documentation & step-by-step setup guide
```

---

## 🚀 Local Setup Guide (Windows / macOS / Linux)

### 1. Prerequisites
- **Python 3.10+** installed.
- **Ollama** installed locally ([ollama.com](https://ollama.com)).

### 2. Pull Gemma 2 Model
Open your terminal and run:
```bash
ollama pull gemma2:2b
```
Ensure Ollama is running in the background (`ollama serve`).

### 3. Clone Repository & Install Dependencies
```bash
git clone https://github.com/your-username/haven.git
cd haven

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows:
.\.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Optional Environment Variables Setup
Create a `.env` file in the root folder (optional):
```env
# Optional ElevenLabs API Key for voice output
ELEVENLABS_API_KEY=your_eleven_labs_api_key

# Optional MongoDB Atlas URI for cloud memory storage
MONGODB_URI=mongodb+srv://user:password@cluster.mongodb.net/haven_db

# Optional Remote OpenAI-compatible Endpoint (for Cloud Execution Mode)
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_API_KEY=your_openai_api_key
MODEL_NAME=gemma-2-9b-it
```

### 5. Run the Haven Application
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

---

## ☁️ Deployment Guide (Render)

1. Fork or push this repository to GitHub.
2. Log in to [Render Dashboard](https://dashboard.render.com/).
3. Click **New +** -> **Blueprint**.
4. Connect your GitHub repository. Render will automatically detect `render.yaml`.
5. Specify your optional environment variables (`ELEVENLABS_API_KEY`, `MONGODB_URI`, `OPENAI_BASE_URL`, `OPENAI_API_KEY`) under Service Settings.
6. Click **Apply**. Render will build the container using `Dockerfile` and launch your service!

---

## 🔒 Privacy & Safety Statement

Haven is built with privacy at its core. When using default local Ollama execution and local SQLite storage, **0 bytes of conversation data leave your local computer**. 

---

## 📄 License
MIT License. Built with ❤️ for friends who need a safe place to talk.
