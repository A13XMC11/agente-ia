'use client'

import { CheckSquare, Square, Printer } from 'lucide-react'
import { useState } from 'react'

const CHECKLIST = [
  'Tengo una cuenta en Meta for Developers (developers.facebook.com)',
  'Creé una app de tipo Business en Meta Developers',
  'Agregué el producto WhatsApp a mi app',
  'Mi número de teléfono NO está activo en WhatsApp personal',
  'Agregué y verifiqué mi número en WhatsApp → Configuración de API',
  'Copié mi Phone Number ID',
  'Copié mi WABA ID (Identificador de cuenta)',
  'Creé un Usuario del sistema administrador en Meta Business Suite',
  'Asigné la app al usuario con permisos whatsapp_business_messaging',
  'Generé y guardé el token permanente en un lugar seguro',
]

const STEPS = [
  {
    number: 1,
    title: 'Abre Meta for Developers',
    detail: 'Ve a developers.facebook.com e inicia sesión con tu cuenta de Facebook Business.',
    url: 'developers.facebook.com',
  },
  {
    number: 2,
    title: 'Crea tu app de tipo Business',
    detail:
      'Haz click en "Mis Apps" → "Crear app". Selecciona el tipo "Business". Ponle el nombre de tu negocio.',
    screenshot: '[Captura: Pantalla de creación de app en Meta Developers]',
  },
  {
    number: 3,
    title: 'Agrega WhatsApp como producto',
    detail:
      'Dentro de tu app ve a "Agregar producto". Busca "WhatsApp" y haz click en "Configurar".',
    screenshot: '[Captura: Panel de productos en Meta Developers]',
  },
  {
    number: 4,
    title: 'Agrega y verifica tu número',
    detail:
      'Ve a WhatsApp → Configuración de API. Haz click en "Agregar número de teléfono". Sigue la verificación por SMS. IMPORTANTE: El número no debe estar en uso en WhatsApp personal.',
    screenshot: '[Captura: Configuración de API de WhatsApp]',
    warning: true,
    warningText: 'El número NO debe estar activo en WhatsApp personal ni WhatsApp Business convencional. Si lo está, primero elimínalo de esa cuenta.',
  },
  {
    number: 5,
    title: 'Copia tu Phone Number ID y WABA ID',
    detail:
      'Una vez agregado el número, verás en la pantalla el Phone Number ID y el WABA ID (Identificador de cuenta WhatsApp Business). Cópialos, los necesitarás en el formulario.',
    screenshot: '[Captura: Phone Number ID y WABA ID en la consola]',
  },
  {
    number: 6,
    title: 'Genera el token permanente',
    detail:
      'Ve a business.facebook.com → Configuración → Usuarios del sistema. Crea un "Usuario del sistema administrador". Asígnale tu app con permisos completos. Haz click en "Generar token" con permisos de whatsapp_business_messaging. Guarda el token en un lugar seguro: no podrás verlo de nuevo.',
    url: 'business.facebook.com',
    screenshot: '[Captura: Generación de token en Meta Business Suite]',
    warning: false,
  },
  {
    number: 7,
    title: 'Conéctate en el dashboard',
    detail:
      'Vuelve a tu dashboard → Configuración → WhatsApp. Ingresa el Phone Number ID, WABA ID y el token permanente. Haz click en "Verificar y conectar". ¡Listo!',
  },
]

