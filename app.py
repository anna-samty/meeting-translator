import streamlit as st
import google.generativeai as genai
from streamlit_mic_recorder import mic_recorder
from gtts import gTTS
import io

# 1. Setup
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-3-flash-preview')

# Initialize History and a 'Last Processed' ID to stop duplicates
if 'history' not in st.session_state:
    st.session_state['history'] = []
if 'last_audio_id' not in st.session_state:
    st.session_state['last_audio_id'] = None

st.set_page_config(page_title="JP-EN Live Tool", layout="wide")

# --- TOP SECTION: TRANSCRIPT ---
st.header("1. Live Conversation Waterfall")
with st.container(height=400): 
    for item in st.session_state['history']:
        with st.chat_message("user" if item['side'] == "English" else "assistant"):
            st.write(f"**{item['side']}:** {item['orig']}")
            st.caption(f"Translation: {item['trans']}")

# --- MIDDLE: THE AUTO-RECORDER ---
col1, col2 = st.columns([1, 2])
with col1:
    speaker_lang = st.selectbox("Speaker Language", ["English", "Japanese"])
    st.info("The recorder will process as soon as you stop speaking.")
    
    # mic_recorder returns a unique ID in its data. We use this to stop duplicates.
    audio_data = mic_recorder(
        start_prompt="🔴 Start Live Session",
        stop_prompt="⏹️ Process Segment",
        key='live_recorder'
    )

# 2. Logic to prevent multiple translations of the same audio
if audio_data and audio_data.get('id') != st.session_state['last_audio_id']:
    st.session_state['last_audio_id'] = audio_data['id'] # Lock this ID
    
    with st.spinner("Translating..."):
        try:
            audio_bytes = audio_data['bytes']
            prompt = f"Transcribe this {speaker_lang} audio and translate it. If silent, say 'SILENCE'. Format: Transcript: [text] | Translation: [text]"
            
            response = model.generate_content([prompt, {'mime_type': 'audio/wav', 'data': audio_bytes}])
            res_text = response.text.strip()

            if "SILENCE" not in res_text.upper() and "|" in res_text:
                parts = res_text.split("|")
                orig = parts[0].replace("Transcript:", "").strip()
                trans = parts[1].replace("Translation:", "").strip()
                
                # Append to history
                st.session_state['history'].append({"orig": orig, "trans": trans, "side": speaker_lang})
                st.rerun() # Refresh to show new bubble
        except Exception as e:
            st.error(f"Error: {e}")

st.divider()

# --- BOTTOM SECTION: YOUR RESPONSE ---
st.header("2. Your Response")
my_lang = st.radio("I am typing in:", ["English", "Japanese"], horizontal=True)
my_msg = st.text_area(f"Type {my_lang} message:")

if st.button("Speak Translation"):
    if my_msg:
        target = "polite Japanese" if my_lang == "English" else "natural English"
        res = model.generate_content(f"Translate to {target}. Provide ONLY text: {my_msg}")
        clean_text = res.text.strip()
        st.success(clean_text)
        
        audio_lang = 'ja' if my_lang == "English" else 'en'
        tts = gTTS(text=clean_text, lang=audio_lang)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        st.audio(fp, autoplay=True) # Added autoplay for faster response
