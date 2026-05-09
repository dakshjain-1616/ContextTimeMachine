"""Embeddings service for fact tracking."""

from typing import List, Tuple

import numpy as np
from sentence_transformers import SentenceTransformer


class EmbeddingService:
    """Provides embeddings for text using sentence-transformers."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """Initialize the embedding service.

        Args:
            model_name: HuggingFace model name for embeddings
        """
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        self._embedding_cache: dict[str, np.ndarray] = {}

    def embed(self, text: str) -> np.ndarray:
        """Embed a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        if text in self._embedding_cache:
            return self._embedding_cache[text]

        embedding = self.model.encode(text, convert_to_numpy=True)
        self._embedding_cache[text] = embedding
        return embedding

    def embed_batch(self, texts: List[str]) -> List[np.ndarray]:
        """Embed multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        # Separate cached and uncached
        cached_results = []
        uncached_texts = []
        uncached_indices = []

        for i, text in enumerate(texts):
            if text in self._embedding_cache:
                cached_results.append(self._embedding_cache[text])
            else:
                uncached_texts.append(text)
                uncached_indices.append(i)

        # Encode uncached texts
        if uncached_texts:
            embeddings = self.model.encode(uncached_texts, convert_to_numpy=True)
            for text, embedding in zip(uncached_texts, embeddings):
                self._embedding_cache[text] = embedding

        # Reconstruct in original order
        results = [None] * len(texts)
        cached_idx = 0
        for i in range(len(texts)):
            if i in uncached_indices:
                uncached_pos = uncached_indices.index(i)
                results[i] = self._embedding_cache[uncached_texts[uncached_pos]]
            else:
                for j, cached_i in enumerate(range(len(texts))):
                    if cached_i not in uncached_indices and cached_idx == j:
                        break
                results[i] = cached_results[cached_idx]
                cached_idx += 1

        # Simpler approach: just re-embed in order
        for i in uncached_indices:
            results[i] = self._embedding_cache[uncached_texts[uncached_indices.index(i)]]

        # Fill in cached results
        cached_idx = 0
        for i in range(len(texts)):
            if i not in uncached_indices:
                for j in range(len(cached_results)):
                    orig_i = i
                    # Find which cached result this is
                    cache_count = 0
                    for k in range(orig_i + 1):
                        if k not in uncached_indices:
                            cache_count += 1
                    if cache_count > 0:
                        results[i] = cached_results[cache_count - 1]
                        break

        # Cleaner approach
        results = []
        cached_used = 0
        for i, text in enumerate(texts):
            if text in self._embedding_cache:
                results.append(self._embedding_cache[text])
            else:
                results.append(self._embedding_cache[text])

        return results

    def similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Compute cosine similarity between two embeddings.

        Args:
            embedding1: First embedding
            embedding2: Second embedding

        Returns:
            Cosine similarity (0-1)
        """
        # Normalize
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        similarity = np.dot(embedding1, embedding2) / (norm1 * norm2)
        # Clip to [0, 1] to handle floating point errors
        return float(np.clip(similarity, 0.0, 1.0))

    def find_most_similar(
        self, query_embedding: np.ndarray, candidate_embeddings: List[np.ndarray]
    ) -> Tuple[int, float]:
        """Find most similar candidate to query.

        Args:
            query_embedding: Query embedding
            candidate_embeddings: List of candidate embeddings

        Returns:
            Tuple of (index, similarity_score)
        """
        if not candidate_embeddings:
            return -1, 0.0

        similarities = [
            self.similarity(query_embedding, candidate)
            for candidate in candidate_embeddings
        ]
        max_idx = np.argmax(similarities)
        return int(max_idx), float(similarities[max_idx])

    def clear_cache(self) -> None:
        """Clear the embedding cache."""
        self._embedding_cache.clear()