export default function GuiaOnboardingPage() {
  const [checked, setChecked] = useState<Record<number, boolean>>({})

  function toggle(i: number) {
    setChecked((prev) => ({ ...prev, [i]: !prev[i] }))
  }

  return (
    <>
      <style>{`
        @media print {
          .no-print { display: none !important; }
          body { background: white !important; }
          .print-break { page-break-before: always; }
        }
      `}</style>

      <div className="min-h-screen bg-white text-gray-900 max-w-3xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="flex items-start justify-between mb-8">
          <div>
            <p className="text-sm text-gray-500 mb-1">LanLabs — Guía de activación</p>
            <h1 className="text-3xl font-bold text-gray-900">
              Conecta tu WhatsApp Business
            </h1>
            <p className="text-gray-600 mt-2">
              Sigue esta guía paso a paso para activar tu agente IA en WhatsApp.
              Tiempo estimado: 15–20 minutos.
            </p>
          </div>
          <button
            onClick={() => window.print()}
            className="no-print flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium hover:bg-gray-50 shrink-0 ml-4"
          >
            <Printer className="h-4 w-4" />
            Descargar PDF
          </button>
        </div>

        <hr className="border-gray-200 mb-8" />

        {/* Steps */}
        <section className="space-y-8 mb-12">
          <h2 className="text-xl font-semibold text-gray-800">Pasos de configuración</h2>

          {STEPS.map((step) => (
            <div key={step.number} className="flex gap-4">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gray-900 text-white text-sm font-bold">
                {step.number}
              </div>
              <div className="flex-1 space-y-2">
                <p className="font-semibold text-gray-900">{step.title}</p>
                <p className="text-gray-600 text-sm leading-relaxed">{step.detail}</p>
                {step.url && (
                  <p className="text-sm font-mono text-blue-700">🔗 {step.url}</p>
                )}
                {step.warning && step.warningText && (
                  <div className="border-l-4 border-yellow-400 bg-yellow-50 px-3 py-2 rounded-r">
                    <p className="text-sm text-yellow-800 font-medium">⚠️ {step.warningText}</p>
                  </div>
                )}
                {step.screenshot && (
                  <div className="border-2 border-dashed border-gray-200 rounded-lg px-4 py-6 text-center">
                    <p className="text-xs text-gray-400">{step.screenshot}</p>
                  </div>
                )}
              </div>
            </div>
          ))}
        </section>

        <hr className="border-gray-200 mb-8 print-break" />

        {/* Checklist */}
        <section className="mb-12">
          <h2 className="text-xl font-semibold text-gray-800 mb-4">Checklist de verificación</h2>
          <p className="text-sm text-gray-500 mb-4 no-print">
            Marca cada ítem antes de ingresar tus credenciales en el dashboard.
          </p>
          <div className="space-y-3">
            {CHECKLIST.map((item, i) => (
              <label
                key={i}
                className="flex items-start gap-3 cursor-pointer group no-print"
                onClick={() => toggle(i)}
              >
                <span className="mt-0.5 shrink-0">
                  {checked[i] ? (
                    <CheckSquare className="h-5 w-5 text-green-600" />
                  ) : (
                    <Square className="h-5 w-5 text-gray-300 group-hover:text-gray-400" />
                  )}
                </span>
                <span className={`text-sm ${checked[i] ? 'line-through text-gray-400' : 'text-gray-700'}`}>
                  {item}
                </span>
              </label>
            ))}
            {/* Print-only static checklist */}
            {CHECKLIST.map((item, i) => (
              <div key={`print-${i}`} className="hidden print:flex items-start gap-3">
                <span className="mt-0.5 shrink-0 h-5 w-5 border-2 border-gray-400 rounded" />
                <span className="text-sm text-gray-700">{item}</span>
              </div>
            ))}
          </div>
        </section>

        <hr className="border-gray-200 mb-8" />

        {/* Data to collect */}
        <section className="mb-12">
          <h2 className="text-xl font-semibold text-gray-800 mb-4">Datos que debes recopilar</h2>
          <p className="text-sm text-gray-600 mb-4">
            Anota estos valores antes de ir al formulario del dashboard:
          </p>
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="bg-gray-50">
                <th className="border border-gray-200 px-4 py-2 text-left font-semibold text-gray-700">Campo</th>
                <th className="border border-gray-200 px-4 py-2 text-left font-semibold text-gray-700">Dónde encontrarlo</th>
                <th className="border border-gray-200 px-4 py-2 text-left font-semibold text-gray-700 w-40">Tu valor</th>
              </tr>
            </thead>
            <tbody>
              {[
                { campo: 'Phone Number ID', donde: 'WhatsApp → Configuración de API' },
                { campo: 'WABA ID', donde: 'WhatsApp → Configuración de API (junto al Phone Number ID)' },
                { campo: 'Token permanente', donde: 'Meta Business Suite → Usuarios del sistema → Generar token' },
              ].map((row) => (
                <tr key={row.campo}>
                  <td className="border border-gray-200 px-4 py-2 font-mono text-gray-900">{row.campo}</td>
                  <td className="border border-gray-200 px-4 py-2 text-gray-600">{row.donde}</td>
                  <td className="border border-gray-200 px-4 py-2 text-gray-300 text-xs italic">Anota aquí...</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        {/* Footer */}
        <div className="border-t border-gray-200 pt-6 text-center">
          <p className="text-sm text-gray-500">
            ¿Necesitas ayuda? Contáctanos en{' '}
            <span className="text-blue-700">soporte@lanlabsec.com</span>
          </p>
          <p className="text-xs text-gray-400 mt-1">LanLabs — Plataforma de Agentes IA</p>
        </div>
      </div>
    </>
  )
}
