from PyPDF2 import PdfReader
import chromadb
from sentence_transformers import SentenceTransformer

# Initialize ChromaDB client and collection
CHROMA_PATH = "./chroma_db"
COLLECTION_NAME = "all_interview_data"
client = chromadb.PersistentClient(path=CHROMA_PATH)

# Load single collection
try:
    collection = client.get_collection(COLLECTION_NAME)
except Exception as e:
    print(f"⚠️ Error loading collection '{COLLECTION_NAME}': {e}")
    collection = None

# Initialize SentenceTransformer model once
model = SentenceTransformer("all-MiniLM-L6-v2")

def retrieve_docs_from_all_collections(query: str, k: int = 5) -> list:
    """
    Retrieves top-k relevant documents from the single ChromaDB collection.
    """
    if not collection:
        print(f"⚠️ Collection '{COLLECTION_NAME}' not available.")
        return []
    
    try:
        query_embedding = model.encode(query, show_progress_bar=False).tolist()
        results = collection.query(query_embeddings=[query_embedding], n_results=k, include=["documents"])
        return results.get("documents", [[]])[0]
    except Exception as e:
        print(f"⚠️ Error querying collection '{COLLECTION_NAME}': {e}")
        return []

def embed_and_store(ids: list, texts: list, collection_name: str = COLLECTION_NAME, chroma_path: str = CHROMA_PATH) -> None:
    """
    Embeds texts and stores them in a ChromaDB collection.
    """
    try:
        client = chromadb.PersistentClient(path=chroma_path)
        collection = client.get_or_create_collection(name=collection_name)
        embeddings = model.encode(texts, show_progress_bar=False).tolist()
        collection.add(documents=texts, embeddings=embeddings, ids=ids)
        print(f"✅ Stored {len(texts)} items in collection '{collection_name}'")
    except Exception as e:
        print(f"⚠️ Error storing in collection '{collection_name}': {e}")