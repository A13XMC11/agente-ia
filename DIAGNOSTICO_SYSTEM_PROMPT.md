# 🔍 Diagnóstico: System Prompt de Sofía

He agregado logs exhaustivos en **3 puntos críticos**:

## 1. **Router - Identificación del Cliente** (router.py)

```
🔍 [IDENTIFY] Searching for phone_number_id in canales_config:
   phone_number_id: '...'

🔍 [IDENTIFY] Query response:
   Found record: [keys...]
✅ [IDENTIFY] Resolved phone_number_id=... → client_id=...
```

**¿Qué buscar?**
- El `client_id` debe ser: `d21c2725-7e2d-442b-8207-958fd4bcb038`
- Si es diferente → **el problema está en canales_config**
- Si retorna vacío → **no existe el mapping**

---

## 2. **Router - Carga de Configuración** (router.py)

```
🔍 [ROUTER CONFIG QUERY] Starting to fetch agentes config
   client_id being queried: 'd21c2725...'

🔍 [ROUTER CONFIG RESPONSE] Query returned:
   Number of records: 1
   Available keys in first record: ['id', 'cliente_id', 'system_prompt', ...]

🔍 [ROUTER CONFIG DATA] Raw data from agentes table:
   config['system_prompt'] = 'Eres Sofía, asistente IA de LanLabs...'

✅ Found 'system_prompt' in config (EN), length=5847

🔍 [ROUTER MERGED CONFIG] Final config after merge:
   system_prompt source: DB (agentes)
   system_prompt length: 7892
   system_prompt first 150 chars: 'Eres Sofía, asistente...'
```

**¿Qué buscar?**
- `Number of records: 1` → encontró el registro
- `✅ Found 'system_prompt' in config` → extrajo correctamente
- `system_prompt source: DB (agentes)` → está usando la DB, no el default
- Si ves `DEFAULT fallback` → **el query no encontró nada**

---

## 3. **Agent - Inyección en GPT-4o** (agent.py)

```
🔍 [AGENT INIT] AgentEngine constructor called:
   client_id: 'd21c2725...'
   system_prompt from client_config (before rules):
      Length: 7892
      First 200 chars: 'Eres Sofía, asistente...'

🔍 [AGENT PROCESS_MESSAGE] Building messages for GPT-4o:
   client_id: 'd21c2725...'
   system_prompt length: 8000
   system_prompt first 300 chars: 'Eres Sofía, asistente IA de LanLabs...'
```

**¿Qué buscar?**
- El system_prompt debe empezar con "Eres Sofía"
- La longitud debe ser ~7900+ (porque se agregan reglas adicionales)
- Si ves "You are a helpful business assistant" → **está usando el DEFAULT**

---

## 📊 Flujo Esperado (Paso a Paso)

1. **WhatsApp recibe mensaje** → webhook con `phone_number_id`
2. **[IDENTIFY]** → busca en canales_config → obtiene `d21c2725...`
3. **[ROUTER CONFIG QUERY]** → busca en agentes tabla → obtiene system_prompt
4. **[ROUTER CONFIG RESPONSE]** → verifica que encontró 1 registro
5. **[ROUTER MERGED CONFIG]** → system_prompt viene de DB
6. **[AGENT INIT]** → AgentEngine recibe system_prompt correcto
7. **[AGENT PROCESS_MESSAGE]** → inyecta en messages[0].content
8. **[GPT-4o]** → responde como Sofía con planes $149/$249/$399

---

## 🚨 Escenarios de Fallo

### Escenario A: client_id incorrecto
```
❌ [IDENTIFY] NO MATCH in canales_config
   Checking all records in canales_config for debugging...
   Total records: 5
```
**Solución:** Revisar tabla `canales_config` - ¿existe un registro para Sofía?

### Escenario B: agentes tabla vacía para Sofía
```
🔍 [ROUTER CONFIG RESPONSE] Query returned:
   Number of records: 0
```
**Solución:** Insertar en tabla `agentes` para `d21c2725...`

### Escenario C: system_prompt es NULL en BD
```
✅ Found 'system_prompt' in config (EN), length=0
```
**Solución:** Actualizar registro en `agentes` con el prompt personalizado

### Escenario D: Caching antiguo
```
Checking if already cached... True
```
El agente está en caché. Reinicia la aplicación o:
```python
router.invalidate_agent_cache("d21c2725-7e2d-442b-8207-958fd4bcb038")
```

---

## 📝 Pasos para Diagnosticar

1. **Envía un mensaje a Sofía por WhatsApp**
2. **Abre los logs/stdout** en terminal
3. **Busca estos patrones:**
   - `🔍 [IDENTIFY]` → verifica el client_id
   - `🔍 [ROUTER CONFIG RESPONSE]` → verifica si encontró registro
   - `✅ Found 'system_prompt'` → verifica que lo extrajo
   - `system_prompt source:` → verifica si es DB o DEFAULT
4. **Nota en qué paso falla**
5. **Reporta exactamente lo que ves en los logs**

---

## 🔄 Cómo Invalidar Cache (si necesitas)

```python
# En main.py o en una ruta de admin
message_router.invalidate_agent_cache("d21c2725-7e2d-442b-8207-958fd4bcb038")
print("Cache invalidated for Sofía")
```

O simplemente **reinicia el servidor FastAPI**.

---

## 📋 Checklist Final

- [ ] El client_id de Sofía en canales_config es: `d21c2725-7e2d-442b-8207-958fd4bcb038`
- [ ] Existe un registro en tabla `agentes` con ese client_id
- [ ] El `system_prompt` en ese registro NO es NULL/vacío
- [ ] El `system_prompt` menciona "Sofía" y "$149, $249, $399"
- [ ] Los logs muestran `system_prompt source: DB (agentes)`
- [ ] Los logs muestran que empieza con "Eres Sofía"
