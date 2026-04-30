-- ============================================================================
-- Agente-IA: Complete Database Schema for Supabase
-- Multi-tenant conversational AI agent platform
-- ============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- 1. CLIENTES - Business customers
-- ============================================================================

CREATE TABLE clientes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nombre VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    telefono VARCHAR(20),
    plan VARCHAR(50) NOT NULL DEFAULT 'starter', -- starter, professional, enterprise
    estado VARCHAR(50) NOT NULL DEFAULT 'activo', -- activo, pausado, suspendido, cancelado
    fecha_creacion TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    fecha_pago TIMESTAMP WITH TIME ZONE,
    stripe_customer_id VARCHAR(255),
    stripe_subscription_id VARCHAR(255),
    monthly_token_limit INTEGER DEFAULT 1000000,
    website VARCHAR(255),
    industria VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- 2. AGENTES - Agent configuration per client
-- ============================================================================

CREATE TABLE agentes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cliente_id UUID NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    nombre VARCHAR(255) NOT NULL,
    tono VARCHAR(50) DEFAULT 'profesional', -- profesional, amigable, entusiasta
    idioma VARCHAR(10) DEFAULT 'es', -- es, en, pt
    system_prompt TEXT,
    horario_atencion_inicio TIME DEFAULT '08:00',
    horario_atencion_fin TIME DEFAULT '18:00',
    zona_horaria VARCHAR(50) DEFAULT 'America/Guayaquil',
    feriados TEXT, -- JSON array of dates
    revela_que_es_ia BOOLEAN DEFAULT true,
    modelo_ia VARCHAR(50) DEFAULT 'gpt-4o',
    temperature DECIMAL(3,2) DEFAULT 0.7,
    max_tokens INTEGER DEFAULT 4000,
    response_delay_ms INTEGER DEFAULT 1000,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- 3. MODULOS_ACTIVOS - Feature toggles per client
-- ============================================================================

CREATE TABLE modulos_activos (
    cliente_id UUID PRIMARY KEY REFERENCES clientes(id) ON DELETE CASCADE,
    ventas BOOLEAN DEFAULT true,
    agendamiento BOOLEAN DEFAULT true,
    cobros BOOLEAN DEFAULT false,
    links_pago BOOLEAN DEFAULT false,
    calificacion BOOLEAN DEFAULT true,
    campanas BOOLEAN DEFAULT false,
    analytics BOOLEAN DEFAULT true,
    alertas BOOLEAN DEFAULT true,
    seguimientos BOOLEAN DEFAULT true,
    documentos BOOLEAN DEFAULT false,
    multiidioma BOOLEAN DEFAULT false,
    multi_agente BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- 4. CANALES_CONFIG - Channel credentials (encrypted)
-- ============================================================================

CREATE TABLE canales_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cliente_id UUID NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    canal VARCHAR(50) NOT NULL, -- whatsapp, instagram, facebook, email
    phone_number_id VARCHAR(255), -- for WhatsApp
    waba_id VARCHAR(255), -- WhatsApp Business Account ID
    token TEXT, -- encrypted access token
    page_id VARCHAR(255), -- for Instagram/Facebook
    email_address VARCHAR(255), -- for email channel
    activo BOOLEAN DEFAULT false,
    fecha_verificacion TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(cliente_id, canal)
);

-- ============================================================================
-- 5. PLANTILLAS_WHATSAPP - WhatsApp templates per client
-- ============================================================================

