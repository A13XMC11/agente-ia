import { CreditCard, CheckCircle, AlertTriangle, XCircle, Clock, HelpCircle, Mail, Building2, MapPin } from 'lucide-react'
import { getServerSession } from '@/lib/server-auth'
import { createServerClient } from '@/lib/supabase/server'
import { redirect } from 'next/navigation'
import ProofUpload from './ProofUpload'

/* ── Types ─────────────────────────────────────────── */
type SubscriptionStatus =
  | 'active'
  | 'past_due'
  | 'cancelled'
  | 'trialing'
  | 'pending_payment'
  | 'proof_submitted'

type PaymentMethod = 'payphone' | 'transferencia' | 'efectivo'

interface Subscription {
  id: string
  cliente_id: string
  monthly_amount: number
  status: SubscriptionStatus
  payment_method: PaymentMethod | null
  current_period_start: string | null
  current_period_end: string | null
  next_billing_date: string | null
  last_payment_date: string | null
  payment_failed_count: number
  cancelled_date: string | null
  pending_proof_url: string | null
  created_at: string
}

interface SubscriptionPayment {
  id: string
  payment_method: PaymentMethod
  amount: number
  status: 'pending' | 'proof_submitted' | 'paid' | 'rejected'
  period_start: string | null
  period_end: string | null
  verified_at: string | null
  created_at: string
}

interface PlatformBankInfo {
  banco: string
  tipo_cuenta: string
  numero_cuenta: string
  titular: string
  ruc: string
  cash_address: string
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
    description: 'Hay un problema con tu último pago. Realiza el pago para reactivar tu agente.',
    icon: AlertTriangle,
    iconColor: 'text-warning',
    badgeCls: 'bg-warning/10 text-warning border border-warning/20',
  },
  pending_payment: {
    label: 'Esperando pago',
    description: 'Tu suscripción está lista. Completa el pago para activar tu agente.',
    icon: Clock,
    iconColor: 'text-accent',
    badgeCls: 'bg-accent/10 text-accent border border-accent/20',
  },
  proof_submitted: {
    label: 'Comprobante en revisión',
    description: 'Recibimos tu comprobante. El equipo de LanLabs lo revisará pronto.',
    icon: Clock,
    iconColor: 'text-accent',
    badgeCls: 'bg-accent/10 text-accent border border-accent/20',
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

const PAYMENT_STATUS_LABEL: Record<SubscriptionPayment['status'], string> = {
  pending: 'Pendiente',
  proof_submitted: 'En revisión',
  paid: 'Pagado',
  rejected: 'Rechazado',
}

const PAYMENT_STATUS_CLS: Record<SubscriptionPayment['status'], string> = {
  pending: 'bg-accent/10 text-accent border-accent/20',
  proof_submitted: 'bg-accent/10 text-accent border-accent/20',
  paid: 'bg-success/10 text-success border-success/20',
  rejected: 'bg-error/10 text-error border-error/20',
}

/* ── Helpers ───────────────────────────────────────── */
function formatDate(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('es', { year: 'numeric', month: 'long', day: 'numeric' })
}

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount)
}

function getPlatformBankInfo(): PlatformBankInfo {
  return {
    banco: process.env.LANLABS_BANCO ?? '',
    tipo_cuenta: process.env.LANLABS_TIPO_CUENTA ?? '',
    numero_cuenta: process.env.LANLABS_NUMERO_CUENTA ?? '',
    titular: process.env.LANLABS_TITULAR ?? '',
    ruc: process.env.LANLABS_RUC ?? '',
    cash_address: process.env.LANLABS_CASH_ADDRESS ?? '',
  }
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
        <Mail className="h-3.5 w-3.5" />
        Contactar soporte
      </a>
    </div>
  )
}

