import streamlit as st
import requests

st.set_page_config(page_title="AI Calendar Assistant", page_icon="📅")
st.title("🤖 AI Appointment Booking Assistant")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

user_input = st.text_input("You:", key="input")
submit = st.button("Send")

if submit and user_input:
    st.session_state.chat_history.append(("You", user_input))

    with st.spinner("Thinking..."):
        try:
            response = requests.post(
                st.secrets["BACKEND_API_URL"],  # Use production-ready backend URL
                json={"prompt": user_input},
                timeout=30  # Optional: avoids long hangs
            )
            if response.ok:
                data = response.json()
                reply = data.get("response") or data.get("output") or data.get("content") or " Appointment processed."
            else:
                reply = f" Backend returned an error: {response.status_code}"
        except Exception as e:
            reply = f" Could not connect to backend. Error: {str(e)}"

    st.session_state.chat_history.append(("Bot", reply))

# Render chat history
for speaker, message in st.session_state.chat_history:
    with st.chat_message(name=speaker):
        st.markdown(message)