CREATE TABLE plantillas_whatsapp (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cliente_id UUID NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    nombre_plantilla VARCHAR(255) NOT NULL,
    tipo VARCHAR(50) NOT NULL, -- recordatorio_24h, recordatorio_1h, confirmacion, seguimiento
    contenido TEXT NOT NULL,
    variables TEXT, -- JSON array of variable names
    estado VARCHAR(50) DEFAULT 'pendiente', -- pendiente, aprobada, rechazada
    fecha_aprobacion TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- 6. USUARIOS - Super admins, admins, operators
-- ============================================================================

CREATE TABLE usuarios (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cliente_id UUID REFERENCES clientes(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    rol VARCHAR(50) NOT NULL DEFAULT 'operador', -- super_admin, admin, operador
    nombre_completo VARCHAR(255),
    activo BOOLEAN DEFAULT true,
    intentos_fallidos INTEGER DEFAULT 0,
    bloqueado_hasta TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(email, cliente_id)
);

-- ============================================================================
-- 7. CONVERSACIONES - Conversation history per end user
-- ============================================================================

CREATE TABLE conversaciones (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cliente_id UUID NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    canal VARCHAR(50) NOT NULL, -- whatsapp, instagram, facebook, email
    usuario_id VARCHAR(255) NOT NULL, -- external user ID from channel
    usuario_nombre VARCHAR(255),
    usuario_telefono VARCHAR(20),
    usuario_email VARCHAR(255),
    estado VARCHAR(50) DEFAULT 'activa', -- activa, esperando, escalada, cerrada
    assigned_to UUID REFERENCES usuarios(id) ON DELETE SET NULL, -- operator taking over
    lead_score INTEGER DEFAULT 0, -- 0-10
    lead_state VARCHAR(50), -- curioso, prospecto, caliente, cliente, descartado
    tema_actual VARCHAR(255), -- current conversation topic
    fecha_inicio TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    fecha_ultimo_mensaje TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    fecha_cierre TIMESTAMP WITH TIME ZONE,
    mensaje_count INTEGER DEFAULT 0,
    tokens_utilizados INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- 8. MENSAJES - Individual messages
-- ============================================================================

CREATE TABLE mensajes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversacion_id UUID NOT NULL REFERENCES conversaciones(id) ON DELETE CASCADE,
    cliente_id UUID NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    sender_id VARCHAR(255) NOT NULL, -- user ID or system
    sender_type VARCHAR(50) NOT NULL, -- user, agent, operator, system
    contenido TEXT NOT NULL,
    tipo VARCHAR(50) DEFAULT 'texto', -- texto, imagen, documento, audio
    media_url VARCHAR(500),
    media_type VARCHAR(50),
    tokens_utilizados INTEGER DEFAULT 0,
    function_calls TEXT, -- JSON of GPT function calls made
    estado VARCHAR(50) DEFAULT 'enviado', -- enviado, entregado, leido
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- 9. LEADS - Qualified prospects
-- ============================================================================

CREATE TABLE leads (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cliente_id UUID NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    conversacion_id UUID REFERENCES conversaciones(id) ON DELETE SET NULL,
    nombre VARCHAR(255) NOT NULL,
    telefono VARCHAR(20),
    email VARCHAR(255),
    canal VARCHAR(50), -- whatsapp, instagram, facebook, email
    score INTEGER DEFAULT 0, -- 0-10
    estado VARCHAR(50) DEFAULT 'prospecto', -- prospecto, caliente, cliente, descartado
    urgencia VARCHAR(50), -- baja, media, alta, critica
    presupuesto_estimado DECIMAL(12,2),
    decision VARCHAR(50), -- poco_probable, posible, probable, muy_probable
    notas TEXT,
    seguimiento_proxima_fecha TIMESTAMP WITH TIME ZONE,
    asignado_a UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- 10. CITAS - Business appointments
-- ============================================================================

CREATE TABLE citas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cliente_id UUID NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    lead_id UUID REFERENCES leads(id) ON DELETE SET NULL,
    conversacion_id UUID REFERENCES conversaciones(id) ON DELETE SET NULL,
    nombre_cliente VARCHAR(255) NOT NULL,
    telefono_cliente VARCHAR(20),
    email_cliente VARCHAR(255),
    servicio VARCHAR(255) NOT NULL,
    fecha DATE NOT NULL,
    hora TIME NOT NULL,
    duracion_minutos INTEGER DEFAULT 30,
    estado VARCHAR(50) DEFAULT 'pendiente', -- pendiente, confirmada, cancelada, completada
    google_event_id VARCHAR(255),
    zoom_url VARCHAR(500),
    notas TEXT,
    recordatorio_24h_enviado BOOLEAN DEFAULT false,
    recordatorio_1h_enviado BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- 11. PAGOS - Payment verification records
-- ============================================================================

CREATE TABLE pagos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cliente_id UUID NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    conversacion_id UUID REFERENCES conversaciones(id) ON DELETE SET NULL,
    monto DECIMAL(12,2) NOT NULL,
    moneda VARCHAR(3) DEFAULT 'USD',
    metodo_pago VARCHAR(50), -- transferencia, tarjeta, efectivo, otro
    estado VARCHAR(50) DEFAULT 'pendiente', -- pendiente, verificado, rechazado, dudoso
    comprobante_url VARCHAR(500),
    numero_transaccion VARCHAR(255),
    verificado_por UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    fecha_verificacion TIMESTAMP WITH TIME ZONE,
    banco_origen VARCHAR(100),
    banco_destino VARCHAR(100),
    cuenta_destino VARCHAR(50),
    fraud_score DECIMAL(3,2), -- 0-1 confidence score
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- 12. COMPROBANTES_PROCESADOS - Anti-duplicate for payments
-- ============================================================================

CREATE TABLE comprobantes_procesados (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    numero_transaccion VARCHAR(255) NOT NULL,
    cliente_id UUID NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    monto DECIMAL(12,2) NOT NULL,
    fecha_procesado TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(numero_transaccion, cliente_id)
);

-- ============================================================================
-- 13. ALERTAS - Alert log
-- ============================================================================

CREATE TABLE alertas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cliente_id UUID NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    tipo VARCHAR(50) NOT NULL, -- critica, importante, informativa
    mensaje TEXT NOT NULL,
    canal_envio VARCHAR(50), -- whatsapp, email, dashboard
    leida BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- 14. USO_TOKENS - Token consumption control
-- ============================================================================

CREATE TABLE uso_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cliente_id UUID NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    mes INTEGER NOT NULL,
    año INTEGER NOT NULL,
    tokens_input INTEGER DEFAULT 0,
    tokens_output INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    total_mensajes INTEGER DEFAULT 0,
    limite_mensajes INTEGER DEFAULT 1000000,
    alerta_80_enviada BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(cliente_id, mes, año)
);

-- ============================================================================
-- 15. CAMPANAS - Bulk messaging campaigns
-- ============================================================================

CREATE TABLE campanas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cliente_id UUID NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    nombre VARCHAR(255) NOT NULL,
    estado VARCHAR(50) DEFAULT 'borrador', -- borrador, programada, en_progreso, completada, cancelada
    plantilla TEXT NOT NULL,
    segmento VARCHAR(100), -- all, hot_leads, new_leads, etc
    total_enviados INTEGER DEFAULT 0,
    total_respondidos INTEGER DEFAULT 0,
    tasa_respuesta DECIMAL(5,2),
    fecha_envio TIMESTAMP WITH TIME ZONE,
    fecha_inicio_programada TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- 16. DATOS_BANCARIOS - Business bank accounts (encrypted)
-- ============================================================================

CREATE TABLE datos_bancarios (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cliente_id UUID NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    banco VARCHAR(100) NOT NULL,
    tipo_cuenta VARCHAR(50), -- corriente, ahorros
    numero_cuenta TEXT, -- encrypted
    titular VARCHAR(255) NOT NULL,
    ruc VARCHAR(20),
    pais VARCHAR(50) DEFAULT 'Ecuador',
    activo BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- INDEXES - Performance optimization
-- ============================================================================

-- clientes
CREATE INDEX idx_clientes_email ON clientes(email);
CREATE INDEX idx_clientes_estado ON clientes(estado);
CREATE INDEX idx_clientes_stripe_customer ON clientes(stripe_customer_id);

-- agentes
CREATE INDEX idx_agentes_cliente_id ON agentes(cliente_id);

-- modulos_activos
CREATE INDEX idx_modulos_activos_cliente_id ON modulos_activos(cliente_id);

-- canales_config
CREATE INDEX idx_canales_config_cliente_id ON canales_config(cliente_id);
CREATE INDEX idx_canales_config_canal ON canales_config(cliente_id, canal);

-- plantillas_whatsapp
CREATE INDEX idx_plantillas_whatsapp_cliente_id ON plantillas_whatsapp(cliente_id);
CREATE INDEX idx_plantillas_whatsapp_tipo ON plantillas_whatsapp(cliente_id, tipo);

-- usuarios
CREATE INDEX idx_usuarios_email ON usuarios(email);
CREATE INDEX idx_usuarios_cliente_id ON usuarios(cliente_id);
CREATE INDEX idx_usuarios_rol ON usuarios(cliente_id, rol);

-- conversaciones
CREATE INDEX idx_conversaciones_cliente_id ON conversaciones(cliente_id);
CREATE INDEX idx_conversaciones_usuario_id ON conversaciones(cliente_id, usuario_id);
CREATE INDEX idx_conversaciones_canal ON conversaciones(cliente_id, canal);
CREATE INDEX idx_conversaciones_estado ON conversaciones(cliente_id, estado);
CREATE INDEX idx_conversaciones_assigned_to ON conversaciones(assigned_to);
CREATE INDEX idx_conversaciones_fecha_ultimo ON conversaciones(fecha_ultimo_mensaje DESC);

-- mensajes
CREATE INDEX idx_mensajes_conversacion_id ON mensajes(conversacion_id);
CREATE INDEX idx_mensajes_cliente_id ON mensajes(cliente_id);
CREATE INDEX idx_mensajes_sender_type ON mensajes(conversacion_id, sender_type);
CREATE INDEX idx_mensajes_created_at ON mensajes(created_at DESC);

-- leads
CREATE INDEX idx_leads_cliente_id ON leads(cliente_id);
CREATE INDEX idx_leads_score ON leads(cliente_id, score DESC);
CREATE INDEX idx_leads_estado ON leads(cliente_id, estado);
CREATE INDEX idx_leads_telefono ON leads(telefono);
CREATE INDEX idx_leads_email ON leads(email);

-- citas
CREATE INDEX idx_citas_cliente_id ON citas(cliente_id);
CREATE INDEX idx_citas_fecha ON citas(cliente_id, fecha);
CREATE INDEX idx_citas_estado ON citas(cliente_id, estado);
CREATE INDEX idx_citas_lead_id ON citas(lead_id);

-- pagos
CREATE INDEX idx_pagos_cliente_id ON pagos(cliente_id);
CREATE INDEX idx_pagos_numero_transaccion ON pagos(numero_transaccion);
CREATE INDEX idx_pagos_estado ON pagos(cliente_id, estado);
CREATE INDEX idx_pagos_fecha_verificacion ON pagos(fecha_verificacion DESC);

-- comprobantes_procesados
CREATE INDEX idx_comprobantes_numero ON comprobantes_procesados(numero_transaccion);
CREATE INDEX idx_comprobantes_cliente ON comprobantes_procesados(cliente_id);

-- alertas
CREATE INDEX idx_alertas_cliente_id ON alertas(cliente_id);
CREATE INDEX idx_alertas_tipo ON alertas(cliente_id, tipo);
CREATE INDEX idx_alertas_leida ON alertas(cliente_id, leida);

-- uso_tokens
CREATE INDEX idx_uso_tokens_cliente_id ON uso_tokens(cliente_id);
CREATE INDEX idx_uso_tokens_periodo ON uso_tokens(cliente_id, año, mes);

-- campanas
CREATE INDEX idx_campanas_cliente_id ON campanas(cliente_id);
CREATE INDEX idx_campanas_estado ON campanas(cliente_id, estado);

-- datos_bancarios
CREATE INDEX idx_datos_bancarios_cliente_id ON datos_bancarios(cliente_id);

-- ============================================================================
-- ROW LEVEL SECURITY (RLS) - Multi-tenant isolation
-- ============================================================================

-- Enable RLS on all tables
ALTER TABLE clientes ENABLE ROW LEVEL SECURITY;
ALTER TABLE agentes ENABLE ROW LEVEL SECURITY;
ALTER TABLE modulos_activos ENABLE ROW LEVEL SECURITY;
ALTER TABLE canales_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE plantillas_whatsapp ENABLE ROW LEVEL SECURITY;
ALTER TABLE usuarios ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversaciones ENABLE ROW LEVEL SECURITY;
ALTER TABLE mensajes ENABLE ROW LEVEL SECURITY;
ALTER TABLE leads ENABLE ROW LEVEL SECURITY;
ALTER TABLE citas ENABLE ROW LEVEL SECURITY;
ALTER TABLE pagos ENABLE ROW LEVEL SECURITY;
ALTER TABLE comprobantes_procesados ENABLE ROW LEVEL SECURITY;
ALTER TABLE alertas ENABLE ROW LEVEL SECURITY;
ALTER TABLE uso_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE campanas ENABLE ROW LEVEL SECURITY;
ALTER TABLE datos_bancarios ENABLE ROW LEVEL SECURITY;

-- Helper function to get current client_id from JWT
CREATE OR REPLACE FUNCTION get_current_client_id()
RETURNS UUID AS $$
    SELECT (current_setting('request.jwt.claims', true)::jsonb->>'client_id')::uuid;
$$ LANGUAGE SQL STABLE;

-- Helper function to get current user role
CREATE OR REPLACE FUNCTION get_current_role()
RETURNS TEXT AS $$
    SELECT current_setting('request.jwt.claims', true)::jsonb->>'role';
$$ LANGUAGE SQL STABLE;

-- Helper function to check if user is super_admin
CREATE OR REPLACE FUNCTION is_super_admin()
RETURNS BOOLEAN AS $$
    SELECT get_current_role() = 'super_admin';
$$ LANGUAGE SQL STABLE;

-- ============================================================================
-- RLS POLICIES: clientes
-- ============================================================================

-- Super admin can see all clients
CREATE POLICY "super_admin_can_see_all_clients" ON clientes
    FOR SELECT TO authenticated
    USING (is_super_admin());

-- Users can see their own client
CREATE POLICY "users_can_see_own_client" ON clientes
    FOR SELECT TO authenticated
    USING (id = get_current_client_id());

-- Super admin can insert clients
CREATE POLICY "super_admin_can_insert_clients" ON clientes
    FOR INSERT TO authenticated
    WITH CHECK (is_super_admin());

-- Super admin can update clients
CREATE POLICY "super_admin_can_update_clients" ON clientes
    FOR UPDATE TO authenticated
    USING (is_super_admin());

-- ============================================================================
-- RLS POLICIES: agentes
-- ============================================================================

CREATE POLICY "clients_can_see_own_agents" ON agentes
    FOR SELECT TO authenticated
    USING (cliente_id = get_current_client_id() OR is_super_admin());

CREATE POLICY "clients_can_insert_own_agents" ON agentes
    FOR INSERT TO authenticated
    WITH CHECK (cliente_id = get_current_client_id() OR is_super_admin());

CREATE POLICY "clients_can_update_own_agents" ON agentes
    FOR UPDATE TO authenticated
    USING (cliente_id = get_current_client_id() OR is_super_admin());

-- ============================================================================
-- RLS POLICIES: modulos_activos
-- ============================================================================

CREATE POLICY "clients_can_see_own_modules" ON modulos_activos
    FOR SELECT TO authenticated
    USING (cliente_id = get_current_client_id() OR is_super_admin());

CREATE POLICY "clients_can_update_own_modules" ON modulos_activos
    FOR UPDATE TO authenticated
    USING (cliente_id = get_current_client_id() OR is_super_admin());

-- ============================================================================
-- RLS POLICIES: canales_config
-- ============================================================================

CREATE POLICY "clients_can_see_own_channels" ON canales_config
    FOR SELECT TO authenticated
    USING (cliente_id = get_current_client_id() OR is_super_admin());

CREATE POLICY "clients_can_insert_own_channels" ON canales_config
    FOR INSERT TO authenticated
    WITH CHECK (cliente_id = get_current_client_id() OR is_super_admin());

CREATE POLICY "clients_can_update_own_channels" ON canales_config
    FOR UPDATE TO authenticated
    USING (cliente_id = get_current_client_id() OR is_super_admin());

-- ============================================================================
-- RLS POLICIES: plantillas_whatsapp
-- ============================================================================

CREATE POLICY "clients_can_see_own_templates" ON plantillas_whatsapp
    FOR SELECT TO authenticated
    USING (cliente_id = get_current_client_id() OR is_super_admin());

CREATE POLICY "clients_can_insert_own_templates" ON plantillas_whatsapp
    FOR INSERT TO authenticated
    WITH CHECK (cliente_id = get_current_client_id() OR is_super_admin());

CREATE POLICY "clients_can_update_own_templates" ON plantillas_whatsapp
    FOR UPDATE TO authenticated
    USING (cliente_id = get_current_client_id() OR is_super_admin());

-- ============================================================================
-- RLS POLICIES: usuarios
-- ============================================================================

CREATE POLICY "super_admin_can_see_all_users" ON usuarios
    FOR SELECT TO authenticated
    USING (is_super_admin());

CREATE POLICY "users_can_see_own_client_users" ON usuarios
    FOR SELECT TO authenticated
    USING (cliente_id = get_current_client_id());

CREATE POLICY "clients_can_insert_own_users" ON usuarios
    FOR INSERT TO authenticated
    WITH CHECK (cliente_id = get_current_client_id() OR is_super_admin());

-- ============================================================================
-- RLS POLICIES: conversaciones
-- ============================================================================

CREATE POLICY "clients_can_see_own_conversations" ON conversaciones
    FOR SELECT TO authenticated
    USING (cliente_id = get_current_client_id() OR is_super_admin());

CREATE POLICY "clients_can_insert_own_conversations" ON conversaciones
    FOR INSERT TO authenticated
    WITH CHECK (cliente_id = get_current_client_id());

CREATE POLICY "clients_can_update_own_conversations" ON conversaciones
    FOR UPDATE TO authenticated
    USING (cliente_id = get_current_client_id() OR is_super_admin());

-- ============================================================================
-- RLS POLICIES: mensajes
-- ============================================================================

CREATE POLICY "clients_can_see_own_messages" ON mensajes
    FOR SELECT TO authenticated
    USING (cliente_id = get_current_client_id() OR is_super_admin());

CREATE POLICY "clients_can_insert_own_messages" ON mensajes
    FOR INSERT TO authenticated
    WITH CHECK (cliente_id = get_current_client_id());

-- ============================================================================
-- RLS POLICIES: leads
-- ============================================================================

CREATE POLICY "clients_can_see_own_leads" ON leads
    FOR SELECT TO authenticated
    USING (cliente_id = get_current_client_id() OR is_super_admin());

CREATE POLICY "clients_can_insert_own_leads" ON leads
    FOR INSERT TO authenticated
    WITH CHECK (cliente_id = get_current_client_id());

CREATE POLICY "clients_can_update_own_leads" ON leads
    FOR UPDATE TO authenticated
    USING (cliente_id = get_current_client_id() OR is_super_admin());

-- ============================================================================
-- RLS POLICIES: citas
-- ============================================================================

CREATE POLICY "clients_can_see_own_appointments" ON citas
    FOR SELECT TO authenticated
    USING (cliente_id = get_current_client_id() OR is_super_admin());

CREATE POLICY "clients_can_insert_own_appointments" ON citas
    FOR INSERT TO authenticated
    WITH CHECK (cliente_id = get_current_client_id());

CREATE POLICY "clients_can_update_own_appointments" ON citas
    FOR UPDATE TO authenticated
    USING (cliente_id = get_current_client_id() OR is_super_admin());

-- ============================================================================
-- RLS POLICIES: pagos
-- ============================================================================

CREATE POLICY "clients_can_see_own_payments" ON pagos
    FOR SELECT TO authenticated
    USING (cliente_id = get_current_client_id() OR is_super_admin());

CREATE POLICY "clients_can_insert_own_payments" ON pagos
    FOR INSERT TO authenticated
    WITH CHECK (cliente_id = get_current_client_id());

CREATE POLICY "clients_can_update_own_payments" ON pagos
    FOR UPDATE TO authenticated
    USING (cliente_id = get_current_client_id() OR is_super_admin());

-- ============================================================================
-- RLS POLICIES: comprobantes_procesados
-- ============================================================================

CREATE POLICY "clients_can_see_own_receipts" ON comprobantes_procesados
    FOR SELECT TO authenticated
    USING (cliente_id = get_current_client_id() OR is_super_admin());

CREATE POLICY "clients_can_insert_own_receipts" ON comprobantes_procesados
    FOR INSERT TO authenticated
    WITH CHECK (cliente_id = get_current_client_id());

-- ============================================================================
-- RLS POLICIES: alertas
-- ============================================================================

CREATE POLICY "clients_can_see_own_alerts" ON alertas
    FOR SELECT TO authenticated
    USING (cliente_id = get_current_client_id() OR is_super_admin());

CREATE POLICY "system_can_insert_alerts" ON alertas
    FOR INSERT TO authenticated
    WITH CHECK (cliente_id = get_current_client_id() OR is_super_admin());

-- ============================================================================
-- RLS POLICIES: uso_tokens
-- ============================================================================

CREATE POLICY "clients_can_see_own_token_usage" ON uso_tokens
    FOR SELECT TO authenticated
    USING (cliente_id = get_current_client_id() OR is_super_admin());

CREATE POLICY "system_can_insert_token_usage" ON uso_tokens
    FOR INSERT TO authenticated
    WITH CHECK (cliente_id = get_current_client_id());

CREATE POLICY "system_can_update_token_usage" ON uso_tokens
    FOR UPDATE TO authenticated
    USING (cliente_id = get_current_client_id() OR is_super_admin());

-- ============================================================================
-- RLS POLICIES: campanas
-- ============================================================================

CREATE POLICY "clients_can_see_own_campaigns" ON campanas
    FOR SELECT TO authenticated
    USING (cliente_id = get_current_client_id() OR is_super_admin());

CREATE POLICY "clients_can_insert_own_campaigns" ON campanas
    FOR INSERT TO authenticated
    WITH CHECK (cliente_id = get_current_client_id());

CREATE POLICY "clients_can_update_own_campaigns" ON campanas
    FOR UPDATE TO authenticated
    USING (cliente_id = get_current_client_id() OR is_super_admin());

-- ============================================================================
-- RLS POLICIES: datos_bancarios
-- ============================================================================

CREATE POLICY "clients_can_see_own_bank_accounts" ON datos_bancarios
    FOR SELECT TO authenticated
    USING (cliente_id = get_current_client_id() OR is_super_admin());

CREATE POLICY "clients_can_insert_own_bank_accounts" ON datos_bancarios
    FOR INSERT TO authenticated
    WITH CHECK (cliente_id = get_current_client_id() OR is_super_admin());

CREATE POLICY "clients_can_update_own_bank_accounts" ON datos_bancarios
    FOR UPDATE TO authenticated
    USING (cliente_id = get_current_client_id() OR is_super_admin());

-- ============================================================================
-- TRIGGERS - Automatic timestamps
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers for all tables with updated_at
CREATE TRIGGER update_clientes_timestamp BEFORE UPDATE ON clientes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_agentes_timestamp BEFORE UPDATE ON agentes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_modulos_activos_timestamp BEFORE UPDATE ON modulos_activos
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_canales_config_timestamp BEFORE UPDATE ON canales_config
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_plantillas_whatsapp_timestamp BEFORE UPDATE ON plantillas_whatsapp
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_usuarios_timestamp BEFORE UPDATE ON usuarios
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_conversaciones_timestamp BEFORE UPDATE ON conversaciones
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_leads_timestamp BEFORE UPDATE ON leads
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_citas_timestamp BEFORE UPDATE ON citas
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_pagos_timestamp BEFORE UPDATE ON pagos
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_uso_tokens_timestamp BEFORE UPDATE ON uso_tokens
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_campanas_timestamp BEFORE UPDATE ON campanas
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_datos_bancarios_timestamp BEFORE UPDATE ON datos_bancarios
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- ADDITIONAL HELPER FUNCTIONS
-- ============================================================================

-- Function to get client MRR (Monthly Recurring Revenue)
CREATE OR REPLACE FUNCTION get_client_mrr(client_id UUID)
RETURNS DECIMAL AS $$
BEGIN
    RETURN (
        SELECT COALESCE(
            (monthly_token_limit::numeric / 1000000) * 0.02,
            0
        )
        FROM clientes
        WHERE id = client_id
            AND estado = 'activo'
    );
END;
$$ LANGUAGE plpgsql;

-- Function to get lead score based on conversation
CREATE OR REPLACE FUNCTION calculate_lead_score(conversation_id UUID)
RETURNS INTEGER AS $$
DECLARE
    message_count INT;
    last_7_days_messages INT;
    score INT := 0;
BEGIN
    -- Get total messages
    SELECT COUNT(*) INTO message_count
    FROM mensajes
    WHERE conversacion_id = conversation_id
        AND sender_type = 'user';

    -- Get messages in last 7 days
    SELECT COUNT(*) INTO last_7_days_messages
    FROM mensajes
    WHERE conversacion_id = conversation_id
        AND sender_type = 'user'
        AND created_at > NOW() - INTERVAL '7 days';

    -- Calculate score: more engaged = higher score
    score := LEAST(10, (message_count / 10) + (last_7_days_messages * 2));

    RETURN GREATEST(0, score);
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- DOCUMENTATION
-- ============================================================================

/*
MULTI-TENANT ARCHITECTURE:

1. Row Level Security (RLS) enforced at database level
2. All queries automatically filtered by get_current_client_id()
3. Super admins bypass RLS with is_super_admin() check
4. JWT claims contain: client_id, user_id, role, email

ENCRYPTION:

- Encrypted fields: token, numero_cuenta, numero_transaccion
- Use Supabase pgcrypto or application-level encryption
- Decryption happens only when needed

PERFORMANCE:

- Indexed on: cliente_id, channel, estado, timestamps
- Composite indexes for common queries
- Consider partitioning large tables (mensajes, uso_tokens)

BACKUP STRATEGY:

- Daily automated Supabase backups
- Monthly exports to cold storage
- Test restore procedures monthly

DATA RETENTION:

- Conversaciones: 12 months
- Mensajes: 6 months (archive older)
- Pagos: 7 years (compliance)
- Alertas: 3 months
*/