/* ── Bank transfer instructions ────────────────────── */
function TransferenciaInstructions({
  bank,
  amount,
  status,
}: {
  bank: PlatformBankInfo
  amount: number
  status: SubscriptionStatus
}) {
  const needsPayment = status === 'pending_payment' || status === 'past_due'
  const inReview = status === 'proof_submitted'

  return (
    <div className="stagger-4 rounded-xl border border-border bg-card-bg p-6 space-y-5">
      <div className="flex items-center gap-2">
        <Building2 className="h-4 w-4 text-accent" />
        <h3 className="text-sm font-semibold text-text-primary">Datos para transferencia</h3>
      </div>

      <div className="rounded-lg bg-surface border border-border divide-y divide-border">
        {bank.banco && <InfoRow label="Banco" value={bank.banco} />}
        {bank.tipo_cuenta && <InfoRow label="Tipo de cuenta" value={bank.tipo_cuenta} />}
        {bank.numero_cuenta && <InfoRow label="Número de cuenta" value={bank.numero_cuenta} />}
        {bank.titular && <InfoRow label="Titular" value={bank.titular} />}
        {bank.ruc && <InfoRow label="RUC / Cédula" value={bank.ruc} />}
        <InfoRow label="Monto a transferir" value={formatCurrency(amount)} />
      </div>

      {inReview ? (
        <div className="flex items-center gap-3 rounded-lg border border-accent/30 bg-accent/5 p-4">
          <Clock className="h-5 w-5 text-accent shrink-0" />
          <p className="text-sm text-text-secondary">
            Tu comprobante está siendo revisado. Te notificaremos cuando sea aprobado.
          </p>
        </div>
      ) : needsPayment ? (
        <div className="space-y-3">
          <p className="text-sm text-text-secondary">
            Realiza la transferencia por el monto exacto y sube el comprobante.
          </p>
          <ProofUpload />
        </div>
      ) : (
        <p className="text-sm text-text-muted">
          Tu suscripción está activa. Al próximo vencimiento deberás realizar una nueva transferencia.
        </p>
      )}
    </div>
  )
}

/* ── Cash instructions ─────────────────────────────── */
function EfectivoInstructions({ bank }: { bank: PlatformBankInfo }) {
  return (
    <div className="stagger-4 rounded-xl border border-border bg-card-bg p-6 space-y-4">
      <div className="flex items-center gap-2">
        <MapPin className="h-4 w-4 text-accent" />
        <h3 className="text-sm font-semibold text-text-primary">Pago en efectivo</h3>
      </div>
      <p className="text-sm text-text-secondary">
        Acércate a nuestras instalaciones para realizar el pago en efectivo.
      </p>
      {bank.cash_address && (
        <div className="rounded-lg bg-surface border border-border p-4">
          <p className="text-xs text-text-muted uppercase tracking-wide mb-1">Dirección</p>
          <p className="text-sm font-medium text-text-primary">{bank.cash_address}</p>
        </div>
      )}
      <p className="text-xs text-text-muted">
        Una vez recibido el pago, nuestro equipo activará o renovará tu suscripción.
      </p>
    </div>
  )
}

