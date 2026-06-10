'use client'

import { useState, useRef } from 'react'
import { Upload, CheckCircle, AlertTriangle, Loader2 } from 'lucide-react'

type UploadState = 'idle' | 'uploading' | 'submitted' | 'error'

interface ProofUploadProps {
  onSuccess?: () => void
}

export default function ProofUpload({ onSuccess }: ProofUploadProps) {
  const [state, setState] = useState<UploadState>('idle')
  const [errorMsg, setErrorMsg] = useState('')
  const [fileName, setFileName] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return

    setFileName(file.name)
    setState('uploading')
    setErrorMsg('')

    try {
      const formData = new FormData()
      formData.append('file', file)

      const res = await fetch('/api/cliente/billing/proof', {
        method: 'POST',
        body: formData,
      })

      const data = await res.json() as { success: boolean; error?: string }

      if (res.ok && data.success) {
        setState('submitted')
        onSuccess?.()
      } else {
        setState('error')
        setErrorMsg(data.error ?? 'Error al subir el archivo. Intenta nuevamente.')
      }
    } catch {
      setState('error')
      setErrorMsg('Error de red. Verifica tu conexión e intenta nuevamente.')
    }
  }

  if (state === 'submitted') {
    return (
      <div className="flex items-center gap-3 rounded-lg border border-success/30 bg-success/5 p-4">
        <CheckCircle className="h-5 w-5 text-success shrink-0" />
        <div>
          <p className="text-sm font-medium text-text-primary">Comprobante enviado</p>
          <p className="text-xs text-text-muted mt-0.5">
            Tu comprobante está siendo revisado por el equipo de LanLabs. Te notificaremos cuando sea aprobado.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp,image/gif,application/pdf"
        className="hidden"
        onChange={handleFileChange}
        disabled={state === 'uploading'}
      />

      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        disabled={state === 'uploading'}
        className="w-full flex items-center justify-center gap-2 rounded-lg border-2 border-dashed border-border hover:border-accent/40 bg-surface/50 hover:bg-accent/5 px-4 py-4 text-sm font-medium text-text-secondary hover:text-accent transition-all disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {state === 'uploading' ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            Subiendo {fileName}...
          </>
        ) : (
          <>
            <Upload className="h-4 w-4" />
            Subir comprobante de transferencia
          </>
        )}
      </button>

      {state === 'error' && (
        <div className="flex items-start gap-2 rounded-lg border border-error/30 bg-error/5 px-3 py-2.5">
          <AlertTriangle className="h-4 w-4 text-error shrink-0 mt-0.5" />
          <p className="text-xs text-error">{errorMsg}</p>
        </div>
      )}

      <p className="text-xs text-text-muted">
        Formatos aceptados: JPG, PNG, PDF · Máximo 5 MB
      </p>
    </div>
  )
}
