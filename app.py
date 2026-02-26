import streamlit as st
import google.generativeai as genai
from streamlit_mic_recorder import mic_recorder
from gtts import gTTS
import io
import streamlit.components.v1 as components  # Added this back

# 1. Setup
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

model = genai.GenerativeModel(
    model_name='gemini-1.5-flash', # Corrected to stable version
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

st.set_page_config(page_title="JP-EN Stealth Tool", layout="wide")

# --- KEYBOARD SHORTCUT (Spacebar to Record) ---
components.html(
    """
    <script>
    const doc = window.parent.document;
    doc.addEventListener('keydown', function(e) {
        if (e.code === 'Space' && e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
            e.preventDefault();
            const buttons = doc.querySelectorAll('button');
            for (let btn of buttons) {
                if (btn.innerText.includes("Record") || btn.innerText.includes("Process")) {
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

st.title("🎙️ Meeting Translator (Stealth Mode)")
st.caption("Tip: Press **Spacebar** to Start/Stop recording (ensure you aren't typing in a box).")

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
    start_prompt="🔴 Record Speech",
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
                prompt = f"Transcribe and translate this {speaker_lang} audio into {target_lang}. Split thoughts into lines using: [Original] | [Translation]"
                
                response = model.generate_content([prompt, {'mime_type': 'audio/wav', 'data': audio_bytes}])
                res_text = response.text.strip()

                if "SILENCE" not in res_text.upper():
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

# --- MANUAL TYPING ---
st.write("---")
st.subheader("Type Your Response")
my_msg = st.text_input("Type a message to translate & speak:")

if st.button("Generate & Prepare Voice"):
    if my_msg:
        with st.spinner("Translating..."):
            target = "Japanese" if speaker_lang == "English" else "English"
            res = model.generate_content(f"Translate to {target}. ONLY translation text: {my_msg}")
            clean_result = res.text.strip()
            
            st.success(clean_result)
            
            voice_lang = 'ja' if target == "Japanese" else 'en'
            tts = gTTS(text=clean_result, lang=voice_lang)
            fp = io.BytesIO()
            tts.write_to_fp(fp)
            # autoplay=False ensures it only plays when you click
            st.audio(fp, autoplay=False)
