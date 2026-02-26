import streamlit as st
import google.generativeai as genai
from streamlit_mic_recorder import mic_recorder
from gtts import gTTS
import io

# 1. Setup
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# Use the latest flash model for speed
model = genai.GenerativeModel(
    model_name='gemini-2.5-flash', # 2.0/2.5 Flash is significantly faster for 'live' feels
    system_instruction="""
    You are a strict translation engine. 
    - If input is English, output ONLY Japanese.
    - If input is Japanese, output ONLY English.
    - Format: [Original Text] | [Translated Text]
    """
)

if 'history' not in st.session_state:
    st.session_state['history'] = []
if 'last_id' not in st.session_state:
    st.session_state['last_id'] = 0

st.set_page_config(page_title="JP-EN Live-ish Tool", layout="wide")
st.title("🎙️ Meeting Translator (Streaming)")

# --- TRANSCRIPT DISPLAY ---
transcript_container = st.container(height=400)
with transcript_container: 
    for item in st.session_state['history']:
        with st.chat_message("user" if item['side'] == "English" else "assistant"):
            st.write(f"**{item['side']}:** {item['orig']}")
            st.caption(f"Translation: {item['trans']}")

# --- THE RECORDER ---
st.write("---")
speaker_lang = st.selectbox("Current Speaker Language:", ["English", "Japanese"])

# Just_once=True is key for stability in Streamlit
audio_data = mic_recorder(
    start_prompt="🔴 Start Listening",
    stop_prompt="⏹️ Stop & Translate",
    just_once=True, 
    key='recorder'
)

if audio_data:
    new_id = audio_data.get('id')
    if new_id != st.session_state['last_id']:
        st.session_state['last_id'] = new_id
        
        # Create a placeholder for the "Live" typing effect
        with st.chat_message("assistant"):
            status_placeholder = st.empty()
            streaming_placeholder = st.empty()
            
            status_placeholder.markdown("*Processing audio...*")
            
            try:
                audio_bytes = audio_data['bytes']
                target_lang = "Japanese" if speaker_lang == "English" else "English"
                prompt = f"Translate this {speaker_lang} audio into {target_lang}. Format: [Original] | [Translation]"
                
                # --- START STREAMING ---
                # 'stream=True' makes Gemini send bits of text as they are generated
                response = model.generate_content(
                    [prompt, {'mime_type': 'audio/wav', 'data': audio_bytes}],
                    stream=True 
                )
                
                full_response_text = ""
                status_placeholder.markdown(f"*Translating to {target_lang}...*")
                
                for chunk in response:
                    full_response_text += chunk.text
                    # Update the UI instantly with the partial text
                    streaming_placeholder.write(full_response_text)
                
                # --- POST-PROCESSING ---
                if "|" in full_response_text:
                    orig, trans = full_response_text.split("|", 1)
                    st.session_state['history'].append({
                        "orig": orig.strip(), 
                        "trans": trans.strip(), 
                        "side": speaker_lang
                    })
                    # Clear placeholders before rerun
                    status_placeholder.empty()
                    streaming_placeholder.empty()
                    st.rerun()
                    
            except Exception as e:
                st.error(f"Error: {e}")

# --- MANUAL TYPING (Same as your original) ---
st.write("---")
my_msg = st.text_input("Type a message to translate & speak:")
if st.button("Speak Now"):
    if my_msg:
        target = "Japanese" if speaker_lang == "English" else "English"
        res = model.generate_content(f"Translate to {target}, output ONLY translation: {my_msg}")
        clean = res.text.strip()
        st.success(clean)
        
        voice_lang = 'ja' if target == "Japanese" else 'en'
        tts = gTTS(text=clean, lang=voice_lang)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        st.audio(fp, autoplay=True)
