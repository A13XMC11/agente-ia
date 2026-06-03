import { NextResponse } from 'next/server'

export async function POST(): Promise<NextResponse> {
  const response = NextResponse.json({ success: true })
  response.cookies.set('_role_synced', '', { maxAge: 0, path: '/' })
  return response
}
