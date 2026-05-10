import { createClient } from '@supabase/supabase-js'
import * as fs from 'fs'
import * as path from 'path'
import { createHash } from 'crypto'

// Load .env.local
const envPath = path.join(process.cwd(), '.env.local')
if (fs.existsSync(envPath)) {
  const envContent = fs.readFileSync(envPath, 'utf-8')
  envContent.split('\n').forEach(line => {
    const [key, value] = line.split('=')
    if (key && value) {
      process.env[key.trim()] = value.trim()
    }
  })
}

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || ''
const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY || ''

if (!supabaseUrl || !supabaseServiceKey) {
  console.error('❌ Error: NEXT_PUBLIC_SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY deben estar configuradas')
  process.exit(1)
}

const supabase = createClient(supabaseUrl, supabaseServiceKey, {
  auth: {
    autoRefreshToken: false,
    persistSession: false
  }
})

async function createTestUser() {
  try {
    console.log('🔍 Buscando cliente existente...')

    // Obtener un cliente existente
    const { data: clientes, error: clientesError } = await supabase
      .from('clientes')
      .select('id, nombre')
      .eq('estado', 'activo')
      .limit(1)

    if (clientesError || !clientes || clientes.length === 0) {
      console.error('❌ No hay clientes activos en la base de datos')
      console.log('📝 Crea un cliente primero en el admin panel')
      process.exit(1)
    }

    const cliente = clientes[0]
    console.log(`✅ Cliente encontrado: ${cliente.nombre} (ID: ${cliente.id})`)

    const testEmail = 'cliente@test.com'
    const testPassword = 'password123'

    console.log(`\n🔐 Creando usuario en Supabase Auth...`)
    console.log(`   Email: ${testEmail}`)
    console.log(`   Contraseña: ${testPassword}`)

    // Crear usuario en Supabase Auth
    let authUserId = null

    try {
      const { data: authUser, error: authError } = await supabase.auth.admin.createUser({
        email: testEmail,
        password: testPassword,
        email_confirm: true
      })

      if (authError) {
        if (authError.message?.includes('already') || authError.code === 'email_exists') {
          console.log(`⚠️  Usuario ${testEmail} ya existe en Supabase Auth`)
          // Obtener el user ID del usuario existente
          const { data: existingUser } = await supabase.auth.admin.listUsers()
          const found = existingUser?.users?.find(u => u.email === testEmail)
          authUserId = found?.id
        } else {
          throw authError
        }
      } else {
        console.log(`✅ Usuario creado en Auth: ${authUser?.user?.id}`)
        authUserId = authUser?.user?.id
      }
    } catch (err: any) {
      if (err.code === 'email_exists' || err.message?.includes('already')) {
        console.log(`⚠️  Usuario ${testEmail} ya existe en Supabase Auth`)
      } else {
        throw err
      }
    }

    // Insertar en tabla usuarios
    console.log(`\n📝 Insertando en tabla usuarios...`)

    // Obtener el user_id de Supabase Auth
    const { data: allUsers } = await supabase.auth.admin.listUsers()
    const supabaseUser = allUsers?.users?.find(u => u.email === testEmail)

    if (!supabaseUser?.id) {
      console.error('❌ No se pudo encontrar el user_id de Supabase Auth')
      process.exit(1)
    }

    // Hash de la contraseña (simple SHA256 para propósitos de ejemplo)
    const passwordHash = createHash('sha256').update(testPassword).digest('hex')

    const { data: usuario, error: userError } = await supabase
      .from('usuarios')
      .insert({
        id: supabaseUser.id,
        email: testEmail,
        password_hash: passwordHash,
        rol: 'cliente',
        cliente_id: cliente.id
      })
      .select()
      .single()

    if (userError) {
      if (userError.message?.includes('duplicate') || userError.code === '23505') {
        console.log(`⚠️  Usuario ${testEmail} ya existe en la tabla`)
      } else {
        console.error('❌ Error inserting user:', userError)
        process.exit(1)
      }
    }

    console.log(`✅ Usuario insertado en tabla usuarios`)

    console.log(`
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✨ Usuario cliente de prueba creado exitosamente
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📧 Email:     ${testEmail}
🔑 Contraseña: ${testPassword}
👤 Rol:       cliente
🏢 Cliente:   ${cliente.nombre}

🌐 Accede a: http://localhost:3000/login

Credenciales de login:
  Email:     ${testEmail}
  Contraseña: ${testPassword}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    `)

  } catch (error) {
    console.error('❌ Error:', error)
    process.exit(1)
  }
}

createTestUser()