/* ── Payment history ───────────────────────────────── */
function PaymentHistory({ payments }: { payments: SubscriptionPayment[] }) {
  if (payments.length === 0) return null

  return (
    <div className="stagger-5 rounded-xl border border-border bg-card-bg p-6 space-y-4">
      <h3 className="text-sm font-semibold text-text-secondary uppercase tracking-wider">Historial de pagos</h3>
      <div className="space-y-2">
        {payments.map((p) => (
          <div key={p.id} className="flex items-center justify-between py-2.5 border-b border-border last:border-0">
            <div>
              <p className="text-sm font-medium text-text-primary">
                {formatCurrency(p.amount)}
                <span className="ml-2 text-xs text-text-muted capitalize">{p.payment_method}</span>
              </p>
              {p.period_start && p.period_end && (
                <p className="text-xs text-text-muted mt-0.5">
                  {formatDate(p.period_start)} — {formatDate(p.period_end)}
                </p>
              )}
            </div>
            <span className={`text-xs font-semibold px-2 py-0.5 rounded-full border ${PAYMENT_STATUS_CLS[p.status]}`}>
              {PAYMENT_STATUS_LABEL[p.status]}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

/* ── Page ──────────────────────────────────────────── */
export default async function BillingPage() {
  const session = await getServerSession()
  if (!session?.cliente_id) redirect('/login')

  const supabase = createServerClient()

  const { data: subscription } = await supabase
    .from('subscription')
    .select('*')
    .eq('cliente_id', session.cliente_id)
    .order('created_at', { ascending: false })
    .limit(1)
    .maybeSingle()

  let payments: SubscriptionPayment[] = []
  if (subscription?.id) {
    const { data: paymentsData } = await supabase
      .from('subscription_payments')
      .select('id, payment_method, amount, status, period_start, period_end, verified_at, created_at')
      .eq('subscription_id', subscription.id)
      .order('created_at', { ascending: false })
      .limit(12)
    payments = (paymentsData ?? []) as SubscriptionPayment[]
  }

  const statusCfg = subscription
    ? (STATUS_CONFIG[subscription.status as SubscriptionStatus] ?? STATUS_CONFIG.active)
    : null

  const daysUntilBilling = subscription?.next_billing_date
    ? Math.max(0, Math.ceil((new Date(subscription.next_billing_date).getTime() - Date.now()) / 86_400_000))
    : null

  const paymentMethod = (subscription?.payment_method ?? 'payphone') as PaymentMethod
  const bankInfo = getPlatformBankInfo()

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
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-card-bg border border-border">
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
              {subscription.current_period_start && subscription.current_period_end && (
                <InfoRow
                  label="Período actual"
                  value={`${formatDate(subscription.current_period_start)} — ${formatDate(subscription.current_period_end)}`}
                />
              )}
              <InfoRow
                label="Próximo cobro"
                value={
                  subscription.status === 'cancelled'
                    ? 'Sin cobros futuros'
                    : daysUntilBilling !== null && subscription.next_billing_date
                    ? `${formatDate(subscription.next_billing_date)} (en ${daysUntilBilling} día${daysUntilBilling !== 1 ? 's' : ''})`
                    : formatDate(subscription.next_billing_date)
                }
              />
              <InfoRow label="Último pago" value={formatDate(subscription.last_payment_date)} />
              <InfoRow label="Suscripción creada" value={formatDate(subscription.created_at)} />
            </div>
          </div>

          {/* Payment method — context-aware */}
          {paymentMethod === 'payphone' && (
            <div className="stagger-4 rounded-xl border border-border bg-card-bg p-5 flex items-center justify-between gap-4">
              <div>
                <p className="text-sm font-medium text-text-primary">Método de pago</p>
                <p className="text-xs text-text-muted mt-0.5">
                  Los cobros se realizan mediante Payphone. Si tienes problemas, contáctanos.
                </p>
              </div>
              <div className="shrink-0 text-xs font-semibold text-accent bg-accent/10 border border-accent/20 rounded-lg px-3 py-1.5">
                Payphone
              </div>
            </div>
          )}

          {paymentMethod === 'transferencia' && (
            <TransferenciaInstructions
              bank={bankInfo}
              amount={subscription.monthly_amount}
              status={subscription.status as SubscriptionStatus}
            />
          )}

          {paymentMethod === 'efectivo' && (
            <EfectivoInstructions bank={bankInfo} />
          )}

          {/* Payment history (manual methods) */}
          {paymentMethod !== 'payphone' && payments.length > 0 && (
            <PaymentHistory payments={payments} />
          )}

          {/* Support */}
          <div className="stagger-6 rounded-xl border border-border bg-card-bg p-5 flex items-center justify-between gap-4">
            <div>
              <p className="text-sm font-medium text-text-primary">¿Problemas con tu facturación?</p>
              <p className="text-xs text-text-muted mt-0.5">Contacta a soporte y te ayudamos de inmediato.</p>
            </div>
            <a
              href="mailto:soporte@lanlabsec.com"
              className="shrink-0 inline-flex items-center gap-2 rounded-lg bg-accent/10 text-accent border border-accent/20 px-4 py-2 text-sm font-medium hover:bg-accent/15 transition-colors"
            >
              <Mail className="h-3.5 w-3.5" />
              Contactar soporte
            </a>
          </div>
        </>
      )}
    </div>
  )
}
