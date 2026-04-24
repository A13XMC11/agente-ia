# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Agente-IA** is a multi-tenant SaaS platform for conversational AI agents that serve businesses. Each client owns their own AI agent that interacts with their end users through multiple channels (WhatsApp, Instagram, Facebook, Email).

### Tech Stack

- **Backend**: Python 3.11 + FastAPI
- **AI**: OpenAI GPT-4o with function calling
- **Database**: Supabase (PostgreSQL + Row Level Security)
- **Cache/Queue**: Redis
- **Payments**: Stripe (business subscription), Stripe/MercadoPago/PayPal (client payment links)
- **Channels**: Meta Cloud API (WhatsApp, Instagram, Facebook), SendGrid (Email)
- **Integrations**: Google Calendar API, GPT-4o Vision (receipt verification)
- **Dashboard**: Streamlit
- **Infrastructure**: Docker + Docker Compose, Git

## Project Structure

```
/agente-ia
├── /core                   → Agent engine and message routing
│   ├── agent.py           → GPT-4o motor with function calling
│   ├── buffer.py          → Message debouncing (Redis)
│   ├── memory.py          → Conversation history (Supabase)
│   ├── router.py          → Routes messages to correct agent per channel
│   └── normalizer.py      → Unifies message format across all channels
├── /modulos               → Feature modules (toggleable per client)
│   ├── ventas.py          → Sales: catalog, quotes, objection handling
│   ├── agendamiento.py    → Booking: Google Calendar integration, full lifecycle
│   ├── cobros.py          → Payment verification with GPT-4o Vision
│   ├── links_pago.py      → Payment links (Stripe, MercadoPago, PayPal)
│   ├── calificacion.py    → Lead scoring (0-10, automatic notifications)
│   ├── campanas.py        → Bulk messaging campaigns
│   ├── alertas.py         → Critical/Important/Info alerts to business owner
│   ├── seguimiento.py     → Auto follow-ups (24h reminder, post-sale, reactivation)
│   └── analytics.py       → Metrics and reports
├── /canales               → Channel-specific implementations
│   ├── whatsapp.py        → Meta Cloud API webhook handler
│   ├── instagram.py       → Meta Graph API webhook handler
│   ├── facebook.py        → Meta Graph API webhook handler
│   └── email.py           → SendGrid webhook handler
├── /onboarding            → Conversational setup wizard
│   ├── wizard.py          → AI-driven onboarding agent
│   └── generator.py       → Auto-generates client agent config
├── /seguridad             → Security and authentication
│   ├── auth.py            → JWT + role-based access control
│   ├── rate_limiter.py    → Per-user and per-client rate limits
│   ├── validator.py       → Meta webhook signature validation
│   └── encryption.py      → Encryption for sensitive data
├── /dashboard             → Streamlit dashboards (role-based)
│   ├── super_admin.py     → Master panel (all clients, MRR)
│   ├── admin.py           → Business owner panel (their data only)
│   └── operador.py        → Human advisor panel (assigned conversations)
├── /billing               → Subscription and usage tracking
│   ├── stripe.py          → Monthly client billing
│   └── usage.py           → Token consumption tracking per client
├── /config                → Feature toggles and configuration
│   ├── modulos.py         → Module activation per client
│   ├── canales.py         → Active channels per client
│   └── prompts.py         → System prompts per client
├── main.py                → FastAPI application entrypoint
├── requirements.txt       → Python dependencies
├── .env.example           → Environment variables template
├── docker-compose.yml     → Redis, FastAPI, Streamlit services
└── .gitignore            → Git ignore rules
```

## Quick Start

### Development Setup

```bash
# 1. Clone and setup
git clone <repo>
cd agente-ia
cp .env.example .env  # Configure with your credentials

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start services
docker-compose up -d  # Starts Redis, database, server

# 4. Run development server
python main.py        # FastAPI on http://localhost:8000

# 5. Run Streamlit dashboard
streamlit run dashboard/super_admin.py
```

### Build and Test

```bash
# Format code
black . --line-length 100

# Lint
flake8 . --max-line-length 100 --ignore=E203,W503

# Type checking
mypy . --ignore-missing-imports

# Run tests
pytest tests/ -v
pytest tests/test_specific.py::TestClass::test_method  # Single test

# Run with coverage
pytest --cov=. --cov-report=html tests/
```

### Docker Commands

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f fastapi
docker-compose logs -f redis
docker-compose logs -f streamlit

# Stop services
docker-compose down

