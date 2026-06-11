from sentence_transformer import SentenceTransformer

class BGEEmbedder:
    def __init__(self, model_name: str = "BAAI/bge-base-en-v1.5"):
        self.model = SentenceTransformer(model_name)
        self.dim = 768
    
    def embed(self, texts: list[str]) -> list[list[float]]:
        return self.model.encode(texts, normalize_embeddings=True).tolist()
    
    def embed_query(self, query: str) -> list[float]:
        prefixed = f"Represent this sentence for searching relevant passages: {query}"
        return self.embed([prefixed])[0]