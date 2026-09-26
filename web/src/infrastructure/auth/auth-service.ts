import { SessionManager } from '@/infrastructure/auth/session-manager'

export class AuthService {
  private static instance: SessionManager | null = null

  public static getSessionManager(): SessionManager {
    if (!AuthService.instance) {
      const secret =
        process.env.SESSION_SECRET ||
        process.env.API_ADMIN_TOKEN ||
        'fallback_insecure_secret_for_local_dev_only_12345678'
      AuthService.instance = new SessionManager(secret)
    }
    return AuthService.instance
  }
}
