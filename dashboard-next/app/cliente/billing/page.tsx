import { CreditCard, CheckCircle, AlertTriangle, XCircle, Clock, HelpCircle } from 'lucide-react'
import { getServerSession } from '@/lib/server-auth'
import { supabase } from '@/lib/supabase/server'
import { redirect } from 'next/navigation'

/* ── Types ─────────────────────────────────────────── */
type SubscriptionStatus = 'active' | 'past_due' | 'cancelled' | 'trialing'

interface Subscription {
  id: string
  cliente_id: string
  stripe_subscription_id: string
  stripe_customer_id: string
  monthly_amount: number
  status: SubscriptionStatus
  current_period_start: string
  current_period_end: string
  next_billing_date: string
  last_payment_date: string | null
  payment_failed_count: number
  cancelled_date: string | null
  created_at: string
}

/* ── Status config ─────────────────────────────────── */
const STATUS_CONFIG: Record<SubscriptionStatus, {
  label: string
  description: string
  icon: React.ElementType
  iconColor: string
  badgeCls: string
}> = {
  active: {
    label: 'Activo',
    description: 'Tu suscripción está al día. El agente funciona con normalidad.',
    icon: CheckCircle,
    iconColor: 'text-success',
    badgeCls: 'bg-success/10 text-success border border-success/20',
  },
  past_due: {
    label: 'Pago pendiente',
    description: 'No pudimos procesar tu último pago. Por favor actualiza tu método de pago.',
    icon: AlertTriangle,
    iconColor: 'text-warning',
    badgeCls: 'bg-warning/10 text-warning border border-warning/20',
  },
  cancelled: {
    label: 'Cancelado',
    description: 'Tu suscripción ha sido cancelada. Contacta al soporte para reactivarla.',
    icon: XCircle,
    iconColor: 'text-error',
    badgeCls: 'bg-error/10 text-error border border-error/20',
  },
  trialing: {
    label: 'Período de prueba',
    description: 'Estás en período de prueba. Tu primer cobro ocurrirá al finalizar.',
    icon: Clock,
    iconColor: 'text-accent',
    badgeCls: 'bg-accent/10 text-accent border border-accent/20',
  },
}

/* ── Helpers ───────────────────────────────────────── */
function formatDate(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('es', { year: 'numeric', month: 'long', day: 'numeric' })
}

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount)
}

/* ── Data fetching ─────────────────────────────────── */
async function getSubscription(clienteId: string): Promise<Subscription | null> {
  const { data, error } = await supabase
    .from('subscription')
    .select('*')
    .eq('cliente_id', clienteId)
    .maybeSingle()

  if (error) {
    console.error('[BILLING] Error fetching subscription:', error)
    return null
  }
  return data
}

/* ── Info row ──────────────────────────────────────── */
function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between py-3 border-b border-border last:border-0">
      <span className="text-sm text-text-secondary">{label}</span>
      <span className="text-sm font-medium text-text-primary">{value}</span>
    </div>
  )
}

/* ── No subscription state ─────────────────────────── */
function NoSubscription() {
  return (
    <div className="rounded-xl border border-border bg-card-bg p-10 flex flex-col items-center text-center">
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-surface mb-4">
        <HelpCircle className="h-7 w-7 text-text-muted" />
      </div>
      <h2 className="text-lg font-semibold text-text-primary">Sin suscripción activa</h2>
      <p className="text-text-secondary text-sm mt-2 max-w-sm">
        Aún no tienes un plan configurado. Contacta a tu administrador para activar tu suscripción.
      </p>
      <a
        href="mailto:soporte@lanlabsec.com"
        className="mt-6 inline-flex items-center gap-2 rounded-lg bg-accent/10 text-accent border border-accent/20 px-4 py-2 text-sm font-medium hover:bg-accent/15 transition-colors"
      >
        Contactar soporte
      </a>
    </div>
  )
}

