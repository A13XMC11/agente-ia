import { jwtVerify } from 'jose'
import { cookies } from 'next/headers'
import type { User, LoginRequest, LoginResponse } from '@/types'

const secretKey = new TextEncoder().encode(
  process.env.JWT_SECRET || 'your-secret-key-change-this-in-production',
)

// Verify JWT token
export async function verifyJWT(token: string): Promise<User | null> {
  try {
    const verified = await jwtVerify(token, secretKey)
    return verified.payload as unknown as User
  } catch {
    return null
  }
}

// Get current session from cookies
export async function getSession(): Promise<User | null> {
  const cookieStore = await cookies()
  const token = cookieStore.get('auth-token')?.value

  if (!token) {
    return null
  }

  return verifyJWT(token)
}

// Login user - make request to Supabase auth
export async function loginUser(credentials: LoginRequest): Promise<LoginResponse> {
  try {
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_SUPABASE_URL}/auth/v1/token?grant_type=password`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          apikey: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || '',
        },
        body: JSON.stringify({
          email: credentials.email,
          password: credentials.password,
        }),
      },
    )

    if (!response.ok) {
      const error = await response.json()
      return {
        success: false,
        error: error.error_description || 'Login failed',
      }
    }

    const data = await response.json()

    // Verify JWT to extract user info
    const user = await verifyJWT(data.access_token)

    if (!user) {
      return {
        success: false,
        error: 'Invalid token',
      }
    }

    // Set cookie with token
    const cookieStore = await cookies()
    cookieStore.set('auth-token', data.access_token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'strict',
      maxAge: data.expires_in || 3600,
      path: '/',
    })

    return {
      success: true,
      access_token: data.access_token,
      user,
    }
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'An error occurred'
    return {
      success: false,
      error: message,
    }
  }
}

// Logout user - clear cookies
export async function logoutUser(): Promise<void> {
  const cookieStore = await cookies()
  cookieStore.delete('auth-token')
}

// Check if user is authenticated
export async function isAuthenticated(): Promise<boolean> {
  const session = await getSession()
  return session !== null
}

// Get user role
export async function getUserRole(): Promise<string | null> {
  const session = await getSession()
  return session?.role ?? null
}
