import streamlit as st
import google.generativeai as genai
import speech_recognition as sr
from gtts import gTTS
import os

# 1. Setup the "Smart Brain" using the Secret Key
# This line looks for the API key in Streamlit's "Secrets" vault later
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

# 2. Initialize the "Memory"
if 'history' not in st.session_state:
    st.session_state['history'] = []

st.set_page_config(page_title="JP-EN Meeting Tool", layout="wide")
st.title("🎙️ English-Japanese Smart Translator")

# --- TOP SECTION: TRANSCRIPT (Waterfall Style) ---
st.header("1. Conversation Transcript")

# Container for the chat history
with st.container(height=400): 
    for item in st.session_state['history']:
        with st.chat_message("user" if item['side'] == "English" else "assistant"):
            st.write(f"**{item['side']}:** {item['orig']}")
            st.caption(f"Translation: {item['trans']}")

# --- CONTROLS SECTION ---
col1, col2 = st.columns([1, 2])
with col1:
    speaker_lang = st.selectbox("Who is speaking?", ["English", "Japanese"])
    if st.button("🔴 Listen to Speaker"):
        r = sr.Recognizer()
        with sr.Microphone() as source:
            st.toast("Listening...")
            try:
                # Set timeout so it doesn't listen forever if no one speaks
                audio = r.listen(source, timeout=5, phrase_time_limit=10)
                raw_text = r.recognize_google(audio, language='en-US' if speaker_lang == "English" else 'ja-JP')
                
                # Context-Aware Translation using history
                context_str = str(st.session_state['history'][-5:]) 
                prompt = f"Previous context: {context_str}\nTranslate this to the other language: {raw_text}"
                response = model.generate_content(prompt)
                
                # Append to bottom of history
                st.session_state['history'].append({"orig": raw_text, "trans": response.text, "side": speaker_lang})
                st.rerun() 
            except Exception as e:
                st.error("Could not hear clearly or mic timed out.")

st.divider()

# --- BOTTOM SECTION: YOUR RESPONSE ---
st.header("2. Your Prepared Response")
my_msg = st.text_area("Type your English reply:")
if st.button("Translate & Voice"):
    if my_msg:
        res = model.generate_content(f"Translate this to polite Japanese: {my_msg}")
        st.session_state['last_voice'] = res.text
        st.success(f"Japanese: {res.text}")
        
        # Create Audio and show player
        tts = gTTS(text=res.text, lang='ja')
        tts.save("voice.mp3")
        st.audio("voice.mp3")