/* ── Page ──────────────────────────────────────────── */
export default async function BillingPage() {
  const session = await getServerSession()
  if (!session?.cliente_id) redirect('/login')

  const subscription = await getSubscription(session.cliente_id)

  const statusCfg = subscription
    ? STATUS_CONFIG[subscription.status] ?? STATUS_CONFIG.active
    : null

  const daysUntilBilling = subscription?.next_billing_date
    ? Math.max(0, Math.ceil((new Date(subscription.next_billing_date).getTime() - Date.now()) / 86_400_000))
    : null

  return (
    <div className="space-y-8 max-w-2xl">
      {/* Header */}
      <div className="stagger-1">
        <div className="flex items-center gap-3">
          <CreditCard className="h-6 w-6 text-accent" />
          <h1 className="text-3xl md:text-4xl font-bold text-text-primary tracking-tight">Facturación</h1>
        </div>
        <p className="text-text-secondary mt-1.5 text-sm">
          Estado de tu suscripción y próximos cobros
        </p>
      </div>

      {!subscription ? (
        <NoSubscription />
      ) : (
        <>
          {/* Status banner */}
          <div className="stagger-2 rounded-xl border border-border bg-card-bg p-6">
            <div className="flex items-start gap-4">
              <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-card-bg border border-border`}>
                {statusCfg && <statusCfg.icon className={`h-5 w-5 ${statusCfg.iconColor}`} />}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-3 flex-wrap">
                  <h2 className="text-base font-semibold text-text-primary">Estado de suscripción</h2>
                  {statusCfg && (
                    <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold ${statusCfg.badgeCls}`}>
                      {statusCfg.label}
                    </span>
                  )}
                </div>
                <p className="text-text-secondary text-sm mt-1">{statusCfg?.description}</p>

                {/* Past-due warning */}
                {subscription.status === 'past_due' && subscription.payment_failed_count > 0 && (
                  <div className="mt-3 flex items-center gap-2 text-xs text-warning">
                    <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
                    <span>
                      {subscription.payment_failed_count} intento{subscription.payment_failed_count > 1 ? 's' : ''} fallido{subscription.payment_failed_count > 1 ? 's' : ''}.
                      {subscription.payment_failed_count >= 3 ? ' Tu agente ha sido pausado.' : ` Tu agente se pausará al llegar a 3.`}
                    </span>
                  </div>
                )}
              </div>

              {/* Monthly amount */}
              <div className="shrink-0 text-right">
                <p className="text-2xl font-bold text-text-primary">
                  {formatCurrency(subscription.monthly_amount)}
                </p>
                <p className="text-xs text-text-muted">por mes</p>
              </div>
            </div>
          </div>

          {/* Billing details */}
          <div className="stagger-3 rounded-xl border border-border bg-card-bg p-6">
            <h2 className="text-sm font-semibold text-text-secondary uppercase tracking-wider mb-2">
              Detalles del plan
            </h2>
            <div className="mt-1">
              <InfoRow label="Período actual" value={`${formatDate(subscription.current_period_start)} — ${formatDate(subscription.current_period_end)}`} />
              <InfoRow
                label="Próximo cobro"
                value={
                  subscription.status === 'cancelled'
                    ? 'Sin cobros futuros'
                    : daysUntilBilling !== null
                    ? `${formatDate(subscription.next_billing_date)} (en ${daysUntilBilling} día${daysUntilBilling !== 1 ? 's' : ''})`
                    : formatDate(subscription.next_billing_date)
                }
              />
              <InfoRow label="Último pago" value={formatDate(subscription.last_payment_date)} />
              <InfoRow label="Suscripción creada" value={formatDate(subscription.created_at)} />
            </div>
          </div>

          {/* Support */}
          <div className="stagger-4 rounded-xl border border-border bg-card-bg p-5 flex items-center justify-between gap-4">
            <div>
              <p className="text-sm font-medium text-text-primary">¿Problemas con tu facturación?</p>
              <p className="text-xs text-text-muted mt-0.5">Contacta a soporte y te ayudamos de inmediato.</p>
            </div>
            <a
              href="mailto:soporte@lanlabsec.com"
              className="shrink-0 inline-flex items-center gap-2 rounded-lg bg-accent/10 text-accent border border-accent/20 px-4 py-2 text-sm font-medium hover:bg-accent/15 transition-colors"
            >
              Contactar soporte
            </a>
          </div>
        </>
      )}
    </div>
  )
}
