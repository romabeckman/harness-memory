'use client'

import { useState } from 'react'
import { Copy, Check, AlertTriangle, ShieldCheck } from 'lucide-react'

interface SecretRevealModalProps {
  token: string
  onClose: () => void
}

export function SecretRevealModal({ token, onClose }: SecretRevealModalProps) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(token)
      setCopied(true)
      setTimeout(() => setCopied(false), 3000)
    } catch {
      // Fallback
      setCopied(true)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
      <div className="w-full max-w-lg rounded-xl border border-border bg-card p-6 shadow-2xl space-y-5 animate-in fade-in zoom-in-95 duration-200">
        <div className="flex items-center space-x-3 text-emerald-400">
          <ShieldCheck className="h-6 w-6" />
          <h2 className="text-xl font-semibold text-white">Token Emitido com Sucesso!</h2>
        </div>

        <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-200 flex items-start space-x-3">
          <AlertTriangle className="h-5 w-5 flex-shrink-0 text-amber-400 mt-0.5" />
          <div>
            <span className="font-semibold text-amber-300 block mb-1">Aviso de Exibição Única (One-Time Reveal):</span>
            Por motivos de segurança, este segredo em texto puro só pode ser visualizado agora. Ele não será exibido novamente e não pode ser recuperado no banco.
          </div>
        </div>

        <div className="space-y-2">
          <label className="text-xs font-medium uppercase tracking-wider text-gray-400">
            Credencial Gerada (Plaintext Secret)
          </label>
          <div className="flex items-center space-x-2">
            <input
              type="text"
              readOnly
              value={token}
              className="flex-1 rounded-lg border border-border bg-black/50 px-3 py-2.5 font-mono text-sm text-emerald-300 focus:outline-none select-all"
            />
            <button
              onClick={handleCopy}
              className="inline-flex items-center justify-center rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-card"
            >
              {copied ? (
                <>
                  <Check className="mr-1.5 h-4 w-4 text-emerald-300" />
                  Copiado!
                </>
              ) : (
                <>
                  <Copy className="mr-1.5 h-4 w-4" />
                  Copiar
                </>
              )}
            </button>
          </div>
        </div>

        <div className="flex justify-end pt-2">
          <button
            onClick={onClose}
            className="rounded-lg border border-border bg-gray-800 px-5 py-2 text-sm font-medium text-gray-200 transition hover:bg-gray-700 focus:outline-none"
          >
            Concluir e Fechar
          </button>
        </div>
      </div>
    </div>
  )
}
