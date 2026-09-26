'use server'

import { cookies } from 'next/headers'
import { redirect } from 'next/navigation'
import { AdminSession } from '@/domain/admin-session'
import { AuthService } from '@/infrastructure/auth/auth-service'
import { SessionManager } from '@/infrastructure/auth/session-manager'

export async function loginAction(formData: FormData): Promise<{ error?: string }> {
  const token = formData.get('token')?.toString().trim()
  const expectedToken = process.env.API_ADMIN_TOKEN || ''

  if (!token) {
    return { error: 'O token de administração é obrigatório.' }
  }

  try {
    const session = await AdminSession.authenticate(token, expectedToken)
    const sessionManager = AuthService.getSessionManager()
    const jwtString = await sessionManager.signSession(session.sessionId)
    const cookieOptions = sessionManager.getCookieOptions()

    const cookieStore = await cookies()
    cookieStore.set(SessionManager.COOKIE_NAME, jwtString, cookieOptions)
  } catch {
    return { error: 'Credencial inválida. Verifique o API_ADMIN_TOKEN.' }
  }

  redirect('/')
}

export async function logoutAction(): Promise<void> {
  const cookieStore = await cookies()
  cookieStore.delete(SessionManager.COOKIE_NAME)
  redirect('/login')
}
