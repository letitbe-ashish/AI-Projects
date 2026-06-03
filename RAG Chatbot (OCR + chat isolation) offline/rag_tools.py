import os
import glob

import pdfplumber
from langchain_chroma import Chroma
from langchain_community.document_loaders import TextLoader
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
import ollama


DOCS_BASE_DIR = "docs"
CHROMA_PERSIST_DIR = "./chroma_db"
IMAGE_EXTS = ["*.jpg", "*.jpeg", "*.png", "*.webp", "*.bmp"]

embeddings = OllamaEmbeddings(model="nomic-embed-text")


def get_thread_docs_path(thread_id: str) -> str:
    return os.path.join(DOCS_BASE_DIR, str(thread_id))


def ocr_image(image_path: str) -> str:
    response = ollama.chat(
        model="glm-ocr",
        messages=[{
            "role": "user",
            "content": (
                "Extract all text from this image exactly as it appears.\n"
                "Rules:\n"
                "- For tables, preserve each row on its own line with columns separated by ' | '\n"
                "- For bank statements: keep dates, descriptions, debits, credits, and balances on the same line\n"
                "- Do not summarize, interpret, or skip any text\n"
                "- Do not add headers or commentary\n"
                "- Return only the raw extracted text"
            ),
            "images": [image_path],
        }],
        options={"num_ctx": 4096},  # Cap context window to prevent KV-cache ballooning
        keep_alive=0,               # Evict glm-ocr from RAM immediately after OCR — frees ~2 GB for llama3.2:3b
    )
    return response["message"]["content"].strip()


def load_pdf_with_pdfplumber(path: str) -> list[Document]:
    """
    Extract text and tables from a PDF using pdfplumber.
    Tables are formatted as pipe-separated rows for better readability.
    Each page becomes its own Document to preserve source metadata.
    """
    docs = []
    with pdfplumber.open(path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            parts = []

            # Extract tables first and note their bounding boxes so we can
            # exclude those regions from plain-text extraction (avoids duplication)
            table_bboxes = []
            for table in page.find_tables():
                bbox = table.bbox  # (x0, top, x1, bottom)
                table_bboxes.append(bbox)

                extracted = table.extract()
                if not extracted:
                    continue

                # Format table rows as "col1 | col2 | col3"
                rows = []
                for row in extracted:
                    cleaned = [cell.strip() if cell else "" for cell in row]
                    rows.append(" | ".join(cleaned))
                parts.append("\n".join(rows))

            # Extract remaining text, filtering out table regions
            if table_bboxes:
                # Crop away table bounding boxes before extracting text
                remaining_text_parts = []
                page_bbox = (page.bbox[0], page.bbox[1], page.bbox[2], page.bbox[3])
                non_table_page = page
                for bbox in table_bboxes:
                    # Use pdfplumber's filter to exclude table chars
                    non_table_page = non_table_page.filter(
                        lambda obj, b=bbox: not (
                            obj.get("x0", 0) >= b[0]
                            and obj.get("top", 0) >= b[1]
                            and obj.get("x1", 0) <= b[2]
                            and obj.get("bottom", 0) <= b[3]
                        )
                    )
                plain_text = non_table_page.extract_text(
                    x_tolerance=2, y_tolerance=2
                )
            else:
                plain_text = page.extract_text(x_tolerance=2, y_tolerance=2)

            if plain_text and plain_text.strip():
                parts.insert(0, plain_text.strip())  # text before tables in output

            page_content = "\n\n".join(parts).strip()
            if page_content:
                docs.append(Document(
                    page_content=page_content,
                    metadata={
                        "source": path,
                        "page": page_num,
                        "type": "pdf",
                    }
                ))

    return docs


def get_vectorstore(thread_id: str) -> Chroma:
    return Chroma(
        collection_name=f"thread_{thread_id}",
        embedding_function=embeddings,
        persist_directory=CHROMA_PERSIST_DIR,
    )


def add_documents_to_thread(thread_id: str, file_paths: list[str]):
    """Load and index specific files into the thread's vectorstore."""
    docs = []

    for path in file_paths:
        ext = os.path.splitext(path)[1].lower()
        if ext == ".pdf":
            docs.extend(load_pdf_with_pdfplumber(path))
        elif ext == ".txt":
            docs.extend(TextLoader(path).load())
        elif any(path.endswith(e.lstrip("*")) for e in IMAGE_EXTS):
            text = ocr_image(path)
            docs.append(Document(
                page_content=text,
                metadata={"source": path, "type": "image"}
            ))

    if not docs:
        return

    chunks = RecursiveCharacterTextSplitter(
        chunk_size=1200, chunk_overlap=100
    ).split_documents(docs)

    vectorstore = get_vectorstore(thread_id)
    vectorstore.add_documents(chunks)


def retrieve_context(thread_id: str, query: str, k: int = 15) -> str:
    vectorstore = get_vectorstore(thread_id)

    if vectorstore._collection.count() == 0:
        return ""

    docs = vectorstore.as_retriever(search_kwargs={"k": k}).invoke(query)

    return "\n\n---\n\n".join(
        f"[Image: {os.path.basename(doc.metadata.get('source', ''))}]\n{doc.page_content}"
        if doc.metadata.get("type") == "image"
        else doc.page_content
        for doc in docs
    )
