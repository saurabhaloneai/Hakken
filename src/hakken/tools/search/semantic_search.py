import os
import chromadb
from sentence_transformers import SentenceTransformer
from hakken.tools.base import BaseTool


TOOL_DESCRIPTION = """Searches code using semantic similarity (understands meaning, not just exact text matches).

Unlike grep which finds exact text or regex patterns, semantic search understands:
- Conceptual similarity (e.g., "user authentication" finds login code)
- Code intent (e.g., "error handling" finds try-catch blocks)
- Related functionality (e.g., "database query" finds ORM calls)

How it works:
- Embeds your query and code snippets into vector space
- Returns the top_k most semantically similar code sections
- Uses ChromaDB and sentence-transformers for local search

Two modes:
1. **Search mode**: Provide 'query' to search indexed code
2. **Index mode**: Provide 'index_path' to index a directory for searching

Use this when:
- You don't know the exact function/variable names
- You're looking for code that does something conceptually
- Grep returns too many results or misses relevant code

Note: Requires initialization and indexing before searching."""


class SemanticSearchTool(BaseTool):
    def __init__(self):
        super().__init__()
        self.chroma_client = None
        self.collection = None
        self.model = None
        self.initialized = False

    def _initialize(self):
        if not self.initialized:
            db_path = os.path.join(os.getcwd(), ".chroma_db")
            self.chroma_client = chromadb.PersistentClient(path=db_path)
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            self.collection = self.chroma_client.get_or_create_collection(name="codebase_embeddings")
            self.initialized = True

    @staticmethod
    def get_tool_name():
        return "semantic_search"

    async def act(self, query=None, index_path=None, reindex=False, top_k=5):
        self._initialize()
        if not self.initialized:
            return "Error: Semantic search tool failed to initialize. Check that chromadb and sentence-transformers are installed."

        if index_path:
            # Indexing mode
            if reindex:
                try:
                    self.chroma_client.delete_collection("codebase_embeddings")
                    self.collection = self.chroma_client.get_or_create_collection(name="codebase_embeddings")
                except Exception:
                    pass
            
            from hakken.utils.embeddings import index_directory
            error, count = index_directory(index_path, self.model, self.collection)
            if error:
                return f"Error: {error}"
            return f"Successfully indexed {count} files in {index_path}."
        
        if not query:
            return "Error: query is required for searching. Provide a natural language description of what you're looking for."

        # Search mode
        from hakken.utils.embeddings import search_similar
        results = search_similar(query, self.model, self.collection, top_k)
        
        if not results:
            return "No relevant code found. Try indexing the codebase first using the index_path parameter."
        
        formatted_results = []
        for result in results:
            formatted_results.append(f"File: {result['file_path']}\nContent:\n{result['content']}\n---")
        
        return "\n".join(formatted_results)

    def json_schema(self):
        return {
            "type": "function",
            "function": {
                "name": self.get_tool_name(),
                "description": TOOL_DESCRIPTION,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Natural language description of what you're looking for (e.g., 'code that handles file uploads')."
                        },
                        "index_path": {
                            "type": "string",
                            "description": "Absolute path to directory to index. When provided, indexes files instead of searching."
                        },
                        "reindex": {
                            "type": "boolean",
                            "description": "If true, clears existing index before reindexing. Only used with index_path.",
                            "default": False
                        },
                        "top_k": {
                            "type": "integer",
                            "description": "Number of most relevant results to return (default: 5).",
                            "default": 5
                        }
                    },
                    "required": [] 
                }
            }
        }

    def get_status(self):
        if self.initialized:
            return f"ready (Collection size: {self.collection.count()})"
        return "not initialized"
