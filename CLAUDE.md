# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Agente-IA** is a multi-tenant SaaS platform for conversational AI agents that serve businesses. Each client owns their own AI agent that interacts with their end users through multiple channels (WhatsApp, Instagram, Facebook, Email).

### Tech Stack

- **Backend**: Python 3.11 + FastAPI
- **AI**: OpenAI GPT-4o with function calling
- **Database**: Supabase (PostgreSQL + Row Level Security)
- **Cache/Queue**: Redis
- **Payments**: Payphone (business subscription + client payment links), MercadoPago/PayPal (client links)
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
│   ├── links_pago.py      → Payment requests (Payphone, MercadoPago, PayPal)
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
│   ├── payphone.py        → Monthly client billing (Payphone API Sale)
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

- **My Revenue**: Monthly subscription from each client (Payphone — push payment to client's app)
- **Client Payments**: Clients can accept payments via Payphone, MercadoPago, PayPal
- **Token Costs**: I pay OpenAI; client limit enforced by message quota
- **Pausing**: If client doesn't pay after 3 days, agent pauses automatically
- **Reactivation**: Resume immediately when payment received

#### Payphone Payment Flow (API Sale)
Payphone is a push-payment model — no redirect link, the payer receives a push notification in their Payphone app:
1. `POST https://pay.payphonetodoesposible.com/api/Sale` with payer's `phoneNumber` + `countryCode`
2. Payphone sends push notification to payer's mobile app
3. Payer approves/rejects within **5 minutes**
4. Payphone POSTs to `PAYPHONE_RESPONSE_URL` with `?id=<transactionId>&clientTransactionID=<uuid>`
5. Backend calls `POST /button/V2/Confirm` to verify → updates `subscription` table
- Auth: `Authorization: Bearer PAYPHONE_TOKEN`
- Amount in **centavos** (USD × 100): $1.49 → 149
- Required fields: `phoneNumber`, `countryCode`, `amount`, `currency`, `clientTransactionId`

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

# Payphone (for billing my clients — Ecuadorian payment gateway)
PAYPHONE_TOKEN=<token_from_payphone_developer>
PAYPHONE_STORE_ID=<store_id_optional>
PAYPHONE_RESPONSE_URL=https://api.lanlabsec.com/webhooks/payphone

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
- `subscription`: Payphone subscription status per client (columns: payphone_client_transaction_id, payphone_transaction_id)
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
- Payphone: https://docs.payphone.app/api-sale

---

# LanLabs - Agente IA SaaS WhatsApp

## Estado del Proyecto
Plataforma SaaS multi-tenant de agentes IA conversacionales. **En producción.**

## Infraestructura
- API: https://api.lanlabsec.com (FastAPI + Python, VPS Hostinger Easypanel)
- Dashboard: https://dashboard.lanlabsec.com (Next.js, Vercel)
- DB: Supabase (PostgreSQL) - proyecto SaasAIWhatsApp
- Cache: Redis Cloud
- VPS: 147.79.75.41
- GitHub: A13XMC11/agente-ia (rama main)

## Stack
- Backend: Python 3.11, FastAPI, OpenAI GPT-4o, Supabase, Redis
- Frontend: Next.js, TypeScript, Tailwind CSS v4
- IA: GPT-4o (function calling), Whisper (audio), GPT-4o Vision (comprobantes)
- Integraciones: Meta Cloud API, Google Calendar (Service Account), Payphone, SendGrid

## Cliente de Prueba
- ID: d21c2725-7e2d-442b-8207-958fd4bcb038
- Email: alexander777800@gmail.com
- WhatsApp número real: +593 99 267 2980
- Phone Number ID: 1108311609031850
- WABA ID: 1474171134171462
- Google Calendar ID: alexander777800@gmail.com

## Agente Configurado
- Nombre: Sofía
- Empresa: LanLabs
- Servicios: Plan Básico $149/mes, Profesional $249/mes, Empresarial $399/mes
- Zona horaria: America/Guayaquil

## Paleta de Colores Dashboard (globals.css)
El dashboard usa un tema OLED azul oscuro (diferente a la paleta original en este doc):
- `--background`: #060D13
- `--surface`: #0F1E2D
- `--accent`: #38BDF8 (sky blue)
- `--success`: #22D3A0
- Fuente: Geist

## Funcionalidades Completadas ✅
- Panel super_admin con métricas MRR y churn (2026-05-28)
- Agente WhatsApp con GPT-4o y número real
- Instagram y Facebook (canales/instagram.py, canales/facebook.py)
- Agendamiento con Google Calendar (Service Account)
- Transferencias bancarias con GPT-4o Vision
- Procesamiento de audios con Whisper
- Alertas al dueño por WhatsApp en tiempo real
- Calificación de leads acumulativa (score 0-10)
- Seguimientos automáticos (APScheduler cada 30min)
- Links de pago (Payphone, MercadoPago, PayPal) — modulos/links_pago.py
- Campañas masivas — modulos/campanas.py
- Dashboard Next.js completo con datos reales
- Login JWT con roles (super_admin, admin, operador)
- Billing / Payphone — suscripciones, cancelación, reactivación (push payment a app Payphone)
- Analytics en dashboard — métricas, gráficos por día/canal/estado
- Onboarding de clientes (wizard 4 pasos)
- Aprobación de pagos desde dashboard
- Página de configuración WhatsApp self-service
- Guía de onboarding descargable
- Email de bienvenida al cliente (SendGrid) via POST /internal/send-email
- Creación de usuario en Supabase Auth al registrar cliente (login funcional)
- Identificación de cliente por waba_id como fallback + auto-update de phone_number_id (2026-05-24)
- UI de Campañas Masivas en dashboard — página /cliente/campanas con crear, lanzar y cancelar (2026-05-24)

## Pendiente / Roadmap
- Instagram/Facebook: configuración self-service desde dashboard (esperando cuentas Meta)
- Onboarding self-service completo:
  - Landing page pública (lanlabsec.com) con planes y CTA
  - Página de registro público: cliente llena datos, elige plan, paga con Payphone
  - Email de bienvenida automático con credenciales tras pago confirmado
  - Wizard post-login: primer ingreso guía al cliente a conectar WhatsApp y configurar agente
  (Hoy el super_admin crea clientes manualmente desde /admin/clientes/nuevo)

## Arquitectura Futura (cuando haya clientes enterprise)
### DB dedicada por cliente enterprise
Cuando un cliente pague >$1k/mes y requiera aislamiento total:
1. Crear nuevo proyecto Supabase para ese cliente
2. Correr las mismas migraciones en el nuevo proyecto
3. Guardar credenciales en tabla `clientes`: columnas `supabase_url` + `supabase_service_key` (encriptado)
4. Modificar `core/router.py` → `_get_or_create_agent()` para detectar si el cliente tiene DB propia y usar `create_client()` con esas credenciales
5. Migrar datos existentes del cliente desde DB compartida a la nueva
Hoy todos los clientes comparten 1 Supabase con RLS — correcto para planes $149-$399/mes.

## Tablas Supabase (RLS habilitado en todas)
leads, canales_config, clientes, conversaciones,
mensajes, agentes, modulos_activos, datos_bancarios,
alertas, citas, pagos, comprobantes_procesados,
campanas, campaign_recipients

RLS re-habilitado en `leads` el 2026-05-22.
Tablas campanas y campaign_recipients creadas el 2026-05-24.
El dashboard y backend usan service_role, que bypasea RLS.

## Variables de Entorno Backend (Easypanel)
META_VERIFY_TOKEN=agente-ia
META_ACCESS_TOKEN=...
META_PHONE_NUMBER_ID=1108311609031850
GOOGLE_CALENDAR_CREDENTIALS_JSON=...
GOOGLE_CALENDAR_ID=alexander777800@gmail.com
GOOGLE_CALENDAR_TIMEZONE=America/Guayaquil
SUPABASE_URL=...
SUPABASE_KEY=... (anon)
SUPABASE_SERVICE_KEY=...
OPENAI_API_KEY=...
REDIS_URL=...
SENDGRID_API_KEY=SG....
PAYPHONE_TOKEN=...
PAYPHONE_STORE_ID=...
PAYPHONE_RESPONSE_URL=https://api.lanlabsec.com/webhooks/payphone

## Variables de Entorno Dashboard (Vercel)
NEXT_PUBLIC_SUPABASE_URL=...
NEXT_PUBLIC_SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...
JWT_SECRET=...
NEXT_PUBLIC_API_URL=https://api.lanlabsec.com
NEXT_PUBLIC_APP_URL=https://dashboard.lanlabsec.com

## Estructura del Proyecto
/core: agent.py, buffer.py, memory.py, router.py, normalizer.py
/modulos: ventas.py, agendamiento.py, cobros.py, links_pago.py,
          calificacion.py, campanas.py, alertas.py, seguimiento.py, analytics.py
/canales: whatsapp.py, instagram.py, facebook.py, email.py
/billing: payphone.py, usage.py
/migrations: create_campanas.sql, add_follow_up_columns.sql, (re)enable_rls_leads.sql
/dashboard-next: Next.js dashboard (app router)
  /app/admin: gestión de clientes (super_admin)
  /app/cliente: panel del cliente (conversaciones, leads, citas, pagos,
                analytics, billing, campanas, configuración)
  /app/api/cliente: leads, citas, pagos, conversaciones, campanas, whatsapp, billing, etc.
main.py, Dockerfile, requirements.txt

## Notas Importantes
- El campo whatsapp_dueño tiene ñ — usar select('*')
  en queries de Supabase para evitar errores de parsing
- El agente usa supabase_service_client para todas
  las operaciones (no el cliente anon)
- Los logs de debug con print() aparecen en Easypanel.
  Los logger.info() NO aparecen en Easypanel.
- El token de Meta es permanente (no expira)
- Google Calendar usa Service Account (no OAuth2)
- Al crear cliente: createAuthUser crea el usuario en Supabase Auth
  y el registro en tabla usuarios (necesario para login y JWT con rol/cliente_id)
- El endpoint POST /internal/send-email del backend envía emails via SendGrid
  (usado por el dashboard Next.js para el email de bienvenida)
- Identificación WhatsApp (core/router.py → identify_client):
  1. Busca por phone_number_id en canales_config (camino rápido)
  2. Si no encuentra, usa waba_id del entry como fallback
  3. Si encuentra por waba_id, actualiza phone_number_id en Supabase automáticamente
  Esto resuelve el caso donde Meta asigna un phone_number_id diferente al número
  real vs. el número de prueba. El fix se auto-corrige en el primer mensaje.
