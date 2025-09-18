"""
Main chatbot system using LangGraph-enhanced memory with web search tools
"""
import os
import time
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

import openai
from memory.graph_memory import GraphMemorySystem
from tools.web_search import WebSearchTool

class AIChatterBot:
    """AI Chatbot with LangGraph-enhanced memory and web search capabilities"""
    
    def __init__(self, name: str = "AI Assistant"):
        self.name = name
        self.memory_system = GraphMemorySystem("AI Chatbot Memory")
        self.web_search = WebSearchTool()
        
        # Set up OpenAI client
        self.openai_client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
        
        print(f"[CHATBOT] Initialized {name} with LangGraph-enhanced memory")
        print(f"[CHATBOT] Model: {self.model}")
        print(f"[CHATBOT] Web search: {'Mock data' if self.web_search.use_mock_data else 'Live search'}")
    
    def chat(self, user_message: str, conversation_id: Optional[str] = None) -> Dict[str, Any]:
        """Process a chat message and return response with metadata"""
        
        start_time = time.time()
        
        try:
            # Step 1: Retrieve context using LangGraph workflow
            print(f"[CHATBOT] Retrieving context for: {user_message[:50]}...")
            retrieval_result = self.memory_system.retrieve_context(user_message, max_results=5)
            
            # Step 2: Generate response using OpenAI with context
            response_text = self._generate_response(user_message, retrieval_result)
            
            # Step 3: Store the conversation using LangGraph workflow
            context = {'conversation_id': conversation_id} if conversation_id else {}
            self.memory_system.store_conversation(user_message, response_text, context)
            
            processing_time = time.time() - start_time
            
            return {
                'response': response_text,
                'sources': retrieval_result.sources,
                'memory_used': len(retrieval_result.memories),
                'web_results': len(retrieval_result.web_results),
                'facts_retrieved': len(retrieval_result.facts),
                'processing_time': round(processing_time, 2),
                'metadata': retrieval_result.metadata
            }
            
        except Exception as e:
            return {
                'response': f"I apologize, but I encountered an error: {str(e)}",
                'sources': [],
                'memory_used': 0,
                'web_results': 0,
                'facts_retrieved': 0,
                'processing_time': time.time() - start_time,
                'error': str(e),
                'metadata': {}
            }
    
    def _generate_response(self, user_message: str, retrieval_result) -> str:
        """Generate response using OpenAI with retrieved context"""
        
        # Build context from memory and web search
        context_parts = []
        
        # Add memory context
        if retrieval_result.memories:
            context_parts.append("Previous conversation context:")
            for i, memory in enumerate(retrieval_result.memories[:3], 1):
                context_parts.append(f"{i}. {memory}")
        
        # Add facts
        if retrieval_result.facts:
            context_parts.append("\nKnown facts about the user:")
            for key, value in retrieval_result.facts.items():
                context_parts.append(f"- {key}: {value}")
        
        # Add web search results
        if retrieval_result.web_results:
            context_parts.append("\nRecent information from web search:")
            for i, result in enumerate(retrieval_result.web_results[:3], 1):
                title = result.get('title', 'No title')
                snippet = result.get('snippet', 'No description')
                context_parts.append(f"{i}. {title}: {snippet}")
        
        # Build the prompt
        system_prompt = """You are a helpful AI assistant with access to conversation memory and current web information.

Use the provided context to give accurate, helpful responses. If you use information from web search results, mention that you found recent information. If you reference previous conversations, acknowledge the context naturally.

Be conversational, helpful, and accurate. Don't mention technical details about your memory system or processing unless specifically asked."""
        
        context_text = "\n".join(context_parts) if context_parts else "No additional context available."
        
        user_prompt = f"""Context:\n{context_text}\n\nUser message: {user_message}

Please respond naturally and helpfully based on the context provided."""
        
        try:
            # Generate response using OpenAI
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"[ERROR] OpenAI API call failed: {e}")
            
            # Fallback response
            if retrieval_result.memories:
                return f"Based on our previous conversations, I understand you're asking about: {user_message}. However, I'm having trouble accessing my language model right now. Could you please try again?"
            else:
                return f"I understand you're asking about: {user_message}. I'm experiencing some technical difficulties with my response generation. Please try again in a moment."
    
    def get_stats(self) -> Dict[str, Any]:
        """Get chatbot statistics"""
        
        memory_stats = self.memory_system.get_stats()
        search_stats = self.web_search.get_search_stats()
        
        return {
            'chatbot_name': self.name,
            'model': self.model,
            'memory_system': memory_stats,
            'search_tool': search_stats,
            'capabilities': [
                'Natural conversation',
                'Memory of past conversations',
                'Fact extraction and storage',
                'Web search for current information',
                'LangGraph-inspired processing',
                'Intent classification',
                'Conditional tool routing'
            ]
        }
    
    def clear_memory(self):
        """Clear all stored memories"""
        self.memory_system.clear()
        print(f"[CHATBOT] Memory cleared")
    
    def set_model(self, model_name: str):
        """Change the OpenAI model"""
        self.model = model_name
        print(f"[CHATBOT] Model changed to: {model_name}")

# Demo conversation function
def demo_conversation():
    """Run a demo conversation to showcase the chatbot"""
    
    print("AI Chatbot Demo - LangGraph Enhanced with Web Search")
    print("=" * 55)
    
    bot = AIChatterBot("Demo Assistant")
    
    # Demo conversation flow
    demo_messages = [
        "Hi, my name is Sarah and I work as a machine learning engineer",
        "What's the latest news about artificial intelligence?",
        "Tell me about my background",
        "I'm interested in Python programming for AI",
        "What do you remember about me?"
    ]
    
    for i, message in enumerate(demo_messages, 1):
        print(f"\n--- Turn {i} ---")
        print(f"User: {message}")
        
        result = bot.chat(message)
        print(f"Assistant: {result['response']}")
        
        # Show processing info
        if result.get('sources'):
            print(f"Sources used: {', '.join(result['sources'])}")
        
        if result.get('web_results', 0) > 0:
            print(f"Web search results: {result['web_results']}")
        
        if result.get('memory_used', 0) > 0:
            print(f"Memories retrieved: {result['memory_used']}")
        
        print(f"Processing time: {result['processing_time']}s")
        
        time.sleep(1)  # Brief pause between messages
    
    # Show final stats
    print(f"\n" + "=" * 55)
    print("FINAL STATISTICS:")
    print("=" * 55)
    
    stats = bot.get_stats()
    memory_stats = stats['memory_system']
    
    print(f"Conversations processed: {memory_stats['conversation_count']}")
    print(f"Documents stored: {memory_stats['stored_documents']}")
    print(f"Processing stages available: {len(memory_stats['processing_stages'])}")
    print(f"Search provider: {stats['search_tool']['provider']}")
    
    print("\nDemo completed successfully!")
    return bot

if __name__ == "__main__":
    demo_conversation()