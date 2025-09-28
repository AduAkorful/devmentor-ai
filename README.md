# DevMentor AI 🚀

DevMentor AI is an intelligent code analysis and mentoring platform that helps developers understand, explore, and learn from any GitHub repository using advanced AI technology. By combining powerful language models with semantic search capabilities, DevMentor AI provides contextual answers about codebases, making it easier for developers to onboard to new projects, debug issues, and understand complex software architectures.

## ✨ Features

- **🔐 GitHub OAuth Integration**: Secure authentication with GitHub to access your repositories
- **📁 Repository Analysis**: Automatically ingest and analyze any public or private GitHub repository
- **🤖 AI-Powered Code Assistant**: Chat with an AI that understands your codebase using Google's Gemini 2.0 Flash
- **🔍 Semantic Search**: Advanced vector search using Elasticsearch and Google Vertex AI embeddings
- **💬 Real-time Chat Interface**: Stream responses with markdown formatting and syntax highlighting
- **🎨 Modern UI**: Clean, responsive interface built with React and Tailwind CSS
- **⚡ Fast Performance**: RAG (Retrieval-Augmented Generation) pipeline for accurate, context-aware responses

## 🏗️ Architecture

### Frontend (React + Vite)
- **React 19** with modern hooks and functional components
- **Tailwind CSS** for responsive, dark-themed styling
- **Heroicons** for consistent iconography
- **React Markdown** with syntax highlighting support
- **Server-Sent Events** for real-time streaming responses

### Backend (FastAPI + Python)
- **FastAPI** for high-performance API endpoints
- **GitHub OAuth 2.0** for secure authentication
- **Elasticsearch** for vector storage and hybrid search
- **Google Vertex AI** for embeddings and chat completion
- **GitPython** for repository cloning and processing
- **JWT** for session management

### AI/ML Stack
- **Google Vertex AI Embeddings** (`text-embedding-004`) for semantic understanding
- **Google Gemini 2.0 Flash** for conversational AI responses
- **LangChain** for document processing and text splitting
- **Hybrid Search** combining semantic similarity and keyword matching

## 🚦 Getting Started

### Prerequisites
- Node.js 18+ and npm/yarn
- Python 3.8+
- Google Cloud Platform account with Vertex AI enabled
- Elasticsearch Cloud instance
- GitHub OAuth App credentials

### Environment Variables

Create a `.env` file in the `server/` directory:

```env
# GitHub OAuth
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret

# JWT Secret
JWT_SECRET=your-super-secret-jwt-key

# Google Cloud Platform
GCP_PROJECT_ID=your-gcp-project-id
GCP_REGION=us-central1

# Elasticsearch Cloud
ELASTIC_CLOUD_ID=your-elastic-cloud-id
ELASTIC_PASSWORD=your-elastic-password
```

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/AduAkorful/devmentor-ai.git
   cd devmentor-ai
   ```

2. **Setup the backend**:
   ```bash
   cd server
   pip install -r requirements.txt
   python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
   ```

3. **Setup the frontend**:
   ```bash
   cd client
   npm install
   npm run dev
   ```

4. **Visit the application**:
   Open [http://localhost:5173](http://localhost:5173) in your browser

## 🎯 How It Works

1. **Authenticate**: Login with your GitHub account to access your repositories
2. **Select Repository**: Choose any repository from your GitHub account to analyze
3. **Auto-Ingestion**: The system automatically clones, processes, and indexes the codebase
4. **Ask Questions**: Chat with the AI about the codebase - ask about architecture, specific functions, debugging help, or implementation details
5. **Get Context-Aware Answers**: Receive accurate responses based on the actual code in the repository

## 🔧 API Endpoints

- `GET /login/github` - Initiate GitHub OAuth flow
- `GET /auth/github/callback` - Handle OAuth callback
- `GET /user/me` - Get current user information
- `GET /user/repos` - Fetch user's GitHub repositories
- `POST /ingest-repo` - Start repository ingestion process
- `GET /concierge` - Stream AI responses for code questions

## 💡 Use Cases

- **Code Onboarding**: Quickly understand new codebases and their structure
- **Debugging Assistance**: Get help identifying issues and understanding error contexts
- **Architecture Reviews**: Ask about design patterns, dependencies, and system architecture
- **Learning**: Understand how specific features are implemented
- **Documentation**: Get explanations of complex code sections
- **API Exploration**: Discover available functions, classes, and modules

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| Frontend | React 19, Vite, Tailwind CSS |
| Backend | FastAPI, Python |
| Database | Elasticsearch Cloud |
| AI/ML | Google Vertex AI, LangChain |
| Authentication | GitHub OAuth 2.0, JWT |
| Deployment | Docker-ready configuration |

## 📝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Support

If you encounter any issues or have questions:
- Open an issue on GitHub
- Check the existing documentation
- Review the API endpoints and their expected parameters

## 🚧 Roadmap

- [ ] Support for more programming languages
- [ ] Integration with additional version control systems
- [ ] Team collaboration features
- [ ] Advanced code metrics and insights
- [ ] Plugin system for custom integrations
- [ ] Mobile-responsive enhancements
