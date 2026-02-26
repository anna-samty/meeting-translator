import streamlit as st
import google.generativeai as genai
from streamlit_mic_recorder import mic_recorder
from gtts import gTTS
import io

# 1. Setup
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel(
    model_name='gemini-3-flash-preview',
    system_instruction="""
    You are a professional meeting translator. 
    If audio is silent/static, respond with ONLY: 'SILENCE'. 
    Otherwise, transcribe and translate. 
    Format: Transcript: [text] | Translation: [text]
    """
)

if 'history' not in st.session_state:
    st.session_state['history'] = []

st.set_page_config(page_title="JP-EN Meeting Tool", layout="wide")
st.title("🎙️ English-Japanese Smart Translator")

# --- TOP SECTION: TRANSCRIPT ---
st.header("1. Conversation Transcript")
with st.container(height=400): 
    for item in st.session_state['history']:
        with st.chat_message("user" if item['side'] == "English" else "assistant"):
            st.write(f"**{item['side']}:** {item['orig']}")
            st.caption(f"Translation: {item['trans']}")

# --- MIDDLE SECTION: VOICE INPUT ---
col1, col2 = st.columns([1, 2])
with col1:
    speaker_lang = st.selectbox("Who is speaking?", ["English", "Japanese"], key="voice_lang")
    audio_data = mic_recorder(start_prompt="🔴 Start Recording", stop_prompt="⏹️ Stop & Translate", key='recorder')

if audio_data:
    with st.spinner("AI is thinking..."):
        try:
            audio_bytes = audio_data['bytes']
            prompt = f"Transcribe this {speaker_lang} audio and translate it."
            response = model.generate_content([prompt, {'mime_type': 'audio/wav', 'data': audio_bytes}])
            res_text = response.text.strip()

            if "SILENCE" not in res_text.upper() and "|" in res_text:
                parts = res_text.split("|")
                orig = parts[0].replace("Transcript:", "").strip()
                trans = parts[1].replace("Translation:", "").strip()
                st.session_state['history'].append({"orig": orig, "trans": trans, "side": speaker_lang})
                st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

st.divider()

# --- BOTTOM SECTION: MANUAL RESPONSE (Updated) ---
st.header("2. Your Prepared Response")
c1, c2 = st.columns([1, 3])
with c1:
    my_lang = st.radio("I am typing in:", ["English", "Japanese"], horizontal=True)

my_msg = st.text_area(f"Type your {my_lang} reply here:")

if st.button("Generate Translation & Voice"):
    if my_msg:
        with st.spinner("Translating..."):
            target = "polite Japanese" if my_lang == "English" else "natural English"
            res = model.generate_content(f"Translate this to {target}: {my_msg}")
            
            st.success(f"Result: {res.text}")
            
            # Generate Audio (detects language automatically)
            audio_lang = 'ja' if my_lang == "English" else 'en'
            tts = gTTS(text=res.text, lang=audio_lang)
            fp = io.BytesIO()
            tts.write_to_fp(fp)
            st.audio(fp)
