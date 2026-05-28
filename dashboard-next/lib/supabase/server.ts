import { createClient } from '@supabase/supabase-js'

function getEnvVars() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL
  const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY
  if (!url || !serviceKey) {
    throw new Error('Missing Supabase environment variables')
  }
  return { url, serviceKey }
}

export function createServerClient() {
  const { url, serviceKey } = getEnvVars()
  return createClient(url, serviceKey, {
    auth: {
      autoRefreshToken: false,
      persistSession: false,
    },
  })
}

// Backward-compatible singleton for routes that haven't been migrated
export const supabase = createServerClient()
