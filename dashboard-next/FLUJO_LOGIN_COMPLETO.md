# Flujo Completo de Login - Análisis y Solución

## Problema Original

El usuario existía en Supabase Auth pero al hacer login:
- ✗ No redirigía a ningún lado
- ✗ No mostraba error
- ✗ No se consultaba la tabla `usuarios` para obtener el rol
- ✗ El rol se seteaba hardcodeado como 'admin' sin validación

## Cambios Implementados

### 1. Endpoint `/api/auth/login/route.ts` - Mejorado

#### Antes (❌ Incompleto)
```typescript
// Solo autenticaba contra Supabase Auth
// No consultaba tabla usuarios
// Retornaba solo access_token sin información del usuario
cookieStore.set('user-role', 'admin', {...})  // ❌ Hardcodeado
```

#### Después (✅ Completo)

**6 pasos principales:**

1. **Validar entrada** - Email y password requeridos
2. **Autenticar con Supabase Auth** - Obtiene access_token
3. **Consultar tabla `usuarios`** - Busca usuario por email
4. **Si no existe:**
   - Crea nuevo usuario
   - Asigna role = `super_admin` si email = `SUPER_ADMIN_EMAIL` del env
   - Si no, asigna `admin` por defecto
5. **Setear cookies** - auth-token (httpOnly) + user-role
6. **Retornar usuario con rol** - Client puede redirigir según role

### 2. Página `/app/login/page.tsx` - Mejorada

#### Antes (❌ Sin logs ni redirección inteligente)
```typescript
router.push('/admin')  // ❌ Igual para todos los roles
router.refresh()
```

#### Después (✅ Con logs y redirección basada en rol)
```typescript
// Ahora redirige según rol del usuario
const redirectPath = 
  data.user?.role === 'super_admin' ? '/admin' 
  : data.user?.role === 'admin' ? '/admin'
  : '/dashboard'

router.push(redirectPath)
```

## Flujo Completo de Login (Con logs)

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Usuario abre /login y completa formulario                │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. page.tsx → POST /api/auth/login                          │
│ [LOGIN PAGE] Submitting login for: user@example.com         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. route.ts → Step 1: Validar credenciales                  │
│ [AUTH/LOGIN] Email: user@example.com                        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. route.ts → Step 2: Supabase Auth                         │
│ [AUTH/LOGIN] Calling Supabase Auth endpoint                 │
│ [AUTH/LOGIN] Supabase Auth response status: 200 ✓           │
│ [AUTH/LOGIN] Auth successful, user ID: xxxxx               │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. route.ts → Step 3: Consultar tabla usuarios              │
│ [AUTH/LOGIN] Usuarios table query status: 200               │
│                                                             │
│ ¿Usuario existe? ────────┬─────────────────┐               │
│                          │                 │               │
│                    ✓ SÍ  │            ✗ NO │               │
│                          │                 │               │
│                    Usar  │           Crear │               │
│                    rol   │         usuario │               │
│                    actual│      con rol    │               │
│                          │       'admin'   │               │
│                          │  o 'super_admin'│               │
│                          │   si email =    │               │
│                          │   SUPER_ADMIN_  │               │
│                          │   EMAIL         │               │
│                          ▼                 ▼               │
│                    [AUTH/LOGIN] User found in DB - Role: admin
│                    [AUTH/LOGIN] User created successfully
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. route.ts → Step 5: Setear cookies + Retornar usuario     │
│ [AUTH/LOGIN] Setting auth cookie                            │
│ [AUTH/LOGIN] Cookie: auth-token (httpOnly)                  │
│ [AUTH/LOGIN] Cookie: user-role = 'admin'                   │
│ [AUTH/LOGIN] Login successful                              │
│                                                             │
│ Response:                                                   │
│ {                                                           │
│   "success": true,                                         │
│   "access_token": "eyJ...",                                │
│   "user": {                                                │
│     "id": "xxxxx",                                         │
│     "email": "user@example.com",                           │
│     "role": "admin",                                       │
│     "created_at": "2025-05-07T..."                         │
│   }                                                         │
│ }                                                           │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 7. page.tsx → Recibir respuesta                             │
│ [LOGIN PAGE] Response status: 200                           │
│ [LOGIN PAGE] Login successful, user role: admin             │
│ [LOGIN PAGE] Redirecting to: /admin                         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 8. router.push('/admin') + router.refresh()                 │
│ ✓ Usuario redirigido al dashboard                           │
└─────────────────────────────────────────────────────────────┘
```

## Logs Esperados en la Consola del Navegador

```
[LOGIN PAGE] Submitting login for: demo@example.com
[LOGIN PAGE] Response status: 200
[LOGIN PAGE] Response data: {
  success: true,
  hasUser: true,
  userRole: "admin",
  error: undefined
}
[LOGIN PAGE] Login successful, user role: admin
[LOGIN PAGE] Redirecting to: /admin
```

## Logs Esperados en el Servidor (Next.js Console)

```
[AUTH/LOGIN] Step 1: Environment check
  NEXT_PUBLIC_SUPABASE_URL: ✓
  NEXT_PUBLIC_SUPABASE_ANON_KEY: ✓
  SUPABASE_SERVICE_ROLE_KEY: ✓
  JWT_SECRET: ✓
  SUPER_ADMIN_EMAIL: admin@example.com
