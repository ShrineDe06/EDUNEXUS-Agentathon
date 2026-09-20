import os
import json
import faiss
import fitz  # PyMuPDF
from sentence_transformers import SentenceTransformer

class SyllabusMemory:
    _model_cache = {}
    def __init__(
        self, 
        persist_dir="backend/data/syllabus", 
        model_name="all-MiniLM-L6-v2", 
        chunk_size=800, 
        chunk_overlap=100
    ):
        """
        Initializes the SyllabusMemory with a lightweight embedding model and FAISS index.
        """
        self.persist_dir = persist_dir
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Ensure persistence directory exists
        os.makedirs(self.persist_dir, exist_ok=True)
        
        # Load lightweight sentence transformer
        if model_name not in self._model_cache:
            self._model_cache[model_name] = SentenceTransformer(model_name)
        self.model = self._model_cache[model_name]
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        
        self.index_path = os.path.join(self.persist_dir, "faiss.index")
        self.metadata_path = os.path.join(self.persist_dir, "metadata.json")
        
        self.index = None
        self.metadata = []
        
        self.load()

    def load(self):
        """Loads FAISS index and metadata from disk if they exist."""
        if os.path.exists(self.index_path) and os.path.exists(self.metadata_path):
            self.index = faiss.read_index(self.index_path)
            with open(self.metadata_path, 'r', encoding='utf-8') as f:
                self.metadata = json.load(f)
        else:
            self.reset()

    def reset(self):
        """Clears the FAISS index and metadata from memory and disk."""
        self.index = faiss.IndexFlatIP(self.embedding_dim)
        self.metadata = []
        if os.path.exists(self.index_path):
            os.remove(self.index_path)
        if os.path.exists(self.metadata_path):
            os.remove(self.metadata_path)

    def save(self):
        """Persists the current FAISS index and metadata to disk."""
        faiss.write_index(self.index, self.index_path)
        with open(self.metadata_path, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, ensure_ascii=False, indent=2)

    def delete_documents(self, doc_names: list):
        """Removes all chunks for the specified document names and rebuilds the FAISS index."""
        if not doc_names or not self.metadata:
            return
        doc_set = set(doc_names)
        remaining_chunks = [c for c in self.metadata if c.get("document") not in doc_set]
        if len(remaining_chunks) == len(self.metadata):
            return
        
        self.metadata = remaining_chunks
        self.index = faiss.IndexFlatIP(self.embedding_dim)
        if remaining_chunks:
            texts = [c["text"] for c in remaining_chunks]
            embeddings = self.model.encode(texts, convert_to_numpy=True)
            faiss.normalize_L2(embeddings)
            self.index.add(embeddings)
        self.save()

    def _chunk_text(self, text: str, page_num: int, doc_name: str) -> list:
        """Splits text into chunks of specified size and overlap."""
        chunks = []
        start = 0
        text_length = len(text)
        
        while start < text_length:
            end = start + self.chunk_size
            chunk = text[start:end]
            
            chunks.append({
                "text": chunk,
                "page": page_num,
                "document": doc_name
            })
            
            start += self.chunk_size - self.chunk_overlap
            
        return chunks

    def ingest_pdf(self, pdf_path: str):
        """
        Reads a PDF, chunks the text, creates embeddings, and stores them in FAISS.
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
            
        doc_name = os.path.basename(pdf_path)
        doc = fitz.open(pdf_path)
        
        all_chunks = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            if not text or not text.strip():
                continue
                
            page_chunks = self._chunk_text(text, page_num + 1, doc_name)
            all_chunks.extend(page_chunks)
            
        if not all_chunks:
            raise ValueError(f"No extractable text found in PDF: {pdf_path}")
            
        self._add_chunks(all_chunks)

    def add_text(self, text: str, source_name: str = "raw_text", page: int = 1):
        """
        Manually injects text chunks into the memory.
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
            
        chunks = self._chunk_text(text, page, source_name)
        self._add_chunks(chunks)

    def _add_chunks(self, chunks: list):
        """Generates embeddings, normalizes them, and adds to FAISS index."""
        texts = [chunk["text"] for chunk in chunks]
        
        try:
            embeddings = self.model.encode(texts, convert_to_numpy=True)
            # Normalize embeddings so that Inner Product acts as Cosine Similarity
            faiss.normalize_L2(embeddings)
            
            self.index.add(embeddings)
            self.metadata.extend(chunks)
            self.save()
        except Exception as e:
            raise RuntimeError(f"Failed to generate embeddings or store chunks: {e}")

    def retrieve(self, query: str, top_k: int = 5) -> str:
        """
        Finds the top-K chunks most similar to the query and formats them as a context string.
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
            
        if self.index is None or self.index.ntotal == 0:
            raise RuntimeError("Cannot retrieve: no documents have been ingested yet.")
            
        if top_k <= 0:
            raise ValueError("top_k must be > 0")

        # Encode and normalize query
        query_embedding = self.model.encode([query], convert_to_numpy=True)
        faiss.normalize_L2(query_embedding)
        
        k = min(top_k, self.index.ntotal)
        
        distances, indices = self.index.search(query_embedding, k)
        
        context_parts = []
        for idx in indices[0]:
            if idx == -1:
                continue
            chunk_meta = self.metadata[idx]
            context_parts.append(
                f"[Document: {chunk_meta['document']} | Page {chunk_meta['page']}]\n"
                f"{chunk_meta['text'].strip()}"
            )
            
        return "\n\n".join(context_parts)

    def search(self, query: str, top_k: int = 5) -> list:
        """
        Finds the top-K chunks and returns list of metadata dicts.
        """
        if not query or not query.strip() or self.index is None or self.index.ntotal == 0:
            return []
        try:
            query_embedding = self.model.encode([query], convert_to_numpy=True)
            faiss.normalize_L2(query_embedding)
            k = min(top_k, self.index.ntotal)
            distances, indices = self.index.search(query_embedding, k)
            results = []
            for idx in indices[0]:
                if 0 <= idx < len(self.metadata):
                    results.append(self.metadata[idx])
            return results
        except Exception:
            return []
