import streamlit as st

from backend.db import init_db
from backend.repository import (
    save_message,
    get_sessions_for_user,
    get_conversation,
)
from backend.rag import answer_with_rag


# Initialize DB schema (idempotent)
init_db()

st.set_page_config(page_title="RAG Chatbot", page_icon="💬")

st.title("💬 RAG Chatbot")
st.write(
    "Ask questions about the indexed PDFs. "
    "Each question uses RAG (retrieval-augmented generation) and "
    "conversation history stored in Postgres."
)


# -----------------------------
# Sidebar: user & session management
# -----------------------------
st.sidebar.header("User & Sessions")

default_user = "student1"
user_id = st.sidebar.text_input("User ID", value=default_user)

# Load sessions for this user
sessions = get_sessions_for_user(user_id)

if "current_session" not in st.session_state:
    st.session_state.current_session = sessions[0] if sessions else "session-1"

# Create / switch to a new session
new_session_name = st.sidebar.text_input("Create / switch to session ID", value="")
if st.sidebar.button("Activate session"):
    if new_session_name.strip():
        st.session_state.current_session = new_session_name.strip()

# List existing sessions as quick buttons
st.sidebar.subheader("Existing sessions")
if sessions:
    for s in sessions:
        if st.sidebar.button(s):
            st.session_state.current_session = s
else:
    st.sidebar.info("No sessions yet for this user. A new one will be created automatically.")

session_id = st.session_state.current_session

st.write(f"**User:** `{user_id}`  |  **Session:** `{session_id}`")


# -----------------------------
# Load and display conversation history
# -----------------------------
messages = get_conversation(user_id, session_id, limit=50)

for m in messages:
    role = m["role"]
    content = m["content"]
    with st.chat_message("user" if role == "user" else "assistant"):
        st.markdown(content)


# -----------------------------
# Chat input & RAG response
# -----------------------------
prompt = st.chat_input("Ask a question about the documents...")

if prompt:
    # 1) Show user message
    save_message(user_id, session_id, "user", prompt)
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2) Get updated history for RAG (including this new user msg)
    history = get_conversation(user_id, session_id, limit=50)

    # 3) Call RAG pipeline
    with st.chat_message("assistant"):
        with st.spinner("Thinking with RAG..."):
            answer = answer_with_rag(
                user_id=user_id,
                session_id=session_id,
                query=prompt,
                history=history,
            )
            st.markdown(answer)

    # 4) Persist assistant answer
    save_message(user_id, session_id, "assistant", answer)
