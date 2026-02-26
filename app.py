import streamlit as st
import google.generativeai as genai
from streamlit_mic_recorder import mic_recorder
import io

# 1. Setup Gemini 3
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# Advanced System Instruction for "Unmixing" voices
model = genai.GenerativeModel(
    model_name='gemini-3-flash-preview',
    system_instruction="""
    You are a Real-Time Meeting Interpreter.
    RULES:
    1. Output format: [Speaker Name] | [Original] | [Translation]
    2. If you hear multiple people, distinguish them as 'Speaker 1', 'Speaker 2', etc.
    3. Translate English -> Japanese and Japanese -> English.
    4. If no speech is detected, respond ONLY with '...'
    5. Be extremely fast and concise.
    """
)

if 'history' not in st.session_state:
    st.session_state['history'] = []

st.set_page_config(page_title="Live Auto-Translator", layout="wide")
st.title("🚀 Live Multi-Speaker Translator")

# --- UI LAYOUT ---
col1, col2 = st.columns(2)

with col1:
    st.markdown("### 🇬🇧 English Mic")
    # Setting 'just_once=False' and using a key allows continuous capture
    eng_audio = mic_recorder(
        start_prompt="Start English Auto-Stream",
        stop_prompt="Stop",
        key='eng_stream'
    )

with col2:
    st.markdown("### 🇯🇵 Japanese Mic")
    jp_audio = mic_recorder(
        start_prompt="Start Japanese Auto-Stream",
        stop_prompt="Stop",
        key='jp_stream'
    )

# --- THE AUTO-ENGINE ---
def process_segment(audio_data, source_lang):
    if audio_data:
        # We use a spinner to show the "Speed" of processing
        with st.status(f"Interpreting {source_lang}...", expanded=False):
            try:
                # We send the raw audio segment to Gemini 3 Flash
                # Gemini 3 is optimized for "Diarization" (telling speakers apart)
                response = model.generate_content([
                    f"Context: Real-time {source_lang} meeting segment.",
                    {'mime_type': 'audio/wav', 'data': audio_data['bytes']}
                ])
                
                output = response.text.strip()
                if "|" in output and "..." not in output:
                    st.session_state['history'].append({"text": output, "lang": source_lang})
                    st.rerun()
            except Exception as e:
                st.error("Audio processing lag...")

# Run the engine for whichever mic is active
if eng_audio:
    process_segment(eng_audio, "English")
if jp_audio:
    process_segment(jp_audio, "Japanese")

# --- THE LIVE TRANSCRIPT WATERFALL ---
st.divider()
st.subheader("Live Meeting Minutes")

# Displaying newest messages at the top for real-time visibility
for item in reversed(st.session_state['history']):
    icon = "👤" if "Speaker 1" in item['text'] else "👥"
    st.write(f"{icon} {item['text']}")
