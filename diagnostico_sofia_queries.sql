-- 🔍 Diagnóstico de configuración de Sofía en Supabase
-- Ejecuta estas queries en la Supabase SQL Editor

-- ============================================================================
-- 1. Verifica que Sofía existe en tabla 'clientes'
-- ============================================================================

SELECT id, nombre, estado, created_at
FROM clientes
WHERE nombre ILIKE '%sofía%'
   OR nombre ILIKE '%sofia%'
   OR nombre ILIKE '%lanlabs%'
LIMIT 10;

-- Esperado: Al menos 1 registro con id = 'd21c2725-7e2d-442b-8207-958fd4bcb038'


-- ============================================================================
-- 2. Verifica el mapping en 'canales_config' (WhatsApp)
-- ============================================================================

SELECT id, cliente_id, canal, phone_number_id, page_id, created_at
FROM canales_config
WHERE cliente_id = 'd21c2725-7e2d-442b-8207-958fd4bcb038'
  AND canal = 'whatsapp';

-- Esperado: 1 registro con phone_number_id (ej: 1108311609031850)


-- ============================================================================
-- 3. Verifica la configuración del agente en tabla 'agentes'
-- ============================================================================

SELECT
    id,
    cliente_id,
    system_prompt,
    temperature,
    max_tokens,
    active_modules,
    created_at,
    updated_at
FROM agentes
WHERE cliente_id = 'd21c2725-7e2d-442b-8207-958fd4bcb038';

-- Esperado:
-- - 1 registro
-- - system_prompt NO es NULL, NO es vacío
-- - system_prompt menciona "Sofía" y "LanLabs"
-- - active_modules es JSON válido


-- ============================================================================
-- 4. Si el registro de agentes NO existe, inserta uno
-- ============================================================================

INSERT INTO agentes (
    cliente_id,
    system_prompt,
    temperature,
    max_tokens,
    active_modules,
    created_at,
    updated_at
)
VALUES (
    'd21c2725-7e2d-442b-8207-958fd4bcb038',
    'Eres Sofía, asistente IA de LanLabs. Tu rol es ayudar a los clientes de LanLabs a entender nuestros servicios y planes.

PLANES DISPONIBLES:
- Plan Básico: $149/mes - Para emprendedores y pequeños negocios
- Plan Profesional: $249/mes - Para empresas en crecimiento
- Plan Enterprise: $399/mes - Solución personalizada con soporte dedicado

Cuando alguien pregunte sobre precios o planes, siempre menciona los tres planes disponibles. Sé amable, profesional y siempre disponible para ayudar.',
    0.7,
    4000,
    '{"ventas": true, "agendamiento": true, "cobros": true, "links_pago": true, "calificacion": true, "campanas": false, "alertas": true, "seguimientos": true, "documentos": true}'::jsonb,
    NOW(),
    NOW()
);

-- Ejecuta SOLO si el query anterior (3) retorna vacío


-- ============================================================================
-- 5. Si el registro existe pero el system_prompt es NULL, actualiza
-- ============================================================================

UPDATE agentes
SET
    system_prompt = 'Eres Sofía, asistente IA de LanLabs...',
    updated_at = NOW()
WHERE cliente_id = 'd21c2725-7e2d-442b-8207-958fd4bcb038'
  AND (system_prompt IS NULL OR system_prompt = '');


-- ============================================================================
-- 6. Verifica el mapeo INVERSO (de cliente a phone_number_id)
-- ============================================================================

SELECT
    cc.cliente_id,
    cc.phone_number_id,
    c.nombre as cliente_nombre,
    cc.canal
FROM canales_config cc
LEFT JOIN clientes c ON cc.cliente_id = c.id
WHERE cc.canal = 'whatsapp'
LIMIT 10;

-- Esperado: Ver Sofía con su phone_number_id correspondiente


-- ============================================================================
-- 7. Debugging: ¿Qué phone_number_ids existen?
-- ============================================================================

SELECT DISTINCT
    phone_number_id,
    COUNT(*) as count
FROM canales_config
WHERE canal = 'whatsapp'
GROUP BY phone_number_id
ORDER BY count DESC;

-- Esto te ayuda a entender qué phone_number_ids están registrados
