import streamlit as st
import sqlite3
import ollama
import json

st.set_page_config(page_title="Haven | Live Phone Call", page_icon="📞", layout="centered")

# --- DATABASE SETUP ---
DB_NAME = "companion_memory.db"

def init_db():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            speaker TEXT,
            text TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_memory(speaker, text):
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO conversations (speaker, text) VALUES (?, ?)", (speaker, text))
    conn.commit()
    conn.close()

def get_recent_memories(limit=4):
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT speaker, text FROM conversations ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows[::-1]

def clear_all_memories():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM conversations")
    conn.commit()
    conn.close()

init_db()

# --- OPTIMIZED SHORT SYSTEM PROMPT (Faster processing) ---
SYSTEM_PROMPT = """You are Haven, a compassionate friend on a direct phone call.
Rules:
1. Speak in warm Hinglish/Hindi or English matching the user.
2. If they sound distressed, gently ask: "Do you want me to just listen, or think of solutions together?"
3. Reply in ONLY 1 to 2 short sentences. Never give long lectures."""

def generate_fast_reply(user_input):
    history = get_recent_memories(3) # Short history = much faster generation
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for speaker, text in history:
        messages.append({"role": "user" if speaker == "User" else "assistant", "content": text})
    messages.append({"role": "user", "content": user_input})
    try:
        # options: num_predict limits generation to 45 tokens (instant reply!)
        # num_ctx: 1024 keeps RAM low and execution snappy on CPU
        response = ollama.chat(
            model="gemma2:2b",
            messages=messages,
            options={
                "num_predict": 45,
                "temperature": 0.7,
                "num_ctx": 1024
            }
        )
        return response['message']['content'].strip()
    except Exception as e:
        return f"Main sun raha hoon, bolo: {e}"

# --- UI ---
st.title("🌙 Haven")
st.caption("⚡ Ultra-Fast Voice Companion (Optimized for instant replies)")

with st.sidebar:
    st.header("⚙️ Settings")
    if st.button("🗑️ Reset Past Memory", use_container_width=True):
        clear_all_memories()
        st.success("Memory cleared.")
        st.rerun()

mode = st.radio("Choose Mode:", ["📞 Live Phone Call", "💬 Text Chat"], horizontal=True)

if mode == "💬 Text Chat":
    st.subheader("💬 Message Haven")
    history = get_recent_memories(8)
    for spk, text in history:
        with st.chat_message("user" if spk == "User" else "assistant"):
            st.write(text)

    user_input = st.chat_input("Write what's on your mind...")
    if user_input:
        save_memory("User", user_input)
        with st.chat_message("user"):
            st.write(user_input)
        with st.chat_message("assistant"):
            reply = generate_fast_reply(user_input)
            st.write(reply)
            save_memory("Haven", reply)
            st.rerun()

