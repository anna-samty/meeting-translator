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
    You are a Real-Time Meeting Interpreter.
    1. Format: [Speaker Name] | [Original] | [Translation]
    2. Distinguish multiple people as 'Speaker 1', 'Speaker 2', etc.
    3. English <-> Japanese.
    4. If no speech, respond with ONLY '...'
    """
)

if 'history' not in st.session_state:
    st.session_state['history'] = []

st.set_page_config(page_title="Live Dual Translator", layout="wide")
st.title("🚀 Live Multi-Speaker & Manual Translator")

# --- TOP SECTION: LIVE AUTO-STREAM ---
st.header("1. Live Automatic Translation")
col1, col2 = st.columns(2)

with col1:
    st.markdown("### 🇬🇧 English Mic")
    eng_audio = mic_recorder(start_prompt="Start English Auto-Stream", stop_prompt="Stop", key='eng_stream')

with col2:
    st.markdown("### 🇯🇵 Japanese Mic")
    jp_audio = mic_recorder(start_prompt="Start Japanese Auto-Stream", stop_prompt="Stop", key='jp_stream')

# Auto-Processing Logic
def process_segment(audio_data, source_lang):
    if audio_data:
        with st.status(f"Interpreting {source_lang}...", expanded=False):
            try:
                response = model.generate_content([
                    f"Context: Real-time {source_lang} segment.",
                    {'mime_type': 'audio/wav', 'data': audio_data['bytes']}
                ])
                output = response.text.strip()
                if "|" in output and "..." not in output:
                    st.session_state['history'].append({"text": output, "lang": source_lang})
                    st.rerun()
            except Exception as e:
                st.error("Processing...")

if eng_audio: process_segment(eng_audio, "English")
if jp_audio: process_segment(jp_audio, "Japanese")

# --- TRANSCRIPT DISPLAY ---
with st.container(height=300):
    for item in reversed(st.session_state['history']):
        st.write(item['text'])

st.divider()

# --- BOTTOM SECTION: MANUAL RESPONSE (Restored) ---
st.header("2. Your Prepared Response")
c1, c2 = st.columns([1, 3])
with c1:
    my_lang = st.radio("I am typing in:", ["English", "Japanese"], horizontal=True)

my_msg = st.text_area(f"Type your {my_lang} reply here:")

if st.button("Generate & Speak"):
    if my_msg:
        with st.spinner("Translating..."):
            target = "polite Japanese" if my_lang == "English" else "natural English"
            # Command ONLY the translation for clean audio
            clean_prompt = f"Translate to {target}. Provide ONLY the translated text: {my_msg}"
            res = model.generate_content(clean_prompt)
            clean_result = res.text.strip()
            
            st.success(clean_result)
            
            # Generate Audio
            audio_lang = 'ja' if my_lang == "English" else 'en'
            tts = gTTS(text=clean_result, lang=audio_lang)
            fp = io.BytesIO()
            tts.write_to_fp(fp)
            st.audio(fp, autoplay=True)
