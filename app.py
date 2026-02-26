import streamlit as st
import google.generativeai as genai
from streamlit_mic_recorder import mic_recorder
import io

# 1. Setup
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# Advanced System Instruction for Multi-Speaker
model = genai.GenerativeModel(
    model_name='gemini-3-flash-preview',
    system_instruction="""
    You are a Live Meeting Interpreter. 
    1. Identify if multiple people are speaking. 
    2. Label them as 'Speaker A' and 'Speaker B' based on context.
    3. Translate English to Japanese and Japanese to English.
    4. Format: Speaker [A/B] | [Original] | [Translation]
    5. If audio is messy/noise, return 'RETRY'.
    """
)

if 'history' not in st.session_state:
    st.session_state['history'] = []

st.set_page_config(page_title="Live Dual Translator", layout="wide")
st.title("🎙️ Dual-Speaker Live Translator")

# --- DUAL INTERFACE (Same Screen) ---
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("🇬🇧 English Side")
    # This key 'eng_mic' keeps this mic separate from the JP one
    eng_audio = mic_recorder(start_prompt="Start English Mic", stop_prompt="Stop", key='eng_mic', just_once=False)

with col_right:
    st.subheader("🇯🇵 Japanese Side")
    jp_audio = mic_recorder(start_prompt="Start Japanese Mic", stop_prompt="Stop", key='jp_mic', just_once=False)

# --- THE ENGINE ---
def process_live_audio(audio_bits, source_lang):
    if audio_bits:
        with st.spinner("Decoding..."):
            try:
                # Direct byte-stream to Gemini for speed
                response = model.generate_content([
                    f"Task: Real-time {source_lang} translation. Identify speakers.",
                    {'mime_type': 'audio/wav', 'data': audio_bits['bytes']}
                ])
                res = response.text.strip()
                if "|" in res and "RETRY" not in res:
                    st.session_state['history'].append({"data": res, "lang": source_lang})
                    st.rerun()
            except:
                pass

# Monitor both mics
if eng_audio: process_live_audio(eng_audio, "English")
if jp_audio: process_live_audio(jp_audio, "Japanese")

# --- THE WATERFALL ---
st.write("---")
st.header("Live Transcript")
for item in reversed(st.session_state['history']): # Newest at top for easy reading
    st.info(item['data'])
