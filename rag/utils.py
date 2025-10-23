
import os
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.utils import embedding_functions
from rank_bm25 import BM25Okapi
from dataclasses import dataclass

@dataclass
class EmbeddingBackend:
    provider: str
    model_name: str
    _model: object = None
    batch_size: int = 32

    def ensure(self):
        if self.provider == "local":
            if self._model is None:
                self._model = SentenceTransformer(self.model_name)
                # Try to use GPU if available
                try:
                    import torch
                    if torch.cuda.is_available():
                        self._model = self._model.to('cuda')
                        print("[OK] Using GPU for embeddings")
                except ImportError:
                    pass
        elif self.provider == "openai":
            from openai import OpenAI
            self._model = OpenAI()
        return self

    def embed(self, texts):
        """Embed texts with automatic batching"""
        if isinstance(texts, str):
            texts = [texts]
        
        if self.provider == "local":
            return self._model.encode(
                texts, 
                normalize_embeddings=True,
                batch_size=self.batch_size,
                show_progress_bar=False
            ).tolist()
        elif self.provider == "openai":
            return self._embed_openai_batch(texts)
        else:
            raise ValueError("Unknown provider")
    
    def _embed_openai_batch(self, texts):
        """Batch embedding for OpenAI"""
        all_embeddings = []
        # OpenAI allows up to 2048 texts per request
        max_batch = min(self.batch_size, 2048)
        
        for i in range(0, len(texts), max_batch):
            batch = texts[i:i+max_batch]
            res = self._model.embeddings.create(
                model=os.getenv("EMBEDDINGS_MODEL","text-embedding-3-small"),
                input=batch
            )
            all_embeddings.extend([d.embedding for d in res.data])
        
        return all_embeddings
    
    def embed_batch(self, texts_list, batch_size=None):
        """Explicit batch embedding with custom batch size"""
        if batch_size:
            old_batch_size = self.batch_size
            self.batch_size = batch_size
            result = self.embed(texts_list)
            self.batch_size = old_batch_size
            return result
        return self.embed(texts_list)

def chroma_client(path):
    return chromadb.PersistentClient(path=path)

class BM25Index:
    def __init__(self, docs):
        self.docs = docs
        tokenized = [d["content"].lower().split() for d in docs]
        self.engine = BM25Okapi(tokenized)

    def search(self, query, k=200):
        scores = self.engine.get_scores(query.lower().split())
        ranked = sorted(zip(range(len(self.docs)), scores), key=lambda x: x[1], reverse=True)[:k]
        return [(self.docs[i], float(s)) for i,s in ranked]