# Clean up (remove volumes, images)
docker-compose down -v
```

## Architecture Overview

### Multi-Tenant Design

- **Isolation**: Row Level Security (RLS) at database level ensures clients see only their data
- **Auth**: JWT tokens with client_id embedded; every request validated by middleware
- **Webhooks**: Meta webhooks route to correct agent based on phone_number_id or page_id
- **Credentials**: Each client stores encrypted API credentials in Supabase

### Message Flow

1. **Inbound**: Channel (WhatsApp/Email/etc) → Webhook → Normalizer → Router
2. **Processing**: Router identifies client → Fetches memory → Calls Agent (GPT-4o)
3. **Agent Logic**: 
   - Calls enabled module functions (sales, booking, payments, etc.)
   - Uses function_calling to invoke tools (check calendar, verify payment, etc.)
   - Tracks conversation state for context
4. **Outbound**: Agent → Buffer (debounce) → Channel → End user
5. **Storage**: Conversation saved to Supabase, used for memory in next turn

### Core Components

**Agent (GPT-4o with Function Calling)**
- System prompt varies per client
- Functions include: check_calendar, verify_receipt, create_quote, etc.
- Detects intent: sales, booking, support, payment verification
- Escalates to human when needed

**Buffer (Redis-based debounce)**
- Groups rapid messages to avoid sending 5 separate "typing..." indicators
- Configurable delay (2-5 seconds)
- Distributes long responses into 2-3 short messages
- Simulates human-like response timing

**Memory (Supabase)**
- Full conversation history per user_id (Supabase user-client mapping)
- Cross-channel detection: same user on WhatsApp + Email = same record
- Context window = last 5-10 turns (token-aware truncation for GPT-4o)
- Structured: `{timestamp, channel, sender, message, attachments, function_calls}`

**Router**
- Receives normalized message
- Identifies client from phone_number_id (WhatsApp), page_id (Instagram), etc.
- Fetches client config: active modules, system prompt, rules
- Dispatches to correct agent instance

**Normalizer**
- Converts channel-specific message format to internal schema
- Extracts: text, media (image/video), sender_id, channel_type, timestamp
- Handles metadata: message_type (text/image/document), media_url, etc.

### Module System

Each module is a feature flag that can be toggled per client:
- `ventas`: Sales functionality (catalog, quotes, objection handling)
- `agendamiento`: Google Calendar booking integration
- `cobros_transferencias`: Payment verification with Vision
- `links_pago`: Payment link generation
- `calificacion_leads`: Automatic lead scoring
- `campanas_masivas`: Bulk messaging
- `analytics`: Dashboards and reports
- `alertas`: Notifications to business owner
- `seguimientos`: Auto follow-ups
- `documentos`: PDF/image handling

Agent checks module enablement before every action.

### Security Model

- **Authentication**: JWT with client_id + user_id
- **Authorization**: RLS at DB + middleware validation per client
- **Webhook Validation**: HMAC-SHA256 signature from Meta
- **Rate Limiting**: Per-client, per-user limits (configurable)
- **Secret Management**: All credentials in environment variables (never in code)
- **Data Protection**: Sensitive data encrypted at rest (API keys, credentials)
- **Audit Logging**: Immutable logs of all agent actions, payment verifications, escalations

### Billing Model

- **My Revenue**: Monthly subscription from each client (Stripe)
- **Client Payments**: Clients can accept payments via links (Stripe, MercadoPago, PayPal)
- **Token Costs**: I pay OpenAI; client limit enforced by message quota
- **Pausing**: If client doesn't pay after 3 days, agent pauses automatically
- **Reactivation**: Resume immediately when payment received

## Key Implementation Details

### GPT-4o Function Calling

Agent uses function_calling to invoke tools. Functions per module:

```python
# Sales module
get_catalog()
create_quote(product_id, quantity, customer_data)
apply_discount(reason, percentage)
handle_objection(objection_type, context)

# Agendamiento module
check_availability(date_range)
book_appointment(date, time, customer_data)
cancel_appointment(appointment_id)
reschedule_appointment(appointment_id, new_date, new_time)

# Cobros module
analyze_receipt_image(image_base64) → {valid, amount, account, timestamp, fraud_score}

# Links de pago
generate_payment_link(amount, description, payment_methods)

# Alerts
send_alert(priority, title, message) → notifies via WhatsApp/Email
```

### Conversation Memory Context

Memory system fetches:
- Last N turns (usually 5-10, adjusted for token count)
- User profile (from Supabase): name, company, purchase history, etc.
- Conversation state: current_topic, lead_score, last_interaction, etc.
- Module status: which features are relevant for THIS conversation

### Typing Indicators & Human Simulation

- Send "typing..." indicator before responding
- Variable delay based on message length (50ms per char minimum)
- Split responses >500 chars into 2-3 messages
- Never respond instantly (adds 0.5-2 second jitter)

### Cross-Channel User Identification

When message arrives:
1. Check if sender_id exists in any channel for this client
2. If yes, use existing user record (same conversation history)
3. If no, create new user record (different person)
4. Consolidate data: prefer Supabase record if exists

### Onboarding Flow

1. New client signs up
2. System auto-sends WhatsApp to admin with setup wizard
3. Onboarding agent asks questions: industry, services, catalog, prices, etc.
4. System auto-generates client config (system prompt, module defaults)
5. Client is notified to review; admin approves
6. Agent goes live

## Environment Variables

See `.env.example` for full list. Critical ones:

```
# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_ORG_ID=org-...

