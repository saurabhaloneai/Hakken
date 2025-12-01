from typing import Tuple, List, Optional, Dict, Any
import os


def create_embedding_model(model_name: str = 'all-MiniLM-L6-v2'):
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(model_name)


def embed_texts(texts: List[str], model) -> List[List[float]]:
    return model.encode(texts).tolist()


def create_or_get_collection(db_client, collection_name: str = "codebase_embeddings"):
    return db_client.get_or_create_collection(name=collection_name)


def index_directory(
    directory: str,
    model,
    collection,
    extensions: Tuple[str, ...] = ('.py', '.js', '.ts', '.md', '.txt'),
    max_content_size: int = 2000,
    batch_size: int = 100
) -> Tuple[Optional[str], int]:
    if not os.path.exists(directory):
        return f"Directory not found: {directory}", 0
    
    count = 0
    documents = []
    metadatas = []
    ids = []
    
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(extensions):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    if len(content.strip()) > 0:
                        documents.append(content[:max_content_size])
                        metadatas.append({"file_path": file_path})
                        ids.append(file_path)
                        count += 1
                        
                        # Batch add
                        if len(documents) >= batch_size:
                            embeddings = embed_texts(documents, model)
                            collection.add(
                                embeddings=embeddings,
                                documents=documents,
                                metadatas=metadatas,
                                ids=ids
                            )
                            documents = []
                            metadatas = []
                            ids = []
                            
                except (UnicodeDecodeError, IOError):
                    continue
    
    if documents:
        embeddings = embed_texts(documents, model)
        collection.add(
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
    
    return None, count


def search_similar(
    query: str,
    model,
    collection,
    top_k: int = 5
) -> List[Dict[str, Any]]:
    query_embedding = embed_texts([query], model)
    
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=top_k
    )
    
    if not results['documents'][0]:
        return []
    
    formatted = []
    for i, doc in enumerate(results['documents'][0]):
        meta = results['metadatas'][0][i]
        formatted.append({
            'file_path': meta.get('file_path', 'Unknown'),
            'content': doc
        })
    
    return formatted
