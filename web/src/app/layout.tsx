import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Harness Memory — Admin Console',
  description: 'Harness Memory admin console for managing tokens and service accounts',
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en-US" className="dark">
      <body className="antialiased selection:bg-blue-600 selection:text-white">
        {children}
      </body>
    </html>
  )
}
