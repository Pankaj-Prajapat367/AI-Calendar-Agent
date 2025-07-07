import streamlit as st
import requests

st.set_page_config(page_title="AI Calendar Assistant", page_icon="📅")
st.title("🤖 AI Appointment Booking Assistant")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

backend_url = st.secrets["BACKEND_API_URL"]  # e.g. https://...onrender.com

user_input = st.text_input("You:", key="input")
submit = st.button("Send")

if submit and user_input:
    st.session_state.chat_history.append(("You", user_input))
    with st.spinner("Thinking..."):
        try:
            resp = requests.post(f"{backend_url}/agent", json={"prompt": user_input}, timeout=30)
            if resp.ok:
                reply = resp.json().get("response", "Sorry, I didn't generate a reply.")
            else:
                reply = f"Backend returned an error: {resp.status_code}"
        except Exception as e:
            reply = f"Error connecting to backend: {str(e)}"

    st.session_state.chat_history.append(("Bot", reply))

for speaker, message in st.session_state.chat_history:
    with st.chat_message(name=speaker):
        st.markdown(message)
