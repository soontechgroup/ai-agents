"""
Base memory architecture for the AI Chatbot Demo
Implements LangGraph-inspired patterns with OpenAI + ChromaDB
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
import time
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Core imports
import openai
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# ChromaDB for persistent storage
import chromadb
from chromadb.config import Settings

# Set up OpenAI client
openai_client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Set up ChromaDB client
chroma_client = chromadb.PersistentClient(path=os.getenv('CHROMA_PERSIST_DIR', './data/chroma_db'))

@dataclass
class MemoryItem:
    """Represents a memory item in the system"""
    content: str
    timestamp: float
    memory_type: str = "general"
    importance: float = 0.5
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None

@dataclass
class RetrievalResult:
    """Result from memory retrieval"""
    memories: List[str] = field(default_factory=list)
    context: List[str] = field(default_factory=list)
    facts: Dict[str, Any] = field(default_factory=dict)
    web_results: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    sources: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

class BaseMemorySystem(ABC):
    """Base class for memory systems"""
    
    def __init__(self, name: str):
        self.name = name
        self.conversation_count = 0
        
        # Initialize ChromaDB collection
        collection_name = f"{name.lower().replace(' ', '_')}_memory"
        try:
            self.collection = chroma_client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            print(f"[MEMORY] Initialized ChromaDB collection: {collection_name}")
        except Exception as e:
            print(f"[ERROR] Could not initialize ChromaDB: {e}")
            self.collection = None
    
    @abstractmethod
    def store_conversation(self, user_message: str, assistant_response: str, context: Dict[str, Any] = None):
        """Store a conversation turn"""
        pass
    
    @abstractmethod
    def retrieve_context(self, query: str, max_results: int = 5) -> RetrievalResult:
        """Retrieve relevant context for a query"""
        pass
    
    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics"""
        pass
    
    def get_embedding(self, text: str) -> List[float]:
        """Get OpenAI embedding for text"""
        try:
            response = openai_client.embeddings.create(
                input=text,
                model=os.getenv('OPENAI_EMBEDDING_MODEL', 'text-embedding-3-small')
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"[WARNING] Embedding failed: {e}")
            # Return a simple hash-based embedding as fallback
            import hashlib
            hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
            return [(hash_val >> i) % 1000 / 500.0 - 1.0 for i in range(1536)]
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts"""
        try:
            emb1 = self.get_embedding(text1)
            emb2 = self.get_embedding(text2)
            
            emb1_array = np.array(emb1).reshape(1, -1)
            emb2_array = np.array(emb2).reshape(1, -1)
            
            similarity = cosine_similarity(emb1_array, emb2_array)[0][0]
            return float(similarity)
        except Exception as e:
            print(f"[WARNING] Similarity calculation failed: {e}")
            return 0.0
    
    def extract_facts(self, user_message: str, assistant_response: str) -> Dict[str, Any]:
        """Extract structured facts from conversation"""
        try:
            prompt = f"""Extract structured facts from this conversation:

User: {user_message}
Assistant: {assistant_response}

Extract facts in JSON format with keys like:
- user_name: if mentioned
- user_preferences: if mentioned
- topics_discussed: main topics
- user_background: if mentioned (job, location, etc.)
- questions_asked: main questions
- factual_claims: any factual statements

Return only valid JSON, no other text."""

            response = openai_client.chat.completions.create(
                model=os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.1
            )
            
            import json
            facts_text = response.choices[0].message.content.strip()
            
            # Try to parse JSON
            if facts_text.startswith('{') and facts_text.endswith('}'):
                facts = json.loads(facts_text)
                return facts
            else:
                return {}
                
        except Exception as e:
            print(f"[WARNING] Fact extraction failed: {e}")
            return {}
    
    def clear(self):
        """Clear all stored memories"""
        if self.collection:
            try:
                chroma_client.delete_collection(self.collection.name)
                # Recreate the collection
                self.collection = chroma_client.get_or_create_collection(
                    name=self.collection.name,
                    metadata={"hnsw:space": "cosine"}
                )
                print(f"[MEMORY] Cleared collection: {self.collection.name}")
            except Exception as e:
                print(f"[ERROR] Could not clear collection: {e}")
        
        self.conversation_count = 0