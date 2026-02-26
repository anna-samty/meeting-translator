import streamlit as st
import google.generativeai as genai
from streamlit_mic_recorder import mic_recorder
from gtts import gTTS
import io
import streamlit.components.v1 as components

# 1. Setup
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# Use gemini-1.5-flash for stability
model = genai.GenerativeModel(
    model_name='gemini-1.5-flash',
    system_instruction="""
    You are a strict translation engine. 
    - If input is English, you MUST output ONLY Japanese.
    - If input is Japanese, you MUST output ONLY English.
    - Format: [Original Text] | [Translated Text]
    """
)

if 'history' not in st.session_state:
    st.session_state['history'] = []
if 'last_id' not in st.session_state:
    st.session_state['last_id'] = 0

st.set_page_config(page_title="JP-EN Meeting Tool", layout="wide")

# --- STEALTH KEYBOARD CONTROL ---
components.html(
    """
    <script>
    const doc = window.parent.document;
    doc.addEventListener('keydown', function(e) {
        if (e.code === 'Space' && e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
            e.preventDefault();
            const buttons = doc.querySelectorAll('button');
            for (let btn of buttons) {
                if (btn.innerText.includes("Listening") || btn.innerText.includes("Process")) {
                    btn.click();
                    break;
                }
            }
        }
    });
    </script>
    """,
    height=0,
)

st.title("🎙️ Meeting Translator")

# --- TRANSCRIPT SECTION ---
with st.container(height=400): 
    for item in st.session_state['history']:
        with st.chat_message("user" if item['side'] == "English" else "assistant"):
            st.write(f"**{item['side']}:** {item['orig']}")
            st.caption(f"Translation: {item['trans']}")

# --- VOICE INPUT SECTION ---
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
                prompt = f"Translate this {speaker_lang} audio into {target_lang}. Use format: [Original] | [Translation]"
                
                response = model.generate_content([prompt, {'mime_type': 'audio/wav', 'data': audio_bytes}])
                res_text = response.text.strip()

                if "|" in res_text:
                    for line in res_text.splitlines():
                        if "|" in line:
                            orig, trans = line.split("|", 1)
                            st.session_state['history'].append({"orig": orig, "trans": trans, "side": speaker_lang})
                    st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

# --- MANUAL TYPING SECTION (FIXED FOR CLEAN OUTPUT) ---
st.write("---")
st.subheader("Type Your Response")
my_msg = st.text_input("Type a message to translate & speak:")

if st.button("Generate & Prepare Voice"):
    if my_msg:
        with st.spinner("Cleaning translation..."):
            target = "Japanese" if speaker_lang == "English" else "English"
            
            # THE KEY FIX: Using a specific prompt that forbids the original text
            clean_prompt = f"Provide ONLY the {target} translation of the following text. Do not include the original English, do not include brackets, and do not include the word 'Translation'. Text: {my_msg}"
            
            res = model.generate_content(clean_prompt)
            clean_result = res.text.strip()
            
            # Extra safety check: remove common labels if the AI hallucinates them
            for label in ["Translation:", "Translated Text:", "Japanese:", "English:"]:
                clean_result = clean_result.replace(label, "")
            
            st.success(clean_result.strip())
            
            voice_lang = 'ja' if target == "Japanese" else 'en'
            try:
                tts = gTTS(text=clean_result, lang=voice_lang)
                fp = io.BytesIO()
                tts.write_to_fp(fp)
                st.audio(fp, autoplay=False)
            except Exception as e:
                st.error(f"Voice error: {e}")
