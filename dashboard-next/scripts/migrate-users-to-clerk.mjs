/**
 * Migrates all users from the `usuarios` table to Clerk.
 *
 * What it does:
 * 1. Reads every user from Supabase `usuarios` table
 * 2. Creates each one in Clerk (skip password — they must use "Forgot Password" to activate)
 * 3. Sets publicMetadata: { role, cliente_id, email }
 * 4. Sends a password-reset email so each user can set a new password and log in
 *
 * Run: node scripts/migrate-users-to-clerk.mjs
 *
 * Requires env vars (reads from .env.local automatically):
 *   CLERK_SECRET_KEY
 *   NEXT_PUBLIC_SUPABASE_URL
 *   SUPABASE_SERVICE_ROLE_KEY
 */

import { readFileSync } from 'fs'
import { resolve, dirname } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))

// ---------- Load .env.local ----------
function loadEnv() {
  const envPath = resolve(__dirname, '../.env.local')
  const env = {}
  try {
    const lines = readFileSync(envPath, 'utf8').split('\n')
    for (const line of lines) {
      const trimmed = line.trim()
      if (!trimmed || trimmed.startsWith('#')) continue
      const idx = trimmed.indexOf('=')
      if (idx === -1) continue
      const key = trimmed.slice(0, idx).trim()
      const value = trimmed.slice(idx + 1).trim().replace(/^["']|["']$/g, '')
      env[key] = value
    }
  } catch {
    console.error('Could not read .env.local')
    process.exit(1)
  }
  return env
}

const env = loadEnv()
const CLERK_SECRET_KEY = env.CLERK_SECRET_KEY
const SUPABASE_URL = env.NEXT_PUBLIC_SUPABASE_URL
const SUPABASE_SERVICE_KEY = env.SUPABASE_SERVICE_ROLE_KEY

if (!CLERK_SECRET_KEY || !SUPABASE_URL || !SUPABASE_SERVICE_KEY) {
  console.error('Missing required env vars')
  process.exit(1)
}

// ---------- Supabase fetch ----------
async function getSupabaseUsers() {
  const res = await fetch(`${SUPABASE_URL}/rest/v1/usuarios?select=id,email,rol,cliente_id`, {
    headers: {
      apikey: SUPABASE_SERVICE_KEY,
      Authorization: `Bearer ${SUPABASE_SERVICE_KEY}`,
    },
  })
  if (!res.ok) throw new Error(`Supabase error: ${res.status} ${await res.text()}`)
  return res.json()
}

// ---------- Clerk helpers ----------
async function clerkRequest(method, path, body) {
  const res = await fetch(`https://api.clerk.com/v1${path}`, {
    method,
    headers: {
      Authorization: `Bearer ${CLERK_SECRET_KEY}`,
      'Content-Type': 'application/json',
    },
    body: body ? JSON.stringify(body) : undefined,
  })
  const data = await res.json()
  if (!res.ok) {
    const msg = data?.errors?.[0]?.message ?? JSON.stringify(data)
    throw new Error(`Clerk ${method} ${path} → ${res.status}: ${msg}`)
  }
  return data
}

async function findClerkUserByEmail(email) {
  const data = await clerkRequest('GET', `/users?email_address=${encodeURIComponent(email)}`)
  const list = Array.isArray(data) ? data : data.data ?? []
  return list.find(u =>
    u.email_addresses?.some(e => e.email_address === email),
  ) ?? null
}

async function createClerkUser(email, metadata) {
  return clerkRequest('POST', '/users', {
    email_address: [email],
    skip_password_checks: true,
    skip_password_requirement: true,
    public_metadata: metadata,
  })
}

async function updateClerkMetadata(userId, metadata) {
  return clerkRequest('PATCH', `/users/${userId}/metadata`, {
    public_metadata: metadata,
  })
}

async function sendPasswordResetEmail(userId) {
  // Creates a reset-password token and sends an email
  return clerkRequest('POST', `/users/${userId}/send_reset_password_email`, {})
}

// ---------- Migration ----------
async function main() {
  console.log('=== Supabase → Clerk user migration ===\n')

  const supabaseUsers = await getSupabaseUsers()
  console.log(`Found ${supabaseUsers.length} user(s) in Supabase:\n`)
  for (const u of supabaseUsers) {
    console.log(`  ${u.email}  rol=${u.rol}  cliente_id=${u.cliente_id ?? 'null'}`)
  }
  console.log()

  for (const u of supabaseUsers) {
    const metadata = {
      role: u.rol,
      cliente_id: u.cliente_id ?? null,
      email: u.email,
    }

    let clerkUser = await findClerkUserByEmail(u.email)

    if (clerkUser) {
      console.log(`[SKIP] ${u.email} already exists in Clerk (${clerkUser.id}) — updating metadata`)
      await updateClerkMetadata(clerkUser.id, metadata)
      console.log(`  ✓ Metadata updated: ${JSON.stringify(metadata)}`)
    } else {
      console.log(`[CREATE] ${u.email}`)
      clerkUser = await createClerkUser(u.email, metadata)
      console.log(`  ✓ Created → Clerk ID: ${clerkUser.id}`)
      console.log(`  ✓ Metadata set: ${JSON.stringify(metadata)}`)

      // Send reset-password email so the user can activate their account
      try {
        await sendPasswordResetEmail(clerkUser.id)
        console.log(`  ✓ Password-reset email sent to ${u.email}`)
      } catch (e) {
        console.warn(`  ⚠ Could not send reset email: ${e.message}`)
        console.warn(`    They can use "Forgot Password" at /sign-in to activate.`)
      }
    }
    console.log()
  }

  console.log('=== Migration complete ===')
  console.log()
  console.log('Next steps:')
  console.log('  1. Users receive a "Reset your password" email from Clerk.')
  console.log('  2. They click the link, set a new password, and log in.')
  console.log('  3. On first login the /api/auth/sync route re-confirms their role from Supabase.')
  console.log('  4. Once all users have logged in via Clerk you can disable Supabase Auth.')
}

main().catch(e => {
  console.error('Fatal:', e.message)
  process.exit(1)
})
