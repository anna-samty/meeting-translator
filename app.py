import streamlit as st
import google.generativeai as genai
from streamlit_mic_recorder import mic_recorder
from gtts import gTTS
import io

# 1. Setup
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel(
    model_name='gemini-3-flash-preview',
    system_instruction="""
    You are a professional translator focusing on clarity. 
    1. Listen to the audio and provide a clean, punctuated transcript.
    2. Break distinct thoughts into separate sentences. 
    3. Provide the translation for each sentence.
    4. Format: [Original Sentence] | [Translated Sentence]
    """
)

if 'history' not in st.session_state:
    st.session_state['history'] = []

st.set_page_config(page_title="Clear Sentence Translator", layout="wide")
st.title("🎙️ Sentence-by-Sentence Translator")

# --- 1. TRANSCRIPT DISPLAY ---
st.subheader("Conversation Flow")
with st.container(height=400):
    for item in st.session_state['history']:
        # We display each translation as a clean block
        st.markdown(f"**{item['side']}:** {item['orig']}")
        st.markdown(f"*{item['trans']}*")
        st.write("---")

# --- 2. CAPTURE SECTION ---
st.divider()
col1, col2 = st.columns([1, 2])

with col1:
    speaker_lang = st.selectbox("Language being spoken:", ["English", "Japanese"])
    audio_data = mic_recorder(
        start_prompt=f"Record {speaker_lang}", 
        stop_prompt="Stop & Process Sentences", 
        key='sentence_mic'
    )

if audio_data:
    with st.spinner("Breaking down sentences..."):
        try:
            target_lang = "Japanese" if speaker_lang == "English" else "English"
            # We explicitly tell the AI to look for sentence breaks
            prompt = f"Transcribe this {speaker_lang} audio into clear, punctuated sentences and translate them into {target_lang}."
            
            response = model.generate_content([
                prompt,
                {'mime_type': 'audio/wav', 'data': audio_data['bytes']}
            ])
            
            res_text = response.text.strip()
            if "|" in res_text:
                # If the AI sends multiple lines, we process them all
                lines = res_text.split("\n")
                for line in lines:
                    if "|" in line:
                        orig, trans = line.split("|", 1)
                        st.session_state['history'].append({
                            "orig": orig.strip(), 
                            "trans": trans.strip(), 
                            "side": speaker_lang
                        })
                st.rerun()
        except Exception as e:
            st.error(f"Try a shorter recording. Error: {e}")

# --- 3. MANUAL TYPING ---
st.divider()
st.subheader("Send a Message")
m_lang = st.radio("I am typing in:", ["English", "Japanese"], horizontal=True)
my_msg = st.text_input(f"Type your {m_lang} reply:")

if st.button("Speak Now"):
    if my_msg:
        target = "polite Japanese" if m_lang == "English" else "natural English"
        res = model.generate_content(f"Translate to {target}. ONLY the text: {my_msg}")
        clean = res.text.strip()
        st.success(clean)
        
        v_lang = 'ja' if m_lang == "English" else 'en'
        tts = gTTS(text=clean, lang=v_lang)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        st.audio(fp
