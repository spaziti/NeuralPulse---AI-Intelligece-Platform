import logging
from typing import Any, Dict, List, Optional
import chromadb
from chromadb.config import Settings
from backend.app.config import settings

logger = logging.getLogger("neuralpulse.vector_store")


class ChromaDBClient:
    def __init__(self):
        self.host = settings.CHROMA_HOST
        self.port = settings.CHROMA_PORT
        self.collection_name = settings.CHROMA_COLLECTION_NAME
        self._client = None
        self._collection = None

    def _get_client(self) -> chromadb.HttpClient:
        """Lazy loader for ChromaDB HttpClient."""
        if self._client is None:
            try:
                self._client = chromadb.HttpClient(
                    host=self.host,
                    port=str(self.port),
                    settings=Settings(anonymized_telemetry=False)
                )
                logger.info("ChromaDB Client connection established")
            except Exception as e:
                logger.error(f"Failed to connect to ChromaDB server: {e}")
                raise e
        return self._client

    def _get_collection(self):
        """Lazy loader for collection instantiation."""
        if self._collection is None:
            client = self._get_client()
            try:
                # Get or create collection
                self._collection = client.get_or_create_collection(
                    name=self.collection_name
                )
                logger.info(f"Vector collection '{self.collection_name}' initialized")
            except Exception as e:
                logger.error(f"Error accessing ChromaDB collection: {e}")
                raise e
        return self._collection

    async def upsert_article(
        self,
        article_id: str,
        title: str,
        content: str,
        summary: str,
        metadata: Dict[str, Any]
    ) -> None:
        """Embed and store article records in ChromaDB."""
        collection = self._get_collection()
        
        document_text = f"Title: {title}\nSummary: {summary}\nContent: {content}"
        
        try:
            from vector_store.embeddings import embeddings_service
            embedding = await embeddings_service.get_embedding(document_text)
            
            # Running synchronous ChromaDB SDK operation in executor
            import asyncio
            loop = asyncio.get_running_loop()
            
            def sync_upsert():
                collection.upsert(
                    ids=[article_id],
                    embeddings=[embedding],
                    documents=[document_text],
                    metadatas=[metadata]
                )
                
            await loop.run_in_executor(None, sync_upsert)
            logger.info(f"Article {article_id} successfully indexed in vector store")
            
        except Exception as e:
            logger.error(f"Failed to upsert article to ChromaDB: {e}")
            # Do not re-raise to prevent breaking background task chain
            pass

    async def query_articles(
        self,
        query_text: str,
        n_results: int = 5,
        where_filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Perform semantic search against ChromaDB using custom query embeddings."""
        collection = self._get_collection()
        
        try:
            from vector_store.embeddings import embeddings_service
            query_embedding = await embeddings_service.get_embedding(query_text)
            
            import asyncio
            loop = asyncio.get_running_loop()
            
            def sync_query():
                return collection.query(
                    query_embeddings=[query_embedding],
                    n_results=n_results,
                    where=where_filter
                )
                
            results = await loop.run_in_executor(None, sync_query)
            
            # Format results
            formatted_results = []
            if results and results.get("ids"):
                ids = results["ids"][0]
                documents = results["documents"][0]
                metadatas = results["metadatas"][0]
                distances = results["distances"][0] if "distances" in results else [0.0] * len(ids)
                
                for idx in range(len(ids)):
                    formatted_results.append({
                        "id": ids[idx],
                        "document": documents[idx],
                        "metadata": metadatas[idx],
                        "distance": distances[idx]
                    })
                    
            return formatted_results
            
        except Exception as e:
            logger.error(f"Semantic search query against ChromaDB failed: {e}")
            return []


chroma_client = ChromaDBClient()
