import streamlit as st
import google.generativeai as genai
from streamlit_mic_recorder import mic_recorder
from gtts import gTTS
import io
import streamlit.components.v1 as components

# 1. Setup
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# MODEL A: For the Transcript (keeps the [Original] | [Translation] format)
transcript_model = genai.GenerativeModel(
    model_name='gemini-2.5-flash',
    system_instruction="You are a strict translation engine. Format: [Original Text] | [Translated Text]"
)

# MODEL B: For Manual Typing (Pure Translation ONLY)
manual_model = genai.GenerativeModel(
    model_name='gemini-1.5-flash'
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

# --- VOICE INPUT SECTION (Uses Transcript Model) ---
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
        with st.spinner("Processing..."):
            try:
                target_lang = "Japanese" if speaker_lang == "English" else "English"
                response = transcript_model.generate_content([
                    f"Translate this {speaker_lang} audio into {target_lang}.",
                    {'mime_type': 'audio/wav', 'data': audio_data['bytes']}
                ])
                res_text = response.text.strip()
                if "|" in res_text:
                    for line in res_text.splitlines():
                        if "|" in line:
                            orig, trans = line.split("|", 1)
                            st.session_state['history'].append({"orig": orig, "trans": trans, "side": speaker_lang})
                    st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

# --- MANUAL TYPING SECTION (Uses Manual Model for Pure Output) ---
st.write("---")
st.subheader("Type Your Response")
my_msg = st.text_input("Type a message to translate & speak:")

if st.button("Generate & Prepare Voice"):
    if my_msg:
        with st.spinner("Translating..."):
            target = "Japanese" if speaker_lang == "English" else "English"
            
            # Use the Manual Model with a very strict one-time prompt
            clean_res = manual_model.generate_content(
                f"Translate the following text into {target}. "
                f"Output ONLY the translated text. Do not include the original text, "
                f"do not use brackets, and do not provide any explanation. "
                f"Text to translate: {my_msg}"
            )
            
            final_text = clean_res.text.strip()
            
            # Final cleaning just in case the AI includes the prompt text
            if "|" in final_text:
                final_text = final_text.split("|")[-1].strip()
            
            st.success(final_text)
            
            # Generate Audio
            voice_lang = 'ja' if target == "Japanese" else 'en'
            try:
                tts = gTTS(text=final_text, lang=voice_lang)
                fp = io.BytesIO()
                tts.write_to_fp(fp)
                st.audio(fp, autoplay=False)
            except Exception as e:
                st.error(f"Voice error: {e}")