# Supabase
SUPABASE_URL=https://...supabase.co
SUPABASE_KEY=eyJ...
SUPABASE_SERVICE_KEY=eyJ...

# Redis
REDIS_URL=redis://localhost:6379

# Meta (one account for all clients' webhooks)
META_VERIFY_TOKEN=<random_token_for_webhook_validation>
META_ACCESS_TOKEN=<long_lived_token>

# My Stripe (for billing my clients)
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...

# Sendgrid
SENDGRID_API_KEY=SG....

# Google Calendar
GOOGLE_CALENDAR_CREDENTIALS_JSON=<base64_encoded_json>

# Env
ENVIRONMENT=development|production
LOG_LEVEL=DEBUG|INFO|WARNING|ERROR
```

## Database Schema (Key Tables)

- `clients`: Company/business records (SaaS customers)
- `users`: End users (customers of each client's business)
- `conversations`: Full history per user per channel
- `messages`: Individual messages with metadata
- `appointments`: Booking records (linked to Google Calendar)
- `leads`: Lead scoring snapshots and state
- `payments`: Payment verification records with Vision analysis
- `alerts_log`: Immutable audit log of all alerts sent
- `feature_toggles`: Module enablement per client
- `api_credentials`: Encrypted credentials (Google, Stripe, etc)
- `subscription`: Stripe subscription status per client
- `usage_logs`: Token count per client per day

All tables have RLS policies: `auth.uid()` and `current_client_id()` functions enforce isolation.

## Development Workflow

1. **Feature Planning**: Use `planner` agent for complex features
2. **TDD First**: Write tests before implementation (use `tdd-guide` agent)
3. **Code Review**: Run `code-reviewer` after writing code
4. **Type Checking**: `mypy` catches type errors (required)
5. **Security**: `security-reviewer` before any commit touching auth/secrets
6. **Testing**: Minimum 80% coverage required
7. **Commit**: Conventional commits format (feat, fix, refactor, test, docs)

## Common Development Tasks

```bash
# Add new module (e.g., integracion_crm.py)
1. Create /modulos/integracion_crm.py with function definitions
2. Add toggle to /config/modulos.py
3. Add test file tests/test_integracion_crm.py
4. Wire into agent.py function_calling definitions

# Add new channel (e.g., Telegram)
1. Create /canales/telegram.py with webhook handler
2. Add normalizer mapping in /core/normalizer.py
3. Add DB migration for new channel type
4. Wire router to identify Telegram messages

# Deploy to production
1. Commit to main branch
2. Docker image built automatically (CI/CD)
3. Deploy with zero-downtime (rolling update)
4. Verify with smoke tests
```

## Testing Guidelines

- **Unit tests**: Individual functions, no external calls (mock Redis, DB)
- **Integration tests**: Real Supabase + Redis, test message flow end-to-end
- **E2E tests**: Simulate full client journey (webhook → agent → response)
- **Fixtures**: Use pytest fixtures for clients, users, conversations
- **Mocking**: Mock OpenAI API in tests (expensive and slow)

## Performance Considerations

- **Token Optimization**: Truncate conversation history to stay under 4K tokens for GPT-4o
- **Redis Caching**: Cache client configs, module toggles, system prompts (TTL: 1 hour)
- **DB Indexes**: Indexed on: client_id, user_id, created_at, lead_score
- **Batch Operations**: Use batch insert for bulk messaging
- **Rate Limiting**: Per-client message limits enforced in middleware

## Deployment

- **Local**: `docker-compose up` (Redis + FastAPI + Streamlit)
- **Staging**: VPS on Hostinger (same Docker setup)
- **Production**: VPS on Hostinger with automated backups (30-day retention)
- **Monitoring**: Logs in JSON format, integrated with observability tool
- **Backups**: Supabase automated backups + weekly manual exports

## Important Notes

- **No Prompt Injection**: Validate all user inputs; never pass raw text to GPT
- **Conversation Isolation**: Every operation must verify client_id matches JWT
- **Graceful Degradation**: If OpenAI is down, queue messages and retry
- **Cost Control**: Track token usage per client; alert at 80% of monthly limit
- **Idempotency**: All webhooks must be idempotent (handle duplicate deliveries)
- **Compliance**: Handle data deletion requests per GDPR (soft delete, audit trail)

## References

- FastAPI: https://fastapi.tiangolo.com/
- Supabase: https://supabase.com/docs
- OpenAI: https://platform.openai.com/docs/
- Meta Cloud API: https://developers.facebook.com/docs/whatsapp/cloud-api/
- Redis: https://redis.io/documentation
- Stripe: https://stripe.com/docs
