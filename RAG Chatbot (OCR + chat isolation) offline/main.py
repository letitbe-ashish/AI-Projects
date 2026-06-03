import sqlite3
from typing import Annotated
from typing_extensions import TypedDict

from langchain_core.messages import BaseMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

from rag_tools import retrieve_context


llm = ChatOllama(model="llama3.2:3b", num_ctx=4096)  # Cap context window — prevents KV-cache from consuming ~11 GiB of RAM


class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    thread_id: str


def chat_node(state: ChatState):
    messages = state["messages"]
    thread_id = state.get("thread_id")
    
    # Inject RAG context if documents exist for this thread
    last_user_msg = next(
        (m.content for m in reversed(messages) if hasattr(m, "type") and m.type == "human"),
        None
    )
    if thread_id and last_user_msg:
        context = retrieve_context(thread_id, last_user_msg, k=10)
        if context:
            system = SystemMessage(content=(  # FIX: use SystemMessage, not raw dict
                "You are a helpful assistant.\n"
                "Use the following context from the user's documents when relevant:\n\n"
                f"{context}\n\n"
                "If the context is not relevant, answer from your own knowledge."
            ))
            messages = [system] + list(messages)

    return {"messages": [llm.invoke(messages)]}


# Graph setup
conn = sqlite3.connect("chatbot.db", check_same_thread=False)  # check_same_thread=False required for Streamlit
checkpointer = SqliteSaver(conn=conn)

graph = StateGraph(ChatState)
graph.add_node("chat_node", chat_node)
graph.add_edge(START, "chat_node")
graph.add_edge("chat_node", END)

chatbot = graph.compile(checkpointer=checkpointer)


def retrieve_all_threads() -> list[str]:
    return list({
        cp.config["configurable"]["thread_id"]
        for cp in checkpointer.list(None)
    })
