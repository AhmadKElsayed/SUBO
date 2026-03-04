import os
from langchain_core.tools import tool
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

DATA_DIR = os.path.join(os.getcwd(), "data")
FAISS_PATH = os.path.join(DATA_DIR, "faiss_index")
PDF_PATH = os.path.join(DATA_DIR, "INTERNATIONAL TARIFF GENERAL RULES.pdf")

embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")
_retriever = None

def init_rag_index():
    global _retriever
    if os.path.exists(FAISS_PATH):
        print("Loading existing FAISS index...")
        vectorstore = FAISS.load_local(FAISS_PATH, embeddings, allow_dangerous_deserialization=True)
    else:
        print("FAISS index not found. Building from PDF...")
        if not os.path.exists(PDF_PATH):
            raise FileNotFoundError(f"Missing PDF for RAG: Please place {PDF_PATH}")
        loader = PyPDFLoader(PDF_PATH)
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        vectorstore = FAISS.from_documents(text_splitter.split_documents(loader.load()), embeddings)
        vectorstore.save_local(FAISS_PATH)
    
    _retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

@tool
def search_airline_policies(query: str) -> str:
    """Search the Light Airlines Conditions of Carriage document for policies."""
    if _retriever is None:
        init_rag_index()
    
    docs = _retriever.invoke(query)
    if not docs: return "No relevant policies found."
    
    return "\n".join([f"--- Document {i+1} ---\n{doc.page_content}" for i, doc in enumerate(docs)])

rag_tools_list = [search_airline_policies]