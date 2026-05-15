# Diagnóstico: Webhook WhatsApp no recibe mensajes del número real

## Status Actual

✅ **Base de datos**: Configuración correcta
- Tabla: `canales_config`
- Registro encontrado
- Phone Number ID: **1108311609031850** (correcto en Supabase)
- Cliente ID: `d21c2725-7e2d-442b-8207-958fd4bcb038`

## Cómo funciona la identificación del cliente

### 1. **Webhook llega** → canales/whatsapp.py:161
```python
phone_number_id = value.get("metadata", {}).get("phone_number_id")
```
Lee el `phone_number_id` del webhook de Meta

### 2. **Busca cliente** → core/router.py:200-208
```python
response = self.supabase.table("canales_config").select(
    "cliente_id"
).eq("canal", "whatsapp").eq(
    "phone_number_id", identifier
).single().execute()
```
Busca en Supabase el cliente con ese phone_number_id

### 3. **Resultado**
- Si encuentra coincidencia → procesa el mensaje
- Si NO encuentra → ignora el mensaje (log: "Could not identify client")

## Problema Identificado

El webhook probablemente está llegando con un `phone_number_id` **diferente** al registrado en Supabase.

### Posibles razones:
1. **Meta tiene dos phone_number_id para el mismo número**
   - Número de prueba: funciona ✓
   - Número real: different ID, no funciona ✗

2. **Configuración en Meta Cloud API incompleta**
   - El webhook no está vinculado correctamente al número real

3. **Webhook apunta a múltiples números**
   - Meta envía webhooks de múltiples números al mismo endpoint
   - Necesitas actualizar Supabase con el nuevo phone_number_id

## Próximos pasos

### 1. **Ver los logs de debug** (ejecutados)
Reinicia la aplicación con los nuevos logs:
```bash
docker-compose down
docker-compose up -d
```

### 2. **Envía un mensaje del número real** (+593 99 267 2980)
Monitorea los logs:
```bash
docker-compose logs -f fastapi
```

Busca estas líneas:
```
📱 DEBUG: Webhook received with phone_number_id = ???
🔍 [IDENTIFY] Searching for phone_number_id = ???
```

### 3. **Comparar valores**
```
- Si ves: ❌ [IDENTIFY] NO MATCH
  → El phone_number_id que Meta envía es diferente al de Supabase
  
- Si ves: ✅ [IDENTIFY] Found client_id = ...
  → El problema está en otro lado (memory, normalization, etc)
```

### 4. **Actualizar si es necesario**
Si el phone_number_id es diferente, tienes dos opciones:

**Opción A**: Actualizar Supabase con el nuevo phone_number_id
```bash
curl -X PATCH "https://incfxatkrinbecprbrnf.supabase.co/rest/v1/canales_config?id=eq.ad956023-e486-4966-9c30-6ebd683ec396" \
  -H "apikey: [YOUR_KEY]" \
  -H "Content-Type: application/json" \
  -d '{"phone_number_id": "1108311609031850"}'
```

**Opción B**: Registrar AMBOS phone_number_id en Supabase
```sql
-- Agregar una segunda fila para el mismo cliente con el otro ID
INSERT INTO canales_config (cliente_id, canal, phone_number_id, token, waba_id)
VALUES ('d21c2725-7e2d-442b-8207-958fd4bcb038', 'whatsapp', 'NUEVO_ID', 'TOKEN', 'WABA_ID');
```

## Información del cliente

| Campo | Valor |
|-------|-------|
| **Cliente ID** | `d21c2725-7e2d-442b-8207-958fd4bcb038` |
| **Canal** | whatsapp |
| **Phone Number ID (actual)** | `1108311609031850` |
| **Número de prueba** | ✓ (funciona) |
| **Número real** | +593 99 267 2980 ❌ (no funciona) |

## Logs agregados

### En `canales/whatsapp.py` (línea 159+):
- `📱 DEBUG: Webhook received with phone_number_id = XXX`
- `✅ DEBUG: Client identified = XXX` ✓
- `❌ DEBUG: No client found in DB for phone_number_id = XXX` ❌

### En `core/router.py` (línea 200+):
- `🔍 [IDENTIFY] Searching for phone_number_id = XXX`
- `✅ [IDENTIFY] Found client_id = XXX` ✓
- `❌ [IDENTIFY] NO MATCH in canales_config for phone_number_id = XXX` ❌

## Meta Cloud API Settings

Verifica en https://developers.facebook.com/apps:

1. **Business Account → Phone Numbers**
   - Número de prueba: phone_number_id = ? (funciona)
   - Número real: phone_number_id = ? (no funciona)

2. **Webhook Configuration**
   - URL: `https://[tu-dominio]/webhook/whatsapp`
   - Verify Token: configurado en .env

3. **Permissions**
   - whatsapp_business_messaging
   - whatsapp_business_account_management
