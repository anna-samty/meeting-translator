import streamlit as st
import google.generativeai as genai
from streamlit_mic_recorder import mic_recorder
from gtts import gTTS
import io

# 1. Setup with AGGRESSIVE language rules
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

model = genai.GenerativeModel(
    model_name='gemini-2.5-flash',
    system_instruction="""
    You are a strict translation engine. 
    - If input is English, you MUST output ONLY Japanese.
    - If input is Japanese, you MUST output ONLY English.
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

# 'just_once=True' ensures it processes once and doesn't repeat the sentence
audio_data = mic_recorder(
    start_prompt="🔴 Start Listening",
    stop_prompt="⏹️ Process Now",
    just_once=True, 
    key='recorder'
)

# Logic to catch the audio as soon as 'Stop' is pressed
if audio_data:
    # Use the unique ID from the recorder to prevent duplicates
    new_id = audio_data.get('id')
    if new_id != st.session_state['last_id']:
        st.session_state['last_id'] = new_id
        
        with st.spinner("Translating..."):
            try:
                audio_bytes = audio_data['bytes']
                # Force the direction in the prompt too
                target_lang = "Japanese" if speaker_lang == "English" else "English"
                prompt = f"Translate this {speaker_lang} audio into {target_lang}. Format: [Original] | [Translation]"
                
                response = model.generate_content([prompt, {'mime_type': 'audio/wav', 'data': audio_bytes}])
                res_text = response.text.strip()

                if "|" in res_text and "SILENCE" not in res_text.upper():
                    orig, trans = res_text.split("|", 1)
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
        # Determine direction based on the speaker_lang dropdown
        target = "Japanese" if speaker_lang == "English" else "English"
        
        # FIX: We use a specific prompt to override the global system instructions
        prompt_override = (
            f"OVERRIDE SYSTEM FORMAT. Translate the following text into {target}. "
            f"Do NOT include the original text. Do NOT use '|'. "
            f"Output ONLY the translated string: {my_msg}"
        )
        
        res = model.generate_content(prompt_override)
        clean = res.text.strip()
        
        # Further safety: If the model still slips up, we grab only the second part
        if "|" in clean:
            clean = clean.split("|")[-1].strip()

        st.success(clean)
        
        voice_lang = 'ja' if target == "Japanese" else 'en'
        tts = gTTS(text=clean, lang=voice_lang)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        st.audio(fp, autoplay=True)
