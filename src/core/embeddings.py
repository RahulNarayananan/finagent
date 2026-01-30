
from langchain_ollama import OllamaEmbeddings
import os
from langchain_ollama import OllamaEmbeddings
import os
from functools import lru_cache

@lru_cache(maxsize=1)
def get_embedding_model():
    """Initializes the Ollama Embedding Model."""
    base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    return OllamaEmbeddings(model="nomic-embed-text", base_url=base_url)

def generate_embedding(text: str):
    """Generates an embedding vector for the given text."""
    model = get_embedding_model()
    return model.embed_query(text)
