import { NextRequest, NextResponse } from 'next/server'

// Clerk handles token invalidation client-side via <SignOutButton> or clerk.signOut().
// This endpoint exists only for backwards compatibility with any existing logout calls.
export async function POST(request: NextRequest): Promise<NextResponse> {
  return NextResponse.redirect(new URL('/sign-in', request.url), { status: 302 })
}
