# Agente-IA

**Multi-tenant SaaS platform for conversational AI agents** that serve businesses through multiple channels (WhatsApp, Instagram, Facebook, Email).

Each business customer has their own AI agent that intelligently handles sales, customer service, booking, and payments—all through natural conversation.

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Supabase account (PostgreSQL database)
- Redis
- OpenAI API key
- Meta Cloud API credentials (WhatsApp, Instagram, Facebook)

### Development Setup

```bash
# Clone repository
git clone <repo>
cd agente-ia

# 1. Install dependencies
make install

# 2. Configure environment
make env
# Edit .env with your credentials

# 3. Start services
make docker-up

# FastAPI will be at http://localhost:8000
# Streamlit dashboard at http://localhost:8501
# Redis at localhost:6379
```

## 📖 Documentation

- **[CLAUDE.md](./CLAUDE.md)** - Complete project architecture and developer guide
- **[Architecture Overview](#architecture-overview)** - System design
- **[API Reference](#api-reference)** - REST endpoints

## 🏗️ Architecture Overview

### Core Components

**Agent Engine (GPT-4o)**
- Function calling for sales, booking, payments, lead scoring
- Conversation history and context awareness
- Cross-channel user identification
- Human-like response timing and typing indicators

**Message Router**
- Identifies client from webhook identifiers (phone_number_id, page_id, email)
- Normalizes messages from all channels to unified format
- Routes to appropriate client's agent

**Conversation Memory**
- Full history in Supabase with Row-Level Security
- Token-aware context truncation
- Cross-channel user consolidation

**Message Buffer**
- Redis-based debouncing
- Simulates human-like timing (typing delays, message splitting)
- Prevents bot-like rapid responses

### Multi-Tenant Architecture

- **Client Isolation**: RLS at database level + JWT validation
- **Webhooks**: Meta sends to single URL; router identifies client
- **Credentials**: Each client's API keys encrypted in Supabase
- **Data Access**: JWT claims include `client_id`; queries filtered by client

### Message Flow

```
Channel Webhook
    ↓
Normalizer (unified format)
    ↓
Router (identify client)
    ↓
Memory (fetch conversation history)
    ↓
Agent (GPT-4o with function calling)
    ├─ Sales module
    ├─ Booking module
    ├─ Payment verification
    ├─ Lead scoring
    └─ Alerts to business owner
    ↓
Buffer (debounce + human-like timing)
    ↓
Channel API (send response)
```

## 🔧 Available Commands

### Development

```bash
make dev              # Run FastAPI server with hot reload
make docker-up        # Start all services
make docker-down      # Stop services
make docker-logs      # View logs
```

### Testing

```bash
make test             # Run all tests
make test-cov         # Coverage report
make test-one TEST=tests/test_auth.py::TestAuthManager::test_hash_password
```

### Code Quality

```bash
make format           # Black + isort
make lint             # Flake8
make type-check       # MyPy type checking
make security         # Bandit security scan
```

### Before Committing

```bash
make check            # Format + type-check + lint + tests + security
```

## 📁 Project Structure

```
agente-ia/
├── core/
│   ├── agent.py              # GPT-4o agent with function calling
│   ├── buffer.py             # Message debouncing (Redis)
│   ├── memory.py             # Conversation history (Supabase)
│   ├── router.py             # Message routing to client
│   └── normalizer.py         # Unified message format
├── modulos/                  # Feature modules (toggleable per client)
│   ├── ventas.py            # Sales: catalog, quotes, discounts
│   ├── agendamiento.py      # Google Calendar booking
│   ├── cobros.py            # Payment verification with Vision
│   ├── links_pago.py        # Payment links (Stripe, MercadoPago, PayPal)
│   ├── calificacion.py      # Lead scoring
│   ├── campanas.py          # Bulk messaging
│   ├── alertas.py           # Notifications to business owner
│   ├── seguimientos.py      # Auto follow-ups
│   └── analytics.py         # Metrics and reports
├── canales/                  # Channel implementations
│   ├── whatsapp.py          # Meta Cloud API
│   ├── instagram.py         # Meta Graph API
│   ├── facebook.py          # Meta Messenger
│   └── email.py             # SendGrid
├── seguridad/               # Security & auth
│   ├── auth.py              # JWT tokens + RBAC
│   ├── rate_limiter.py      # Rate limiting
│   ├── validator.py         # Webhook validation
│   └── encryption.py        # Data encryption
├── config/
│   └── modelos.py           # Pydantic schemas
├── tests/                   # Test suite (80%+ coverage required)
│   ├── conftest.py         # Pytest fixtures
│   └── test_*.py           # Test files
├── main.py                  # FastAPI application
├── requirements.txt         # Python dependencies
├── docker-compose.yml       # Redis, FastAPI, Streamlit
├── Dockerfile              # FastAPI container
├── CLAUDE.md               # Developer guide
└── README.md              # This file
```

## 🔐 Security

- **No hardcoded secrets**: All in `.env` (never in code)
- **JWT authentication**: 24-hour expiration
- **Rate limiting**: Per-user and per-client limits
- **Row-Level Security**: Database-level isolation
- **Webhook validation**: HMAC-SHA256 signature verification
- **Prompt injection detection**: Validates user inputs
- **Encryption**: Sensitive data encrypted at rest

## 💾 Database

PostgreSQL via Supabase with Row-Level Security (RLS):

**Core Tables:**
- `users` - End users per client
- `conversations` - Conversation records
- `messages` - Full message history
- `leads` - Lead scoring and qualification
- `payments` - Payment verification records
- `appointments` - Booked appointments (Google Calendar)
- `alerts_log` - Audit trail of alerts sent
- `clients` - Business customers (SaaS)
- `agent_config` - Agent settings per client
- `channel_credentials` - Encrypted API keys

## 🤖 AI Agent Capabilities

### Sales Module
- Product catalog and pricing
- Quotation generation
- Objection handling
- Discount application
- Sales confirmation

### Booking Module
- Real-time availability checks (Google Calendar)
- Appointment scheduling
- Confirmation and reminders (24h and 1h before)
- Cancellation and rescheduling
- Timezone handling

### Payment Module
- Payment link generation (Stripe, MercadoPago, PayPal)
- Receipt image analysis with GPT-4o Vision
  - Validates: amount, account, date
  - Detects: duplicates, fraud, alterations
- Automatic payment confirmation

### Lead Scoring
- Real-time scoring (0-10)
- Lead state tracking: Curious → Prospect → Hot → Customer
- Automatic notifications when score >= 8

### Alerts
- **Critical**: Immediate WhatsApp
  - Agent confusion (2 failed responses)
  - Detected frustration
  - Suspicious payment
  - Price/info errors
- **Important**: WhatsApp + Email
  - Hot lead (score >= 8)
  - Human escalation
- **Info**: Email + Dashboard
  - Daily summary
  - New verified payment
  - Weekly report

## 🧪 Testing

Minimum 80% code coverage required. Three types of tests:

```bash
# Unit tests (fast, isolated)
pytest tests/test_auth.py

# Integration tests (real Supabase + Redis)
pytest -m integration

# E2E tests (full message flow)
pytest -m smoke
```

See [tests/test_auth.py](./tests/test_auth.py) for examples.

## 🚀 Deployment

### Development (Local)
```bash
make setup      # Install + configure
make docker-up  # Start services
```

### Production (VPS)
```bash
# Build Docker image
docker build -t agente-ia:latest .

# Run with environment variables
docker run -d \
  --name agente-ia \
  -p 8000:8000 \
  --env-file .env \
  -v /data/agente-ia:/app/data \
  agente-ia:latest
```

## 📊 Monitoring

Structured JSON logging with:
- Request ID tracking
- Client ID in all logs
- Token usage tracking
- Agent decision logging

View logs:
```bash
make docker-logs              # All services
docker logs -f agente-ia-fastapi  # FastAPI only
```

## 🤝 Contributing

1. **Plan first**: Use `/plan` for complex changes
2. **TDD**: Write tests before code
3. **Type hints**: Required in all Python code
4. **Code review**: All PRs reviewed
5. **Tests**: 80%+ coverage minimum

## 📞 Support

- Issues: [GitHub Issues](https://github.com/yourusername/agente-ia/issues)
- Email: support@agente-ia.com

## 📄 License

MIT License - see [LICENSE](./LICENSE) file

## 🔄 API Examples

### Authenticate

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password"}'
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

### Get Conversations

```bash
curl http://localhost:8000/api/clients/client-123/conversations \
  -H "Authorization: Bearer <token>"
```

### Get Leads

```bash
curl http://localhost:8000/api/clients/client-123/leads \
  -H "Authorization: Bearer <token>"
```

## 🎯 Roadmap

- [ ] Voice calls (Twilio)
- [ ] WhatsApp template management UI
- [ ] Advanced analytics dashboard
- [ ] Multi-agent support per client
- [ ] Custom knowledge base integration
- [ ] SMS channel
- [ ] Telegram channel

---

**Built with ❤️ for businesses that want AI agents to just work.**
