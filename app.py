import streamlit as st
import google.generativeai as genai
from streamlit_mic_recorder import mic_recorder
from gtts import gTTS
import io

# 1. Setup
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

model = genai.GenerativeModel(
    model_name='gemini-2.5-flash',
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

st.set_page_config(page_title="JP-EN Meeting Tool", layout="wide")
st.title("🎙️ Meeting Translator")

# --- TRANSCRIPT ---
with st.container(height=400): 
    for item in st.session_state['history']:
        with st.chat_message("user" if item['side'] == "English" else "assistant"):
            st.write(f"**{item['side']}:** {item['orig']}")
            st.caption(f"Translation: {item['trans']}")

# --- THE RECORDER ---
st.write("---")
speaker_lang = st.selectbox("Current Speaker Language:", ["English", "Japanese"])

audio_data = mic_recorder(
    start_prompt="🔴 Start Listening",
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
                
                # Instruction to handle multiple sentences in one recording
                prompt = f"Transcribe and translate this {speaker_lang} audio into {target_lang}. Split different thoughts into new lines using the [Original] | [Translation] format."
                
                response = model.generate_content([prompt, {'mime_type': 'audio/wav', 'data': audio_bytes}])
                res_text = response.text.strip()

                if "SILENCE" not in res_text.upper():
                    # This 'splitlines' logic handles multiple sentences if they exist
                    for line in res_text.splitlines():
                        if "|" in line:
                            orig, trans = line.split("|", 1)
                            st.session_state['history'].append({
                                "orig": orig.strip(), 
                                "trans": trans.strip(), 
                                "side": speaker_lang
                            })
                    st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

# --- MANUAL TYPING SECTION ---
st.write("---")
my_msg = st.text_input("Type a message to translate & speak:")
if st.button("Speak Now"):
    if my_msg:
        target = "Japanese" if speaker_lang == "English" else "English"
        # Force the AI to be concise for the voice output
        res = model.generate_content(f"Translate to {target}. Output ONLY the translation text: {my_msg}")
        clean = res.text.strip()
        st.success(clean)
        
        voice_lang = 'ja' if target == "Japanese" else 'en'
        tts = gTTS(text=clean, lang=voice_lang)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        st.audio(fp, autoplay=True)
