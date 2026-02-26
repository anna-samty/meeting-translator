import streamlit as st
import google.generativeai as genai
from streamlit_mic_recorder import mic_recorder
from gtts import gTTS
import io

# 1. Setup the Brain with "Anti-Hallucination" rules
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# We use gemini-3-flash-preview (the 2026 standard)
# We add a 'System Instruction' to prevent it from making up fake conversations
model = genai.GenerativeModel(
    model_name='gemini-3-flash-preview',
    system_instruction="""
    You are a professional meeting translator. 
    If the audio provided is silent, contains only static, 
    or has no clear human speech, you must respond with ONLY the word: 'SILENCE'. 
    Do not invent any text or conversations.
    """
)

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

# --- CONTROLS SECTION ---
col1, col2 = st.columns([1, 2])
with col1:
    speaker_lang = st.selectbox("Who is speaking?", ["English", "Japanese"])
    st.write("Click to record, speak, then click stop:")
    
    # Capture audio from the browser
    audio_data = mic_recorder(
        start_prompt="🔴 Start Recording",
        stop_prompt="⏹️ Stop & Translate",
        key='recorder'
    )

# When a recording is finished:
if audio_data:
    try:
        audio_bytes = audio_data['bytes']
        
        # We ask Gemini to transcribe and translate in one step
        prompt = f"Transcribe this {speaker_lang} audio and translate it to the other language. Format as: Transcript: [text] | Translation: [text]"
        
        response = model.generate_content([
            prompt,
            {'mime_type': 'audio/wav', 'data': audio_bytes}
        ])
        
        res_text = response.text.strip()

        # Check if the AI thought it was silence
        if "SILENCE" not in res_text.upper() and "|" in res_text:
            parts = res_text.split("|")
            orig = parts[0].replace("Transcript:", "").strip()
            trans = parts[1].replace("Translation:", "").strip()
            
            # Add to the bottom of the waterfall
            st.session_state['history'].append({"orig": orig, "trans": trans, "side": speaker_lang})
            st.rerun()
        elif "SILENCE" in res_text.upper():
            st.toast("No clear speech detected.")
            
    except Exception as e:
        st.error(f"Brain Error: {e}")

st.divider()

# --- BOTTOM SECTION: MANUAL RESPONSE ---
st.header("2. Your Prepared Response")
my_msg = st.text_area("Type your English reply:")

if st.button("Translate & Voice"):
    if my_msg:
        res = model.generate_content(f"Translate this to polite Japanese: {my_msg}")
        st.success(f"Japanese: {res.text}")
        
        # Generate the voice
        tts = gTTS(text=res.text, lang='ja')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        st.audio(fp)
