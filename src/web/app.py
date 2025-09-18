"""
Flask web interface for the AI Chatbot Demo
"""
import os
import sys
from pathlib import Path

# Add src directory to path
sys.path.append(str(Path(__file__).parent.parent))

from flask import Flask, render_template, request, jsonify, session
import uuid
import time
from chatbot import AIChatterBot

app = Flask(__name__, 
            template_folder='../../templates',
            static_folder='../../static')
app.secret_key = os.urandom(24)

# Global chatbot instance
chatbot = None

def initialize_chatbot():
    """Initialize the chatbot system"""
    global chatbot
    if chatbot is None:
        try:
            chatbot = AIChatterBot("Web Demo Assistant")
            print("[WEB] Chatbot initialized successfully")
        except Exception as e:
            print(f"[ERROR] Failed to initialize chatbot: {e}")
            return False
    return True

@app.route('/')
def home():
    """Main chat interface"""
    # Initialize session if needed
    if 'conversation_id' not in session:
        session['conversation_id'] = str(uuid.uuid4())
    
    return render_template('chat.html')

@app.route('/api/chat', methods=['POST'])
def api_chat():
    """API endpoint for chat messages"""
    
    if not initialize_chatbot():
        return jsonify({
            'error': 'Chatbot not available',
            'response': 'Sorry, the chatbot is currently unavailable. Please try again later.'
        }), 500
    
    try:
        data = request.json
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return jsonify({'error': 'Empty message'}), 400
        
        # Get conversation ID from session
        conversation_id = session.get('conversation_id')
        
        # Process the message
        result = chatbot.chat(user_message, conversation_id)
        
        return jsonify({
            'response': result['response'],
            'sources': result.get('sources', []),
            'memory_used': result.get('memory_used', 0),
            'web_results': result.get('web_results', 0),
            'facts_retrieved': result.get('facts_retrieved', 0),
            'processing_time': result.get('processing_time', 0),
            'metadata': result.get('metadata', {}),
            'conversation_id': conversation_id
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'response': 'I encountered an error processing your message. Please try again.'
        }), 500

@app.route('/api/stats')
def api_stats():
    """Get chatbot statistics"""
    
    if not initialize_chatbot():
        return jsonify({'error': 'Chatbot not available'}), 500
    
    try:
        stats = chatbot.get_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/clear', methods=['POST'])
def api_clear():
    """Clear chatbot memory"""
    
    if not initialize_chatbot():
        return jsonify({'error': 'Chatbot not available'}), 500
    
    try:
        chatbot.clear_memory()
        # Create new session
        session['conversation_id'] = str(uuid.uuid4())
        return jsonify({'success': True, 'message': 'Memory cleared successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/demo', methods=['POST'])
def api_demo():
    """Run demo conversation"""
    
    if not initialize_chatbot():
        return jsonify({'error': 'Chatbot not available'}), 500
    
    try:
        demo_messages = [
            "Hi, my name is Alex and I'm a software developer",
            "What's the latest news about Python programming?",
            "I work with machine learning projects",
            "Tell me what you know about me",
            "What are some recent developments in AI?"
        ]
        
        demo_results = []
        conversation_id = str(uuid.uuid4())
        
        for message in demo_messages:
            result = chatbot.chat(message, conversation_id)
            demo_results.append({
                'user_message': message,
                'assistant_response': result['response'],
                'metadata': {
                    'sources': result.get('sources', []),
                    'memory_used': result.get('memory_used', 0),
                    'web_results': result.get('web_results', 0),
                    'processing_time': result.get('processing_time', 0)
                }
            })
            
            # Small delay between demo messages
            time.sleep(0.5)
        
        return jsonify({
            'demo_results': demo_results,
            'conversation_id': conversation_id,
            'total_turns': len(demo_results)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health_check():
    """Health check endpoint"""
    
    status = {
        'status': 'healthy',
        'timestamp': time.time(),
        'chatbot_initialized': chatbot is not None
    }
    
    if chatbot:
        try:
            stats = chatbot.get_stats()
            status['chatbot_status'] = 'operational'
            status['conversations'] = stats['memory_system']['conversation_count']
        except Exception as e:
            status['chatbot_status'] = f'error: {str(e)}'
    
    return jsonify(status)

if __name__ == '__main__':
    print("Starting AI Chatbot Demo Web Interface...")
    print("Features: LangGraph-enhanced memory, web search tools, conversation tracking")
    
    # Initialize chatbot on startup
    if initialize_chatbot():
        print("Chatbot ready!")
        app.run(host='0.0.0.0', port=5000, debug=True)
    else:
        print("Failed to initialize chatbot. Please check your configuration.")
        print("Make sure you have:")
        print("1. OpenAI API key in .env file")
        print("2. Required packages installed: pip install -r requirements.txt")
        print("3. ChromaDB directory accessible")