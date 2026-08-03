
import os
import streamlit as st
from groq import Groq

st.set_page_config(page_title="Nex AI Agent", page_icon="🤖")

st.title("🤖 Nex AI Agent")
st.write("Asisten AI pintar siap membantumu!")

# Ambil API Key dari Streamlit Secrets atau Environment Variables
groq_api_key = os.environ.get("GROQ_API_KEY")

if not groq_api_key:
    try:
        groq_api_key = st.secrets["GROQ_API_KEY"]
    except:
        pass

if not groq_api_key:
    groq_api_key = st.sidebar.text_input("Masukkan Groq API Key:", type="password")

if not groq_api_key:
    st.warning("⚠️ Masukkan Groq API Key terlebih dahulu di sidebar atau secrets!")
else:
    client = Groq(api_key=groq_api_key)
    
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Tulis pesanmu di sini..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            response_stream = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": m["role"], "content": m["content"]} for m in st.session_state.messages],
                stream=True,
            )
            response = st.write_stream(chunk.choices[0].delta.content or "" for chunk in response_stream)
        st.session_state.messages.append({"role": "assistant", "content": response})
