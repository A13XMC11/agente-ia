import { NextResponse } from 'next/server'
import { getServerSession } from '@/lib/server-auth'

export async function GET() {
  try {
    const session = await getServerSession()
    if (!session?.cliente_id) {
      return NextResponse.json({ success: false, error: 'No autorizado' }, { status: 401 })
    }

    const bankInfo = {
      banco: process.env.LANLABS_BANCO ?? '',
      tipo_cuenta: process.env.LANLABS_TIPO_CUENTA ?? '',
      numero_cuenta: process.env.LANLABS_NUMERO_CUENTA ?? '',
      titular: process.env.LANLABS_TITULAR ?? '',
      ruc: process.env.LANLABS_RUC ?? '',
      cash_address: process.env.LANLABS_CASH_ADDRESS ?? '',
    }

    return NextResponse.json({ success: true, data: bankInfo })
  } catch (err) {
    console.error('[BILLING INSTRUCTIONS] Unexpected error:', err)
    return NextResponse.json({ success: false, error: 'Error interno' }, { status: 500 })
  }
}
