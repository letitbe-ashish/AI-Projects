# from langchain_ollama import OllamaLLM
# from langchain_core.prompts import ChatPromptTemplate

# model = OllamaLLM(model="gemma3:4b")

# template = """
#     You are an assistant that helps answer questions about any topic.
#     Here is the question to answer: {question}
#     Please provide an answer to the question. keep the answers breif to safe processing time.
# """

# prompt = ChatPromptTemplate.from_template(template)
# chain = prompt | model

# while True:
#     question = input("Enter your question (or 'q' to quit): ")
#     if question.lower() == 'q':
#         break
#     print("\n\n")
#     result = chain.invoke({"question": question})
#     print(result)  

import streamlit as st
from langchain_ollama import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate

@st.cache_resource
def load_chain():

    model = OllamaLLM(model="gemma3:4b")

    template = """
    You are an assistant that helps interact and answer questions about any topic.
    Here is the message from user to answer: {question}
    Please provide response to the user.
    """

    prompt = ChatPromptTemplate.from_template(template)

    return prompt | model


chain = load_chain()

st.title("AI Assistant")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


if question := st.chat_input("Ask me anything..."):

    st.session_state.messages.append({"role": "user", "content": question})

    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            result = chain.invoke({"question": question})

        st.markdown(result)

    st.session_state.messages.append({"role": "assistant", "content": result})