import { NextResponse } from 'next/server'
import { getServerSession } from '@/lib/server-auth'
import { supabase } from '@/lib/supabase/server'
import { z } from 'zod'

interface SignalEvent {
  id: string
  score_before: number
  score_after: number
  delta: number
  signal_type: string
  signal_keywords: string[]
  message_excerpt: string
  created_at: string
}

interface ApiResponse<T> {
  success: boolean
  data?: T
  error?: string
}

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const session = await getServerSession()
    if (!session || !session.cliente_id) {
      return NextResponse.json(
        { success: false, error: 'Unauthorized' } as ApiResponse<never>,
        { status: 401 }
      )
    }

    const { id } = await params

    // Validate ID is a valid UUID
    const idSchema = z.string().uuid()
    const validatedId = idSchema.safeParse(id)
    if (!validatedId.success) {
      return NextResponse.json(
        { success: false, error: 'Invalid lead ID' } as ApiResponse<never>,
        { status: 400 }
      )
    }

    // Fetch score history for this lead
    const { data, error } = await supabase
      .from('lead_score_history')
      .select('id, score_before, score_after, delta, signal_type, signal_keywords, message_excerpt, created_at')
      .eq('lead_id', validatedId.data)
      .eq('cliente_id', session.cliente_id)
      .order('created_at', { ascending: false })
      .limit(50)

    if (error) {
      // Table might not exist yet
      if (error.code === '42703' || error.code === 'PGRST204') {
        return NextResponse.json({
          success: true,
          data: []
        } as ApiResponse<SignalEvent[]>)
      }
      throw error
    }

    return NextResponse.json({
      success: true,
      data: (data || []) as SignalEvent[]
    } as ApiResponse<SignalEvent[]>)
  } catch (error) {
    console.error('Error fetching lead signals:', error)
    return NextResponse.json(
      { success: false, error: 'Failed to fetch signals' } as ApiResponse<never>,
      { status: 500 }
    )
  }
}
