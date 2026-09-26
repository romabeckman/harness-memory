import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Harness Memory — Admin Console',
  description: 'Console administrativo de controle de tokens e contas de serviço do Harness Memory',
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="pt-BR" className="dark">
      <body className="antialiased selection:bg-blue-600 selection:text-white">
        {children}
      </body>
    </html>
  )
}
