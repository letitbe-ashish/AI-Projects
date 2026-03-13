# AI Assistant (Streamlit + LangChain + Ollama)

A simple AI chatbot built using **Streamlit**, **LangChain**, and **Ollama**.
The application allows users to ask questions and receive responses from a locally running LLM.

---

# Features

* Interactive **chat interface** using Streamlit
* Local **LLM inference using Ollama**
* Chat history maintained using **Streamlit session state**
* Simple **LangChain prompt pipeline**
* Lightweight and easy to run locally

---

# Tech Stack

* **Python**
* **Streamlit** – UI framework
* **LangChain** – LLM orchestration
* **Ollama** – Local LLM runtime
* **Gemma / TinyLlama / Qwen models**

---

# Project Structure

```
project-folder/
│
├── main.py
├── requirements.txt
└── README.md
```

---

# Installation

### 1. Create a virtual environment

```
python -m venv cb_env
```

Activate it:

**Windows**

```
cb_env\Scripts\activate
```

**Mac / Linux**

```
source cb_env/bin/activate
```

---

### 2. Install dependencies

```
pip install -r requirements.txt
```

---

# Install Ollama

Download and install Ollama from:

https://ollama.com

After installing, pull a model:

```
ollama pull gemma3:4b
```

If your system has limited RAM, use a smaller model:

```
ollama pull tinyllama
```

or

```
ollama pull qwen:0.5b
```

---

# Run the Application

Start the Streamlit app:

```
streamlit run main.py
```

The application will open in your browser:

```
http://localhost:8501
```

---

# How It Works

1. Streamlit provides the chat interface.
2. User messages are stored in `st.session_state`.
3. LangChain builds a prompt using `ChatPromptTemplate`.
4. The prompt is sent to an **Ollama LLM**.
5. The response is displayed and stored in chat history.

---

# Example Usage

1. Open the web interface.
2. Type a question in the chat input.
3. The assistant generates a response using the local LLM.

---

# Future Improvements

* Add **conversation memory**
* Implement **streaming responses**
* Add **RAG (Retrieval Augmented Generation)**
* Integrate **FastAPI backend**
* Add **vector database support**

---

# Author

Ashish Yadav
