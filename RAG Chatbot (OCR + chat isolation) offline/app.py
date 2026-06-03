import os
import uuid

import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage

from main import chatbot, retrieve_all_threads
from rag_tools import get_thread_docs_path, add_documents_to_thread


# --- Helpers ---

def new_thread_id() -> str:
    return str(uuid.uuid4())


def reset_chat():
    st.session_state.thread_id = new_thread_id()
    st.session_state.messages = []
    if st.session_state.thread_id not in st.session_state.threads:
        st.session_state.threads.append(st.session_state.thread_id)


def load_conversation(thread_id: str) -> list[dict]:
    state = chatbot.get_state(config={"configurable": {"thread_id": thread_id}})
    return [
        {"role": "user" if isinstance(m, HumanMessage) else "assistant", "content": m.content}
        for m in state.values.get("messages", [])
    ]


# --- Session state init ---

if "thread_id" not in st.session_state:
    st.session_state.thread_id = new_thread_id()

if "messages" not in st.session_state:
    st.session_state.messages = []

if "threads" not in st.session_state:
    st.session_state.threads = retrieve_all_threads()
    if st.session_state.thread_id not in st.session_state.threads:
        st.session_state.threads.append(st.session_state.thread_id)


# --- Sidebar ---

st.sidebar.title("Chatbot")

if st.sidebar.button("New Chat"):
    reset_chat()

st.sidebar.caption(f"Thread: `{st.session_state.thread_id[:8]}...`")

st.sidebar.header("📄 Upload Documents")
uploaded_files = st.sidebar.file_uploader(
    "PDF, TXT, or images",
    type=["pdf", "txt", "jpg", "jpeg", "png", "webp", "bmp"],
    accept_multiple_files=True,
    key=f"uploader_{st.session_state.thread_id}",
)

if uploaded_files:
    thread_docs_path = get_thread_docs_path(st.session_state.thread_id)
    os.makedirs(thread_docs_path, exist_ok=True)

    saved_paths = []
    for f in uploaded_files:
        path = os.path.join(thread_docs_path, f.name)
        with open(path, "wb") as out:
            out.write(f.getbuffer())
        saved_paths.append(path)

    # FIX: index all new files in one call, adding to existing collection
    add_documents_to_thread(st.session_state.thread_id, saved_paths)

    for f in uploaded_files:
        st.sidebar.success(f"✓ {f.name}")

st.sidebar.header("Conversations")
for tid in reversed(st.session_state.threads):
    if st.sidebar.button(f"{tid[:8]}...", key=tid):
        st.session_state.thread_id = tid
        st.session_state.messages = load_conversation(tid)


# --- Chat UI ---

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if user_input := st.chat_input("Type here"):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    config = {"configurable": {"thread_id": st.session_state.thread_id}}

    with st.chat_message("assistant"):
        response = st.write_stream(
            chunk.content
            for chunk, _ in chatbot.stream(
                {"messages": [HumanMessage(content=user_input)], "thread_id": st.session_state.thread_id},
                config=config,
                stream_mode="messages",
            )
            if isinstance(chunk, AIMessage)
        )

    st.session_state.messages.append({"role": "assistant", "content": response})
