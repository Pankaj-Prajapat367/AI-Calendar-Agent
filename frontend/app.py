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
        response = requests.post(
            "http://localhost:8000/agent", json={"prompt": user_input}
        )
        if response.ok:
            reply = response.json()["response"]
        else:
            reply = "Sorry, there was an error processing your request."

    st.session_state.chat_history.append(("Bot", reply))

for speaker, message in st.session_state.chat_history:
    with st.chat_message(name=speaker):
        st.markdown(message)
