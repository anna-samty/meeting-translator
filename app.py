import streamlit as st
import google.generativeai as genai
from streamlit_mic_recorder import mic_recorder
from gtts import gTTS
import io

# 1. Setup
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-3-flash-preview')

# Initialize History
if 'history' not in st.session_state:
    st.session_state['history'] = []

st.set_page_config(page_title="Stable JP-EN Translator", layout="wide")
st.title("🎙️ English-Japanese Meeting Tool")

# --- 1. TRANSCRIPT (Waterfall) ---
st.header("Meeting Transcript")
with st.container(height=350):
    for item in st.session_state['history']:
        with st.chat_message("user" if item['side'] == "English" else "assistant"):
            st.write(f"**{item['side']}:** {item['orig']}")
            st.caption(f"Translation: {item['trans']}")

# --- 2. VOICE INPUT (Manual Trigger) ---
st.divider()
st.subheader("Capture Speech")
col1, col2 = st.columns([1, 2])

with col1:
    speaker_lang = st.selectbox("Who is speaking?", ["English", "Japanese"])
    # Manual trigger avoids the 'ResourceExhausted' error
    audio_data = mic_recorder(
        start_prompt=f"Record {speaker_lang}", 
        stop_prompt="Stop & Translate", 
        key='manual_mic'
    )

if audio_data:
    with st.spinner("Processing..."):
        try:
            target_lang = "Japanese" if speaker_lang == "English" else "English"
            prompt = f"Identify speaker and translate this {speaker_lang} audio into {target_lang}. Format: [Original] | [Translation]"
            
            response = model.generate_content([
                prompt,
                {'mime_type': 'audio/wav', 'data': audio_data['bytes']}
            ])
            
            res_text = response.text.strip()
            if "|" in res_text:
                orig, trans = res_text.split("|", 1)
                st.session_state['history'].append({
                    "orig": orig.strip(), 
                    "trans": trans.strip(), 
                    "side": speaker_lang
                })
                st.rerun()
        except Exception as e:
            st.error(f"API Error: {e}. If it says 'ResourceExhausted', wait 60 seconds.")

# --- 3. PREPARED RESPONSE (Manual Typing) ---
st.divider()
st.subheader("Your Response")
c1, c2 = st.columns([1, 3])
with c1:
    my_lang = st.radio("I am typing in:", ["English", "Japanese"], horizontal=True)

my_msg = st.text_input(f"Type your {my_lang} reply:")

if st.button("Generate & Speak"):
    if my_msg:
        with st.spinner("Translating..."):
            target = "polite Japanese" if my_lang == "English" else "natural English"
            # Explicitly asking for ONLY the text to keep the voice clean
            res = model.generate_content(f"Translate this to {target}. Provide ONLY the translated text, no labels: {my_msg}")
            clean_result = res.text.strip()
            
            st.success(clean_result)
            
            # Generate and Play Audio
            v_lang = 'ja' if my_lang == "English" else 'en'
            tts = gTTS(text=clean_result, lang=v_lang)
            fp = io.BytesIO()
            tts.write_to_fp(fp)
            st.audio(fp, autoplay=True)
