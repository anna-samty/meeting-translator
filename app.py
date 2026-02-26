import streamlit as st
import google.generativeai as genai
from streamlit_mic_recorder import mic_recorder
from gtts import gTTS
import io
import streamlit.components.v1 as components # Essential for keyboard shortcuts

# 1. Setup
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# Use 'gemini-1.5-flash' for the best balance of speed and stability
model = genai.GenerativeModel(
    model_name='gemini-1.5-flash',
    system_instruction="""
    You are a strict translation engine. 
    - If input is English, you MUST output ONLY Japanese.
    - If input is Japanese, you MUST output ONLY English.
    - Break long speech into clear sentences.
    - Format: [Original Text] | [Translated Text]
    - If there is only noise or silence, respond with 'SILENCE'.
    """
)

if 'history' not in st.session_state:
    st.session_state['history'] = []
if 'last_id' not in st.session_state:
    st.session_state['last_id'] = 0

st.set_page_config(page_title="Stealth JP-EN Translator", layout="wide")

# --- KEYBOARD SHORTCUT LOGIC ---
# This script searches for the buttons based on the text "Record" or "Process"
components.html(
    """
    <script>
    const doc = window.parent.document;
    doc.addEventListener('keydown', function(e) {
        // Spacebar trigger, but ONLY if not typing in a text box
        if (e.code === 'Space' && e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
            e.preventDefault();
            const buttons = doc.querySelectorAll('button');
            for (let btn of buttons) {
                if (btn.innerText.includes("Record") || btn.innerText.includes("Process")) {
                    btn.click();
                    break;
                }
            }
        }
    });
    </script>
    """,
    height=0,
)

st.title("🎙️ Meeting Translator (Stealth Mode)")
st.info("💡 **Stealth Tip:** Click the page background once, then use **Spacebar** to Start/Stop recording.")

# --- TRANSCRIPT DISPLAY ---
with st.container(height=400): 
    for item in st.session_state['history']:
        with st.chat_message("user" if item['side'] == "English" else "assistant"):
            st.write(f"**{item['side']}:** {item['orig']}")
            st.caption(f"Translation: {item['trans']}")

# --- THE RECORDER ---
st.write("---")
speaker_lang = st.selectbox("Current Speaker Language:", ["English", "Japanese"])

# prompts must include "Record" and "Process" for the JavaScript to find them
audio_data = mic_recorder(
    start_prompt=f"🔴 Record {speaker_lang}",
    stop_prompt="⏹️ Process Now",
    just_once=True, 
    key='recorder'
)

if audio_data:
    new_id = audio_data.get('id')
    if new_id != st.session_state['last_id']:
        st.session_state['last_id'] = new_id
        
        with st.spinner("Translating..."):
            try:
                audio_bytes = audio_data['bytes']
                target_lang = "Japanese" if speaker_lang == "English" else "English"
                
                prompt = f"Transcribe and translate this {speaker_lang} audio into {target_lang}. Split thoughts into new lines: [Original] | [Translation]"
                
                response = model.generate_content([prompt, {'mime_type': 'audio/wav', 'data': audio_bytes