[AUTH/LOGIN] Email: demo@example.com

[AUTH/LOGIN] Step 2: Authenticating with Supabase Auth
[AUTH/LOGIN] Supabase Auth response status: 200
[AUTH/LOGIN] Auth successful, user ID: a1b2c3d4-e5f6-...
[AUTH/LOGIN] Access token expires in: 3600 seconds

[AUTH/LOGIN] Step 3: Checking usuarios table
[AUTH/LOGIN] Usuarios table query status: 200
[AUTH/LOGIN] Found 1 usuario(s) with email: demo@example.com
[AUTH/LOGIN] User found in DB - Role: admin

[AUTH/LOGIN] Step 5: Setting auth cookie
[AUTH/LOGIN] Step 6: Login successful
[AUTH/LOGIN] User: {
  id: 'a1b2c3d4-e5f6-...',
  email: 'demo@example.com',
  role: 'admin'
}
```

## Requisitos de Configuración

### Variables de Entorno Necesarias en `.env.local`

```env
# Existentes
NEXT_PUBLIC_SUPABASE_URL=https://...supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...
JWT_SECRET=...

# NUEVO: Necesario para consultar tabla usuarios
SUPABASE_SERVICE_ROLE_KEY=eyJ...  # ⚠️ CRÍTICO

# NUEVO: Para asignar super_admin automáticamente
SUPER_ADMIN_EMAIL=admin@example.com
```

### Tabla Supabase `usuarios` - Estructura Requerida

```sql
CREATE TABLE usuarios (
  id UUID PRIMARY KEY,
  email VARCHAR(255) NOT NULL UNIQUE,
  role VARCHAR(50) NOT NULL DEFAULT 'admin',
  cliente_id UUID,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- RLS Policy (Row Level Security)
ALTER TABLE usuarios ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role can manage all usuarios"
ON usuarios
FOR ALL
USING (true)
WITH CHECK (true)
TO service_role;
```

## Checklist de Verificación

- [ ] `.env.local` contiene `SUPABASE_SERVICE_ROLE_KEY`
- [ ] `.env.local` contiene `SUPER_ADMIN_EMAIL` (opcional pero recomendado)
- [ ] Tabla `usuarios` existe en Supabase
- [ ] Tabla `usuarios` tiene estructura correcta (id, email, role, created_at)
- [ ] RLS está habilitado en tabla `usuarios`
- [ ] Service role tiene acceso para leer/escribir en `usuarios`
- [ ] Usuario demo existe en Supabase Auth
- [ ] Usuario demo tiene un registro en tabla `usuarios` (o será creado al primer login)

## Prueba de Login

1. Abre http://localhost:3000/login
2. Ingresa:
   - Email: `demo@example.com`
   - Password: `password123`
3. Abre DevTools (F12) → Console
4. Deberías ver logs `[LOGIN PAGE]...` y redirección a `/admin`
5. Si hay error, revisa logs en servidor (terminal donde corre Next.js)

## Posibles Errores y Soluciones

### Error: "Server configuration error" 
**Causa:** Falta `SUPABASE_SERVICE_ROLE_KEY`
**Solución:** Agrega `SUPABASE_SERVICE_ROLE_KEY` a `.env.local`

### Error: "Configuration error - missing Supabase credentials"
**Causa:** Falta `NEXT_PUBLIC_SUPABASE_URL` o `NEXT_PUBLIC_SUPABASE_ANON_KEY`
**Solución:** Verifica variables en `.env.local`

### Login exitoso pero no redirige
**Causa:** 
1. `usuarios` table no existe
2. `user` object vacío en respuesta
**Solución:** 
1. Crea tabla `usuarios` en Supabase
2. Revisa logs en servidor: `[AUTH/LOGIN] User:...`

### Usuario creado con rol incorrecto
**Causa:** `SUPER_ADMIN_EMAIL` no coincide con email del usuario
**Solución:** Actualiza `SUPER_ADMIN_EMAIL` o actualiza rol manualmente en BD

## Diagrama de Roles y Redirección

```
┌─────────────────────────────────────────┐
│ Login exitoso con usuario en DB         │
└────────────────┬────────────────────────┘
                 │
        ┌────────┴────────┬───────────┐
        │                 │           │
   role='super_admin' role='admin'  role='operador'
        │                 │           │
        ▼                 ▼           ▼
      /admin            /admin      /dashboard
      (full access)   (full access) (limited)
```

Actualmente, `super_admin` y `admin` redirigen a `/admin`. Si quieres diferenciar:

```typescript
const redirectPath = 
  data.user?.role === 'super_admin' ? '/admin/super' 
  : data.user?.role === 'admin' ? '/admin'
  : '/dashboard'
```
