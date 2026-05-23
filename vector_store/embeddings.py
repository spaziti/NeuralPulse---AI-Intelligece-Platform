import hashlib
import json
import logging
import asyncio
from typing import List
import requests
import numpy as np

from backend.app.config import settings
from backend.app.redis_client import redis_client

logger = logging.getLogger("neuralpulse.vector_store.embeddings")


class EmbeddingsService:
    def __init__(self) -> None:
        self.openai_key = settings.OPENAI_API_KEY
        self.openai_url = "https://api.openai.com/v1/embeddings"
        self.cache_expiry = 2592000  # 30 days cache expiration (in seconds)
        self.dimension = 1536

    def _generate_deterministic_mock(self, text: str) -> List[float]:
        """Generates a deterministic 1536-dimensional L2-normalized float vector fallback."""
        vector = np.zeros(self.dimension)
        if not text:
            return vector.tolist()

        # Hash entire text to generate base seed
        hash_obj = hashlib.sha256(text.encode("utf-8"))
        seed = int(hash_obj.hexdigest(), 16) % (2**32 - 1)

        # Seed random number generator deterministically
        rng = np.random.default_rng(seed)
        vector = rng.normal(0.0, 1.0, self.dimension)

        # Add vocabulary weight overlap: hash individual words and increment respective indices
        words = text.lower().split()
        for word in words:
            w_hash = hashlib.md5(word.encode("utf-8")).hexdigest()
            w_idx = int(w_hash, 16) % self.dimension
            vector[w_idx] += 1.0

        # Apply L2 normalization
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm

        return vector.tolist()

    async def _fetch_openai_embedding(self, text: str) -> List[float]:
        """Call OpenAI embeddings API in a non-blocking thread executor."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.openai_key}",
        }
        payload = {
            "model": "text-embedding-3-small",
            "input": text,
        }

        loop = asyncio.get_running_loop()

        def make_post():
            return requests.post(self.openai_url, json=payload, headers=headers, timeout=10)

        response = await loop.run_in_executor(None, make_post)
        response.raise_for_status()
        
        res_json = response.json()
        return res_json["data"][0]["embedding"]

    async def get_embedding(self, text: str) -> List[float]:
        """Retrieve L2-normalized 1536-dimensional vector, checking Redis cache first."""
        if not text:
            return [0.0] * self.dimension

        # Generate unique cache key based on text hash
        text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        cache_key = f"np:emb:{text_hash}"

        # 1. Check Redis Cache
        try:
            cached_val = await redis_client.get(cache_key)
            if cached_val:
                logger.debug(f"Redis cache hit for embedding key: {cache_key}")
                return json.loads(cached_val)
        except Exception as e:
            logger.warning(f"Error checking embedding cache in Redis: {e}")

        # 2. Generate Embedding
        embedding: List[float]
        if self.openai_key:
            try:
                embedding = await self._fetch_openai_embedding(text)
                logger.info("Successfully fetched embedding from OpenAI API")
            except Exception as e:
                logger.error(f"OpenAI embedding generation failed: {e}. Falling back to mock vectorizer.")
                embedding = self._generate_deterministic_mock(text)
        else:
            logger.debug("No OpenAI API key found. Using deterministic mock vectorizer.")
            embedding = self._generate_deterministic_mock(text)

        # 3. Store in Redis Cache
        try:
            await redis_client.set(cache_key, json.dumps(embedding), ex=self.cache_expiry)
        except Exception as e:
            logger.warning(f"Failed to cache embedding in Redis: {e}")

        return embedding


embeddings_service = EmbeddingsService()
