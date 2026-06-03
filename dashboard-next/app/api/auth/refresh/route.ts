import { NextResponse } from 'next/server'

// Clerk manages token refresh automatically — this endpoint is a no-op kept for backwards compatibility.
export async function POST(): Promise<NextResponse> {
  return NextResponse.json({ success: true, refreshed: false })
}
