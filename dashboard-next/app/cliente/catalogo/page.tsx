'use client'

import { useState, useEffect, useRef } from 'react'
import {
  ShoppingBag, Plus, Pencil, Trash2, Upload, RefreshCw,
  Package, AlertTriangle, DollarSign, ToggleLeft, ToggleRight,
  Link, Webhook, FolderOpen, Check, X, Info,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

// ── Types ─────────────────────────────────────────────────────────────────────

interface Product {
  id: string
  sku: string | null
  nombre: string
  descripcion: string | null
  precio: number
  moneda: string
  categoria: string | null
  stock: number | null
  imagen_url: string | null
  activo: boolean
  created_at: string
  updated_at: string
}

interface SyncConfig {
  tipo: 'manual' | 'sheets' | 'webhook'
  sheets_url: string | null
  webhook_url: string | null
  sync_interval_minutes: number
  ultimo_sync: string | null
  activo: boolean
}

type Tab = 'productos' | 'importar' | 'sincronizacion'

const EMPTY_FORM = {
  nombre: '', descripcion: '', precio: '', stock: '',
  moneda: 'USD', categoria: '', sku: '', imagen_url: '',
}

// ── Sub-components ────────────────────────────────────────────────────────────

function StatCard({ icon: Icon, label, value, sub }: {
  icon: React.ElementType; label: string; value: string | number; sub?: string
}) {
  return (
    <div className="rounded-xl border border-border bg-card-bg px-4 py-3.5 flex items-center gap-3">
      <div className="h-8 w-8 rounded-lg bg-surface flex items-center justify-center shrink-0">
        <Icon className="h-4 w-4 text-text-muted" />
      </div>
      <div>
        <p className="text-xs text-text-muted">{label}</p>
        <p className="text-lg font-bold text-text-primary tabular-nums leading-tight">{value}</p>
        {sub && <p className="text-xs text-text-muted">{sub}</p>}
      </div>
    </div>
  )
}

function StockBadge({ stock }: { stock: number | null }) {
  if (stock === null) {
    return <span className="text-xs text-text-muted">Ilimitado</span>
  }
  const cls = stock === 0
    ? 'bg-error/10 text-error border-error/20'
    : stock <= 5
      ? 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20'
      : 'bg-success/10 text-success border-success/20'
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium border ${cls}`}>
      {stock === 0 ? 'Sin stock' : stock}
    </span>
  )
}

function ProductModal({
  product, onSave, onClose, saving,
}: {
  product?: Product | null
  onSave: (data: typeof EMPTY_FORM) => void
  onClose: () => void
  saving: boolean
}) {
  const [form, setForm] = useState(
    product
      ? {
          nombre: product.nombre,
          descripcion: product.descripcion || '',
          precio: String(product.precio),
          stock: product.stock !== null ? String(product.stock) : '',
          moneda: product.moneda,
          categoria: product.categoria || '',
          sku: product.sku || '',
          imagen_url: product.imagen_url || '',
        }
      : { ...EMPTY_FORM }
  )

  const set = (k: keyof typeof EMPTY_FORM) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
    setForm(prev => ({ ...prev, [k]: e.target.value }))

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-lg rounded-2xl border border-border bg-card-bg shadow-2xl">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <h2 className="text-base font-semibold text-text-primary">
            {product ? 'Editar producto' : 'Nuevo producto'}
          </h2>
          <button onClick={onClose} className="text-text-muted hover:text-text-primary transition-colors">
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="px-6 py-4 space-y-4 max-h-[70vh] overflow-y-auto">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="col-span-2">
              <label className="block text-xs text-text-muted mb-1">Nombre *</label>
              <Input value={form.nombre} onChange={set('nombre')} placeholder="Ej: Plan Profesional" />
            </div>
            <div>
              <label className="block text-xs text-text-muted mb-1">Precio *</label>
              <Input type="number" min="0" step="0.01" value={form.precio} onChange={set('precio')} placeholder="0.00" />
            </div>
            <div>
              <label className="block text-xs text-text-muted mb-1">Moneda</label>
              <select
                value={form.moneda}
                onChange={set('moneda')}
                className="w-full h-9 rounded-md border border-border bg-surface px-3 text-sm text-text-primary"
              >
                {['USD', 'EUR', 'MXN', 'COP', 'PEN', 'ARS', 'CLP'].map(c => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-text-muted mb-1">SKU / Código</label>
              <Input value={form.sku} onChange={set('sku')} placeholder="Opcional" />
            </div>
            <div>
              <label className="block text-xs text-text-muted mb-1">Stock</label>
              <Input type="number" min="0" value={form.stock} onChange={set('stock')} placeholder="Dejar vacío = ilimitado" />
            </div>
            <div>
              <label className="block text-xs text-text-muted mb-1">Categoría</label>
              <Input value={form.categoria} onChange={set('categoria')} placeholder="Ej: Servicios" />
            </div>
            <div>
              <label className="block text-xs text-text-muted mb-1">URL de imagen</label>
              <Input value={form.imagen_url} onChange={set('imagen_url')} placeholder="https://..." />
            </div>
            <div className="col-span-2">
              <label className="block text-xs text-text-muted mb-1">Descripción</label>
              <textarea
                value={form.descripcion}
                onChange={set('descripcion')}
                rows={2}
                placeholder="Descripción breve del producto o servicio"
                className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-text-primary placeholder:text-text-muted resize-none focus:outline-none focus:ring-1 focus:ring-accent"
              />
            </div>
          </div>
        </div>
        <div className="flex justify-end gap-2 px-6 py-4 border-t border-border">
          <Button variant="outline" onClick={onClose} disabled={saving}>Cancelar</Button>
          <Button onClick={() => onSave(form)} disabled={saving || !form.nombre.trim() || !form.precio}>
            {saving ? 'Guardando…' : product ? 'Guardar cambios' : 'Crear producto'}
          </Button>
        </div>
      </div>
    </div>
  )
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function CatalogoPage() {
  const [tab, setTab] = useState<Tab>('productos')
  const [products, setProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState<string | null>(null)

  // Modal state
  const [showModal, setShowModal] = useState(false)
  const [editingProduct, setEditingProduct] = useState<Product | null>(null)
  const [saving, setSaving] = useState(false)

  // Import state
  const fileRef = useRef<HTMLInputElement>(null)
  const [importFile, setImportFile] = useState<File | null>(null)
  const [importing, setImporting] = useState(false)
  const [importResult, setImportResult] = useState<{ created: number; updated: number; total_rows: number } | null>(null)
  const [importError, setImportError] = useState('')

  // Sync config state
  const [syncConfig, setSyncConfig] = useState<SyncConfig>({
    tipo: 'manual', sheets_url: '', webhook_url: '',
    sync_interval_minutes: 60, ultimo_sync: null, activo: true,
  })
  const [syncLoading, setSyncLoading] = useState(true)
  const [syncSaving, setSyncSaving] = useState(false)
  const [syncSaved, setSyncSaved] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [syncResult, setSyncResult] = useState<{ created: number; updated: number; total_rows: number } | null>(null)
  const [syncError, setSyncError] = useState('')

  // ── Data fetching ──────────────────────────────────────────────────────────

  const fetchProducts = async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/cliente/catalogo')
      const json = await res.json()
      if (json.success) setProducts(json.data)
    } finally {
      setLoading(false)
    }
  }

  const fetchSyncConfig = async () => {
    setSyncLoading(true)
    try {
      const res = await fetch('/api/cliente/catalogo/sync-config')
      const json = await res.json()
      if (json.success && json.data) {
        setSyncConfig({
          tipo: json.data.tipo || 'manual',
          sheets_url: json.data.sheets_url || '',
          webhook_url: json.data.webhook_url || '',
          sync_interval_minutes: json.data.sync_interval_minutes || 60,
          ultimo_sync: json.data.ultimo_sync || null,
          activo: json.data.activo ?? true,
        })
      }
    } finally {
      setSyncLoading(false)
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchProducts()
    fetchSyncConfig()
  }, [])

  // ── Product actions ────────────────────────────────────────────────────────

  const handleSave = async (form: typeof EMPTY_FORM) => {
    setSaving(true)
    try {
      const body = {
        nombre: form.nombre.trim(),
        descripcion: form.descripcion.trim() || null,
        precio: Number(form.precio),
        stock: form.stock !== '' ? Number(form.stock) : null,
        moneda: form.moneda,
        categoria: form.categoria.trim() || null,
        sku: form.sku.trim() || null,
        imagen_url: form.imagen_url.trim() || null,
      }
      const url = editingProduct
        ? `/api/cliente/catalogo/${editingProduct.id}`
        : '/api/cliente/catalogo'
      const res = await fetch(url, {
        method: editingProduct ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const json = await res.json()
      if (!json.success) throw new Error(json.error)
      await fetchProducts()
      setShowModal(false)
      setEditingProduct(null)
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Error al guardar')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (id: string, nombre: string) => {
    if (!confirm(`¿Eliminar "${nombre}"? Esta acción no se puede deshacer.`)) return
    setActionLoading(id)
    try {
      await fetch(`/api/cliente/catalogo/${id}`, { method: 'DELETE' })
      setProducts(prev => prev.filter(p => p.id !== id))
    } finally {
      setActionLoading(null)
    }
  }

  const handleToggleActivo = async (product: Product) => {
    setActionLoading(product.id)
    try {
      const res = await fetch(`/api/cliente/catalogo/${product.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ activo: !product.activo }),
      })
      const json = await res.json()
      if (json.success) {
        setProducts(prev => prev.map(p => p.id === product.id ? { ...p, activo: !p.activo } : p))
      }
    } finally {
      setActionLoading(null)
    }
  }

  // ── Import actions ─────────────────────────────────────────────────────────

  const handleImport = async () => {
    if (!importFile) return
    setImporting(true)
    setImportError('')
    setImportResult(null)
    try {
      const fd = new FormData()
      fd.append('file', importFile)
      const res = await fetch('/api/cliente/catalogo/import', { method: 'POST', body: fd })
      const json = await res.json()
      if (!json.success) throw new Error(json.error)
      setImportResult({ created: json.created, updated: json.updated, total_rows: json.total_rows })
      setImportFile(null)
      if (fileRef.current) fileRef.current.value = ''
      await fetchProducts()
    } catch (e) {
      setImportError(e instanceof Error ? e.message : 'Error al importar')
    } finally {
      setImporting(false)
    }
  }

  // ── Sync config actions ────────────────────────────────────────────────────

  const handleSaveSync = async () => {
    setSyncSaving(true)
    setSyncSaved(false)
    try {
      const res = await fetch('/api/cliente/catalogo/sync-config', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(syncConfig),
      })
      const json = await res.json()
      if (!json.success) throw new Error(json.error)
      setSyncSaved(true)
      setTimeout(() => setSyncSaved(false), 2500)
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Error al guardar')
    } finally {
      setSyncSaving(false)
    }
  }

  const handleSyncNow = async () => {
    setSyncing(true)
    setSyncResult(null)
    setSyncError('')
    try {
      const res = await fetch('/api/cliente/catalogo/sync-config', { method: 'POST' })
      const json = await res.json()
      if (!json.success) throw new Error(json.error)
      setSyncResult({ created: json.created, updated: json.updated, total_rows: json.total_rows })
      await fetchProducts()
    } catch (e) {
      setSyncError(e instanceof Error ? e.message : 'Error al sincronizar')
    } finally {
      setSyncing(false)
    }
  }

  // ── Derived stats ──────────────────────────────────────────────────────────

  const activos = products.filter(p => p.activo).length
  const sinStock = products.filter(p => p.stock !== null && p.stock === 0).length
  const valorTotal = products.reduce((s, p) => s + p.precio, 0)

  const formatPrice = (p: number, moneda: string) =>
    new Intl.NumberFormat('es-EC', { style: 'currency', currency: moneda, minimumFractionDigits: 2 }).format(p)

  const formatDate = (iso: string | null) =>
    iso ? new Date(iso).toLocaleString('es-EC', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }) : '—'

  const TABS: { id: Tab; label: string }[] = [
    { id: 'productos', label: 'Productos' },
    { id: 'importar', label: 'Importar' },
    { id: 'sincronizacion', label: 'Sincronización' },
  ]

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-xl bg-accent/10 flex items-center justify-center">
            <ShoppingBag className="h-5 w-5 text-accent" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-text-primary">Catálogo</h1>
            <p className="text-xs text-text-muted">Productos y servicios que tu agente puede vender</p>
          </div>
        </div>
        {tab === 'productos' && (
          <Button
            onClick={() => { setEditingProduct(null); setShowModal(true) }}
            className="gap-1.5"
          >
            <Plus className="h-4 w-4" />
            Nuevo producto
          </Button>
        )}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 gap-3 min-[430px]:grid-cols-2 md:grid-cols-4">
        <StatCard icon={Package} label="Total productos" value={products.length} />
        <StatCard icon={ToggleRight} label="Activos" value={activos} />
        <StatCard icon={AlertTriangle} label="Sin stock" value={sinStock} sub="stock = 0" />
        <StatCard icon={DollarSign} label="Precio promedio" value={products.length ? formatPrice(valorTotal / products.length, 'USD') : '—'} />
      </div>

      {/* Tabs */}
      <div className="border-b border-border">
        <div className="flex gap-1">
          {TABS.map(t => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={[
                'px-4 py-2.5 text-sm font-medium border-b-2 transition-colors',
                tab === t.id
                  ? 'border-accent text-accent'
                  : 'border-transparent text-text-muted hover:text-text-primary',
              ].join(' ')}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* ── Tab: Productos ── */}
      {tab === 'productos' && (
        <div className="rounded-xl border border-border bg-card-bg overflow-hidden">
          {loading ? (
            <div className="py-16 text-center text-text-muted text-sm">Cargando catálogo…</div>
          ) : products.length === 0 ? (
            <div className="py-16 text-center">
              <ShoppingBag className="h-10 w-10 text-text-muted mx-auto mb-3 opacity-40" />
              <p className="text-text-muted text-sm">Sin productos todavía</p>
              <p className="text-text-muted text-xs mt-1">Agrega productos manualmente o impórtalos desde CSV</p>
            </div>
          ) : (
            <div className="overflow-x-auto overscroll-x-contain">
            <table className="min-w-[720px] w-full text-sm">
              <thead>
                <tr className="border-b border-border text-text-muted text-xs">
                  <th className="text-left px-4 py-3 font-medium">Producto</th>
                  <th className="text-left px-4 py-3 font-medium hidden md:table-cell">Categoría</th>
                  <th className="text-right px-4 py-3 font-medium">Precio</th>
                  <th className="text-center px-4 py-3 font-medium hidden sm:table-cell">Stock</th>
                  <th className="text-center px-4 py-3 font-medium">Activo</th>
                  <th className="text-right px-4 py-3 font-medium">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {products.map(p => (
                  <tr key={p.id} className={['border-b border-border last:border-0 transition-colors', !p.activo && 'opacity-50'].join(' ')}>
                    <td className="px-4 py-3">
                      <div className="font-medium text-text-primary">{p.nombre}</div>
                      {p.sku && <div className="text-xs text-text-muted">SKU: {p.sku}</div>}
                      {p.descripcion && <div className="text-xs text-text-muted truncate max-w-xs">{p.descripcion}</div>}
                    </td>
                    <td className="px-4 py-3 hidden md:table-cell">
                      {p.categoria
                        ? <span className="inline-flex px-2 py-0.5 rounded-md text-xs bg-surface text-text-muted border border-border">{p.categoria}</span>
                        : <span className="text-text-muted">—</span>
                      }
                    </td>
                    <td className="px-4 py-3 text-right font-medium tabular-nums text-text-primary">
                      {formatPrice(p.precio, p.moneda)}
                    </td>
                    <td className="px-4 py-3 text-center hidden sm:table-cell">
                      <StockBadge stock={p.stock} />
                    </td>
                    <td className="px-4 py-3 text-center">
                      <button
                        onClick={() => handleToggleActivo(p)}
                        disabled={actionLoading === p.id}
                        className="transition-colors"
                        title={p.activo ? 'Desactivar' : 'Activar'}
                      >
                        {p.activo
                          ? <ToggleRight className="h-5 w-5 text-success mx-auto" />
                          : <ToggleLeft className="h-5 w-5 text-text-muted mx-auto" />
                        }
                      </button>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          onClick={() => { setEditingProduct(p); setShowModal(true) }}
                          disabled={actionLoading === p.id}
                          className="p-1.5 rounded-lg hover:bg-surface text-text-muted hover:text-text-primary transition-colors"
                          title="Editar"
                        >
                          <Pencil className="h-3.5 w-3.5" />
                        </button>
                        <button
                          onClick={() => handleDelete(p.id, p.nombre)}
                          disabled={actionLoading === p.id}
                          className="p-1.5 rounded-lg hover:bg-error/10 text-text-muted hover:text-error transition-colors"
                          title="Eliminar"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            </div>
          )}
        </div>
      )}

      {/* ── Tab: Importar ── */}
      {tab === 'importar' && (
        <div className="space-y-4">
          {/* Drop zone */}
          <div
            onClick={() => fileRef.current?.click()}
            className={[
              'rounded-xl border-2 border-dashed p-10 text-center cursor-pointer transition-colors',
              importFile ? 'border-accent bg-accent/5' : 'border-border hover:border-accent/50 bg-card-bg',
            ].join(' ')}
          >
            <Upload className={`h-8 w-8 mx-auto mb-3 ${importFile ? 'text-accent' : 'text-text-muted'}`} />
            {importFile ? (
              <div>
                <p className="text-sm font-medium text-text-primary">{importFile.name}</p>
                <p className="text-xs text-text-muted mt-1">{(importFile.size / 1024).toFixed(1)} KB</p>
              </div>
            ) : (
              <div>
                <p className="text-sm font-medium text-text-primary">Haz clic para seleccionar un archivo CSV</p>
                <p className="text-xs text-text-muted mt-1">o arrastra y suelta aquí</p>
              </div>
            )}
            <input
              ref={fileRef}
              type="file"
              accept=".csv"
              className="hidden"
              onChange={e => {
                setImportFile(e.target.files?.[0] || null)
                setImportResult(null)
                setImportError('')
              }}
            />
          </div>

          {/* Actions */}
          <div className="flex items-center gap-3">
            <Button
              onClick={handleImport}
              disabled={!importFile || importing}
              className="gap-2"
            >
              <Upload className="h-4 w-4" />
              {importing ? 'Importando…' : 'Importar productos'}
            </Button>
            {importFile && (
              <button
                onClick={() => { setImportFile(null); setImportResult(null); setImportError('') }}
                className="text-xs text-text-muted hover:text-text-primary transition-colors"
              >
                Cancelar
              </button>
            )}
          </div>

          {/* Result */}
          {importResult && (
            <div className="rounded-xl border border-success/30 bg-success/5 p-4 flex items-start gap-3">
              <Check className="h-4 w-4 text-success mt-0.5 shrink-0" />
              <div>
                <p className="text-sm font-medium text-text-primary">Importación completada</p>
                <p className="text-xs text-text-muted mt-0.5">
                  {importResult.total_rows} filas procesadas · {importResult.created} creados · {importResult.updated} actualizados
                </p>
              </div>
            </div>
          )}
          {importError && (
            <div className="rounded-xl border border-error/30 bg-error/5 p-4 flex items-start gap-3">
              <AlertTriangle className="h-4 w-4 text-error mt-0.5 shrink-0" />
              <p className="text-sm text-error">{importError}</p>
            </div>
          )}

          {/* Format guide */}
          <div className="rounded-xl border border-border bg-card-bg p-5 space-y-3">
            <div className="flex items-center gap-2 text-sm font-medium text-text-primary">
              <Info className="h-4 w-4 text-accent" />
              Formato del archivo CSV
            </div>
            <p className="text-xs text-text-muted">
              La primera fila debe contener los encabezados. Columnas aceptadas:
            </p>
            <div className="overflow-x-auto">
              <table className="text-xs w-full">
                <thead>
                  <tr className="text-text-muted border-b border-border">
                    <th className="text-left py-1.5 pr-4 font-medium">Columna</th>
                    <th className="text-left py-1.5 pr-4 font-medium">Alias aceptados</th>
                    <th className="text-left py-1.5 font-medium">Requerido</th>
                  </tr>
                </thead>
                <tbody className="text-text-primary">
                  {[
                    ['nombre', 'name, producto', 'Sí'],
                    ['precio', 'price, costo', 'Sí'],
                    ['descripcion', 'description', 'No'],
                    ['stock', 'cantidad, inventory', 'No'],
                    ['sku', 'codigo, code, ref', 'No'],
                    ['categoria', 'category', 'No'],
                    ['moneda', 'currency', 'No (default: USD)'],
                  ].map(([col, alias, req]) => (
                    <tr key={col} className="border-b border-border/50 last:border-0">
                      <td className="py-1.5 pr-4 font-mono text-accent">{col}</td>
                      <td className="py-1.5 pr-4 text-text-muted">{alias}</td>
                      <td className={`py-1.5 ${req === 'Sí' ? 'text-error' : 'text-text-muted'}`}>{req}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="rounded-lg bg-surface p-3 font-mono text-xs text-text-muted">
              nombre,precio,descripcion,stock,sku,categoria<br />
              Plan Básico,149,Agente IA con 500 mensajes,,,Servicios<br />
              Plan Profesional,249,Agente IA con 2000 mensajes,,,Servicios
            </div>
          </div>
        </div>
      )}

      {/* ── Tab: Sincronización ── */}
      {tab === 'sincronizacion' && (
        <div className="space-y-4 max-w-xl">
          {syncLoading ? (
            <div className="py-12 text-center text-text-muted text-sm">Cargando configuración…</div>
          ) : (
            <>
              {/* Tipo selector */}
              <div>
                <label className="block text-sm font-medium text-text-primary mb-3">Fuente del catálogo</label>
                <div className="grid grid-cols-3 gap-2">
                  {([
                    { id: 'manual', label: 'Manual', icon: FolderOpen, desc: 'Gestionar desde el dashboard' },
                    { id: 'sheets', label: 'Google Sheets', icon: Link, desc: 'Hoja de cálculo pública' },
                    { id: 'webhook', label: 'API externa', icon: Webhook, desc: 'Tu propio sistema' },
                  ] as const).map(opt => (
                    <button
                      key={opt.id}
                      onClick={() => setSyncConfig(prev => ({ ...prev, tipo: opt.id }))}
                      className={[
                        'rounded-xl border p-3 text-left transition-colors',
                        syncConfig.tipo === opt.id
                          ? 'border-accent bg-accent/10 text-accent'
                          : 'border-border bg-card-bg text-text-muted hover:border-accent/40',
                      ].join(' ')}
                    >
                      <opt.icon className="h-5 w-5 mb-2" />
                      <div className="text-xs font-medium text-text-primary">{opt.label}</div>
                      <div className="text-xs mt-0.5 opacity-70">{opt.desc}</div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Google Sheets config */}
              {syncConfig.tipo === 'sheets' && (
                <div className="space-y-3 rounded-xl border border-border bg-card-bg p-4">
                  <div>
                    <label className="block text-xs text-text-muted mb-1">URL de Google Sheets</label>
                    <Input
                      value={syncConfig.sheets_url || ''}
                      onChange={e => setSyncConfig(prev => ({ ...prev, sheets_url: e.target.value }))}
                      placeholder="https://docs.google.com/spreadsheets/d/e/2PACX-.../pub?output=csv"
                    />
                    {syncConfig.sheets_url && !/\/spreadsheets\/d\/[a-zA-Z0-9_-]{20,}/.test(syncConfig.sheets_url) && (
                      <div className="mt-1.5 rounded-lg bg-error/10 border border-error/20 px-3 py-2 flex items-start gap-2">
                        <AlertTriangle className="h-3.5 w-3.5 text-error mt-0.5 shrink-0" />
                        <p className="text-xs text-error">
                          URL inválida. La URL debe tener el formato:<br />
                          <code className="font-mono">https://docs.google.com/spreadsheets/d/e/2PACX-.../pub?output=csv</code>
                        </p>
                      </div>
                    )}
                    <p className="text-xs text-text-muted mt-1.5">
                      La hoja debe estar <strong className="text-text-primary">publicada en la web</strong>:
                      en Google Sheets ve a <em>Archivo → Compartir → Publicar en la web</em>, elige la pestaña, formato <strong className="text-text-primary">CSV</strong> y haz clic en Publicar.
                      Copia la URL completa que empieza con <code className="bg-surface px-1 rounded font-mono">...d/e/2PACX-...</code>
                    </p>
                  </div>
                  <div>
                    <label className="block text-xs text-text-muted mb-1">Sincronizar cada</label>
                    <div className="flex items-center gap-2">
                      <select
                        value={syncConfig.sync_interval_minutes}
                        onChange={e => setSyncConfig(prev => ({ ...prev, sync_interval_minutes: Number(e.target.value) }))}
                        className="h-9 rounded-md border border-border bg-surface px-3 text-sm text-text-primary"
                      >
                        {[30, 60, 120, 360, 720, 1440].map(m => (
                          <option key={m} value={m}>
                            {m < 60 ? `${m} minutos` : m < 1440 ? `${m / 60} hora${m / 60 > 1 ? 's' : ''}` : '1 día'}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                  {syncConfig.ultimo_sync && (
                    <p className="text-xs text-text-muted flex items-center gap-1.5">
                      <RefreshCw className="h-3 w-3" />
                      Última sincronización: {formatDate(syncConfig.ultimo_sync)}
                    </p>
                  )}
                </div>
              )}

              {/* Webhook config */}
              {syncConfig.tipo === 'webhook' && (
                <div className="space-y-3 rounded-xl border border-border bg-card-bg p-4">
                  <div>
                    <label className="block text-xs text-text-muted mb-1">URL del endpoint</label>
                    <Input
                      value={syncConfig.webhook_url || ''}
                      onChange={e => setSyncConfig(prev => ({ ...prev, webhook_url: e.target.value }))}
                      placeholder="https://mi-sistema.com/api/productos"
                    />
                    <p className="text-xs text-text-muted mt-1.5">
                      El endpoint debe devolver un array JSON o un objeto con clave <code className="bg-surface px-1 rounded">products</code>, <code className="bg-surface px-1 rounded">data</code> o <code className="bg-surface px-1 rounded">items</code>.
                    </p>
                  </div>
                  <div>
                    <label className="block text-xs text-text-muted mb-1">Sincronizar cada</label>
                    <select
                      value={syncConfig.sync_interval_minutes}
                      onChange={e => setSyncConfig(prev => ({ ...prev, sync_interval_minutes: Number(e.target.value) }))}
                      className="h-9 rounded-md border border-border bg-surface px-3 text-sm text-text-primary"
                    >
                      {[30, 60, 120, 360, 720, 1440].map(m => (
                        <option key={m} value={m}>
                          {m < 60 ? `${m} minutos` : m < 1440 ? `${m / 60} hora${m / 60 > 1 ? 's' : ''}` : '1 día'}
                        </option>
                      ))}
                    </select>
                  </div>
                  {syncConfig.ultimo_sync && (
                    <p className="text-xs text-text-muted flex items-center gap-1.5">
                      <RefreshCw className="h-3 w-3" />
                      Última sincronización: {formatDate(syncConfig.ultimo_sync)}
                    </p>
                  )}
                </div>
              )}

              {/* Manual info */}
              {syncConfig.tipo === 'manual' && (
                <div className="rounded-xl border border-border bg-card-bg p-4 flex items-start gap-3">
                  <Info className="h-4 w-4 text-accent mt-0.5 shrink-0" />
                  <div className="text-xs text-text-muted space-y-1">
                    <p className="text-text-primary font-medium">Gestión manual activa</p>
                    <p>Los productos se administran directamente desde la pestaña <strong>Productos</strong> o mediante importaciones CSV desde la pestaña <strong>Importar</strong>.</p>
                    <p>No hay sincronización automática.</p>
                  </div>
                </div>
              )}

              <div className="flex items-center gap-3 flex-wrap">
                <Button
                  onClick={handleSaveSync}
                  disabled={syncSaving}
                  className="gap-2"
                >
                  {syncSaved
                    ? <><Check className="h-4 w-4" />Guardado</>
                    : syncSaving
                      ? 'Guardando…'
                      : 'Guardar configuración'
                  }
                </Button>

                {syncConfig.tipo !== 'manual' && (
                  <Button
                    variant="outline"
                    onClick={handleSyncNow}
                    disabled={syncing || syncSaving}
                    className="gap-2"
                  >
                    <RefreshCw className={`h-4 w-4 ${syncing ? 'animate-spin' : ''}`} />
                    {syncing ? 'Sincronizando…' : 'Sincronizar ahora'}
                  </Button>
                )}
              </div>

              {syncResult && (
                <div className="rounded-xl border border-success/30 bg-success/5 p-4 flex items-start gap-3">
                  <Check className="h-4 w-4 text-success mt-0.5 shrink-0" />
                  <div>
                    <p className="text-sm font-medium text-text-primary">Sincronización completada</p>
                    <p className="text-xs text-text-muted mt-0.5">
                      {syncResult.total_rows} filas procesadas · {syncResult.created} creados · {syncResult.updated} actualizados
                    </p>
                  </div>
                </div>
              )}
              {syncError && (
                <div className="rounded-xl border border-error/30 bg-error/5 p-4 flex items-start gap-3">
                  <AlertTriangle className="h-4 w-4 text-error mt-0.5 shrink-0" />
                  <p className="text-sm text-error">{syncError}</p>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* Product modal */}
      {showModal && (
        <ProductModal
          product={editingProduct}
          onSave={handleSave}
          onClose={() => { setShowModal(false); setEditingProduct(null) }}
          saving={saving}
        />
      )}
    </div>
  )
}
