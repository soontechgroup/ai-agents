# AI Chatbot Demo

A Flask-based web application demonstrating AI chatbot functionality with LangGraph-enhanced memory, web search tools, and conversation tracking.

## Features

- **LangGraph-Enhanced Memory**: Advanced conversation memory using ChromaDB for persistent storage
- **Web Search Integration**: Multi-provider search capabilities (DuckDuckGo, Serper, Mock) with automatic failover
- **OpenAI Integration**: GPT-4o-mini model for intelligent responses
- **Conversation Tracking**: Session-based conversation management
- **Web Interface**: Clean, responsive chat interface
- **API Endpoints**: RESTful API for chat interactions

## Quick Start

1. **Clone and Setup**:
   ```bash
   git clone <repository-url>
   cd ai-chatbot-demo
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure Environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your OpenAI API key and other settings
   ```

3. **Run the Application**:
   ```bash
   python src/web/app.py
   ```

4. **Access the Demo**:
   - Web Interface: http://127.0.0.1:5000
   - API Documentation: http://127.0.0.1:5000/health

## API Endpoints

- `POST /api/chat` - Send chat messages
- `GET /api/stats` - Get chatbot statistics
- `POST /api/clear` - Clear chatbot memory
- `POST /api/demo` - Run demo conversation
- `GET /health` - Health check

## Architecture

- **Frontend**: HTML/CSS/JavaScript with responsive design
- **Backend**: Flask web framework
- **AI Engine**: OpenAI GPT models with custom memory system
- **Memory**: ChromaDB vector database for conversation persistence
- **Search**: Multi-provider web search with intelligent routing

## Configuration

Key environment variables:
- `OPENAI_API_KEY`: Your OpenAI API key (required)
- `OPENAI_MODEL`: Model to use (default: gpt-4o-mini)
- `SEARCH_PROVIDER`: Search provider (duckduckgo, serper, mock)
- `CHROMA_PERSIST_DIR`: ChromaDB storage directory

## Development

The application includes:
- Memory management system in `src/memory/`
- Web search tools in `src/tools/`
- Main chatbot logic in `src/chatbot.py`
- Web interface in `src/web/app.py`
- Frontend assets in `static/` and `templates/`

## License

MIT License - see LICENSE file for details.