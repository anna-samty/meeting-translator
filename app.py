import streamlit as st
import google.generativeai as genai
from streamlit_mic_recorder import mic_recorder
from gtts import gTTS
import io

# 1. Setup the Smart Brain
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

# 2. Initialize Memory
if 'history' not in st.session_state:
    st.session_state['history'] = []

st.set_page_config(page_title="JP-EN Meeting Tool", layout="wide")
st.title("🎙️ English-Japanese Smart Translator")

# --- TOP SECTION: TRANSCRIPT (Waterfall Style) ---
st.header("1. Conversation Transcript")

with st.container(height=400): 
    for item in st.session_state['history']:
        with st.chat_message("user" if item['side'] == "English" else "assistant"):
            st.write(f"**{item['side']}:** {item['orig']}")
            st.caption(f"Translation: {item['trans']}")

# --- CONTROLS SECTION (The New Web-Mic) ---
col1, col2 = st.columns([1, 2])
with col1:
    speaker_lang = st.selectbox("Who is speaking?", ["English", "Japanese"])
    st.write("Click to record, click again to stop:")
    
    # This replaces the old 'Listen' button with a web-compatible one
    audio_data = mic_recorder(
        start_prompt="🔴 Start Recording",
        stop_prompt="⏹️ Stop & Translate",
        key='recorder'
    )

# Process the recording if it exists
if audio_data:
    try:
        # 1. Get the audio from the browser
        audio_bytes = audio_data['bytes']
        
        # 2. Use Gemini to "Hear" and "Translate" in one go
        # This is more stable for web than the old SpeechRecognition library
        prompt = f"""
        The attached audio is in {speaker_lang}. 
        1. Transcribe the audio exactly.
        2. Translate it into {'Japanese' if speaker_lang == 'English' else 'English'}.
        Context of previous meeting: {str(st.session_state['history'][-3:])}
        Format output as: Transcript: [text] | Translation: [text]
        """
        
        # We send the audio bytes directly to Gemini
        response = model.generate_content([
            prompt,
            {'mime_type': 'audio/wav', 'data': audio_bytes}
        ])
        
        # Parse the response (simple split logic)
        res_text = response.text
        if "|" in res_text:
            orig = res_text.split("|")[0].replace("Transcript:", "").strip()
            trans = res_text.split("|")[1].replace("Translation:", "").strip()
            
            # Update History
            st.session_state['history'].append({"orig": orig, "trans": trans, "side": speaker_lang})
            st.rerun()
            
    except Exception as e:
        st.error(f"Error: {e}")

st.divider()

# --- BOTTOM SECTION: YOUR RESPONSE ---
st.header("2. Your Prepared Response")
my_msg = st.text_area("Type your English reply:")

if st.button("Translate & Voice"):
    if my_msg:
        res = model.generate_content(f"Translate this to polite Japanese: {my_msg}")
        st.session_state['last_voice'] = res.text
        st.success(f"Japanese: {res.text}")
        
        # Create Audio
        tts = gTTS(text=res.text, lang='ja')
        # Use a buffer instead of a file for better web performance
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        st.audio(fp)