else:
    st.markdown("""
        <style>
        .phone-frame {
            background: #11141e;
            border: 2px solid #2d334a;
            border-radius: 30px;
            padding: 25px 20px;
            text-align: center;
            max-width: 420px;
            margin: 10px auto;
            box-shadow: 0 10px 35px rgba(0,0,0,0.6);
        }
        .caller-avatar {
            width: 90px;
            height: 90px;
            border-radius: 50%;
            background: linear-gradient(135deg, #4f46e5 0%, #9333ea 100%);
            margin: 0 auto 12px auto;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 40px;
            box-shadow: 0 0 20px rgba(147, 51, 234, 0.45);
        }
        .call-title { color: #f3f4f6; font-size: 1.3rem; font-weight: 600; margin-bottom: 4px; }
        .call-status { color: #10b981; font-size: 0.95rem; margin-bottom: 15px; }
        </style>
    """, unsafe_allow_html=True)

    if "call_connected" not in st.session_state:
        st.session_state.call_connected = False
    if "last_response" not in st.session_state:
        st.session_state.last_response = "Hey, I'm right here. How are you feeling right now?"
        save_memory("Haven", st.session_state.last_response)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🟢 Start Call", use_container_width=True, disabled=st.session_state.call_connected):
            st.session_state.call_connected = True
            st.session_state.last_response = "Hey, I'm right here with you. How are you feeling right now?"
            st.rerun()
    with col2:
        if st.button("🔴 End Call", use_container_width=True, disabled=not st.session_state.call_connected):
            st.session_state.call_connected = False
            st.rerun()

    if not st.session_state.call_connected:
        st.markdown("""
            <div class="phone-frame">
                <div class="caller-avatar">🌙</div>
                <div class="call-title">Haven</div>
                <p style="color: #9ca3af; font-size: 0.85rem;">Instant voice call. Tap 'Start Call' to connect.</p>
            </div>
        """, unsafe_allow_html=True)
    else:
        last_bot_say = st.session_state.last_response

        html_code = f"""
        <div class="phone-frame">
            <div class="caller-avatar">🌙</div>
            <div class="call-title">Haven</div>
            <div class="call-status" id="status">🟢 On Call</div>
            <p id="subtext" style="color: #9ca3af; font-size: 0.88rem; min-height: 40px; padding: 0 10px;">
                "{last_bot_say}"
            </p>
            <div id="micIndicator" style="margin-top: 10px; color: #38bdf8; font-size: 0.85rem; font-weight: 500;">
                🎙️ Listening...
            </div>
        </div>

        <script>
        const botText = {json.dumps(last_bot_say)};
        const synth = window.speechSynthesis;
        let recognition = null;

        function speakAndListen() {{
            synth.cancel();
            const utter = new SpeechSynthesisUtterance(botText);
            utter.rate = 1.05;
            utter.pitch = 1.0;

            const voices = synth.getVoices();
            const preferredVoice = voices.find(v => v.lang.includes('en') || v.lang.includes('hi'));
            if (preferredVoice) utter.voice = preferredVoice;

            document.getElementById("status").innerText = "🔊 Haven is speaking...";
            document.getElementById("micIndicator").innerText = "Listening starts after speaking...";

            utter.onend = function() {{
                startListening();
            }};
            utter.onerror = function() {{
                startListening();
            }};

            synth.speak(utter);
        }}

        function startListening() {{
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            if (!SpeechRecognition) return;

            recognition = new SpeechRecognition();
            recognition.lang = 'en-IN';
            recognition.continuous = false;
            recognition.interimResults = false;

            document.getElementById("status").innerText = "🟢 Call Active (Listening...)";
            document.getElementById("micIndicator").innerHTML = "🎙️ <b>Listening to you...</b>";

            recognition.onresult = function(event) {{
                const userSpeech = event.results[0][0].transcript;
                document.getElementById("status").innerText = "⚡ Thinking...";
                document.getElementById("subtext").innerText = 'You: "' + userSpeech + '"';
                
                const inputs = window.parent.document.querySelectorAll('input[type="text"]');
                for (let inp of inputs) {{
                    if (inp.getAttribute('aria-label') === 'call_transcript_receiver') {{
                        inp.value = userSpeech;
                        inp.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        inp.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        const enterEvent = new KeyboardEvent('keydown', {{ bubbles: true, cancelable: true, keyCode: 13, key: 'Enter' }});
                        inp.dispatchEvent(enterEvent);
                        break;
                    }}
                }}
            }};

            recognition.onerror = function(event) {{
                setTimeout(startListening, 1000);
            }};

            recognition.start();
        }}

        if (synth.getVoices().length > 0) {{
            speakAndListen();
        }} else {{
            synth.onvoiceschanged = speakAndListen;
        }}
        </script>
        """

        st.components.v1.html(html_code, height=340)

        user_spoken = st.text_input("call_transcript_receiver", label_visibility="collapsed", key="live_call_input")
        if user_spoken and user_spoken.strip():
            save_memory("User", user_spoken)
            bot_reply = generate_fast_reply(user_spoken)
            save_memory("Haven", bot_reply)
            st.session_state.last_response = bot_reply