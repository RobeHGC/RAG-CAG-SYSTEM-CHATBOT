# context
the project actually is incomplete and truncated. I'll leave the issues to give context to people who want to make use of this in near future. 
I'll leave the .md implementation guides in the "bitacora". Good luck.
# Nadia AI Companion 🤖

[![CI](https://github.com/RobeHGC/nadia-ai-companion/workflows/CI/badge.svg)](https://github.com/RobeHGC/nadia-ai-companion/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/RobeHGC/nadia-ai-companion/branch/main/graph/badge.svg)](https://codecov.io/gh/RobeHGC/nadia-ai-companion)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An advanced AI companion with emotional-spatial-temporal memory system. Meet Nadia, a 24-year-old medical student from Monterrey who maintains persistent memory, emotional understanding, and coherent personality across conversations.

## 🎯 Project Vision

This project transcends conventional chatbots to create a believable and persistent digital companion. Nadia is not just a Q&A assistant, but an entity with:

- **Defined Personality**: Consistent communication style and character traits
- **Persistent Memory**: Remembers past interactions and learns from users
- **Emotional Intelligence**: VAD (Valence-Arousal-Dominance) analysis and emotional weighting
- **Coherence Verification**: Validates responses to avoid contradictions
- **Human Supervision**: Transparent system with continuous improvement capabilities

## 🏗️ Architecture

The system consists of several interconnected modules:

- **Telegram Userbot**: Communication interface with users
- **Central Orchestrator**: Coordinates all system components
- **Memory System**: Cache (Redis) + Knowledge Graph (Neo4j)
- **Coherence Verification Agent**: Validates responses before sending
- **Management Dashboard**: Web interface for supervision and curation
- **Fine-tuning Database**: Stores curated conversations for model improvement

### Key Features

- **Multi-level Memory**: Short-term (Redis) + Long-term (Neo4j graph)
- **Emotional Analysis**: Real-time VAD emotion detection
- **Spreading Activation**: Emotionally-weighted memory retrieval
- **Memory Consolidation**: Episodic → Semantic memory transformation
- **Adaptive Forgetting**: Emotional modulation of memory retention
- **Contextual Retrieval**: GraphRAG with emotional weighting

## 🔧 Technical Stack

- **Backend**: Python 3.10+, FastAPI, Celery
- **Databases**: PostgreSQL, Redis, Neo4j
- **AI/ML**: Gemini 2.0 Flash, RoBERTa VAD, all-MiniLM-L6-v2
- **Message Queue**: Celery with Redis broker
- **Containerization**: Docker & Docker Compose
- **Code Quality**: Black, isort, flake8, mypy, pytest

## 📋 System Requirements

### With Docker (Recommended) 🐳
- Docker 20.10+
- Docker Compose 2.0+
- 4GB RAM minimum, 8GB recommended

### Local Installation
- Python 3.10+
- PostgreSQL 14+
- Redis 7+
- Neo4j 5+

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/RobeHGC/nadia-ai-companion.git
cd nadia-ai-companion
```

### 2. Environment Setup

```bash
# Run setup script (creates venv and installs dependencies)
./scripts/setup_dev.sh

# Or manually:
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure Environment Variables

```bash
# Copy example file
cp .env.example .env

# Edit with your values
nano .env  # or your preferred editor
```

### 4. Configure Telegram API

1. Go to https://my.telegram.org/apps
2. Create a new application
3. Copy `API ID` and `API Hash` to your `.env` file

### 5. Start with Docker (Recommended)

```bash
# Development: Start all basic services
docker-compose up -d

# Full development with hot-reload
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Production deployment
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Access services:
# - Dashboard: http://localhost:8000
# - Neo4j Browser: http://localhost:7474
# - Flower (monitoring): http://localhost:5555
```

## 🧪 Testing

```bash
# Run all tests
make test
# or
pytest

# With coverage
make coverage
# or
pytest --cov=src

# Specific test categories
make test-unit          # Unit tests only
make test-integration   # Integration tests only
make test-db           # Database tests only

# Full CI pipeline locally
make ci                # Lint + Type check + Tests + Coverage
```

## 🛠️ Development

### Project Structure

```
nadia-ai-companion/
├── src/               # Source code
│   ├── userbot/      # Telegram bot
│   ├── orquestador/  # Central coordinator
│   ├── memoria/      # Memory system
│   ├── verificador/  # Coherence agent
│   ├── dashboard/    # Web interface
│   └── common/       # Shared utilities
├── tests/            # Unit & integration tests
├── docs/             # Documentation
├── scripts/          # Utility scripts
├── config/           # Configuration files
└── bitacora/         # Project documentation
```

### Code Quality

```bash
# Install pre-commit hooks
make pre-commit-install

# Format code
make format

# Lint code
make lint

# Type checking
make type-check

# Full quality gate
make quality-gate
```

## 🐳 Docker Usage

### Available Configurations

1. **Basic Development**: Databases only
   ```bash
   docker-compose up -d postgres redis neo4j
   ```

2. **Full Development**: All services with hot-reload
   ```bash
   docker-compose --profile full up -d
   ```

3. **Production**: Optimized for deployment
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
   ```

### Exposed Ports

- **Dashboard**: http://localhost:8000
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379
- **Neo4j HTTP**: http://localhost:7474
- **Neo4j Bolt**: bolt://localhost:7687
- **Flower**: http://localhost:5555

## 📚 Documentation

- [System Architecture](docs/ARCHITECTURE.md)
- [Implementation Guide](bitacora/GUIA_COMPLETA.md)
- [Quick Configuration](bitacora/configuracion_rapida.md)
- [Memory System](bitacora/memoria/MEMORIA.md)
- [Deployment Guide](bitacora/deployment_guide.md)

## 🎯 Current Status

**Phase 2: Advanced Memory Implementation**
- ✅ Infrastructure setup complete
- ✅ Database schemas configured
- ⚡ Implementing VAD emotional analysis
- ⚡ Building spreading activation system
- ⚡ Creating memory consolidation pipeline
- ⚡ Developing dashboard interface

### Roadmap

- **Phase 1**: ✅ MVP Infrastructure (Completed)
- **Phase 2**: 🔄 Advanced Memory System (In Progress)
- **Phase 3**: 🔄 Optimization & Scaling (Planned)
- **Phase 4**: 🔮 Advanced Features (Future)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👥 Team

- **Roberto H.** - Lead Developer

## 🔗 Links

- [Issues](https://github.com/RobeHGC/nadia-ai-companion/issues)
- [Discussions](https://github.com/RobeHGC/nadia-ai-companion/discussions)
- [Wiki](https://github.com/RobeHGC/nadia-ai-companion/wiki)

---

**Project Status**: 🚧 In Development - Phase 2 (Advanced Memory System)
