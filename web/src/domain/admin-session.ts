export class AdminSession {
  private readonly _sessionId: string
  private _expiresAt: Date

  private constructor(sessionId: string, expiresAt: Date) {
    this._sessionId = sessionId
    this._expiresAt = expiresAt
  }

  public static async authenticate(
    providedToken: string,
    expectedToken: string
  ): Promise<AdminSession> {
    if (!providedToken || !expectedToken || providedToken !== expectedToken) {
      throw new Error('Invalid administrative credentials')
    }

    const sessionId = crypto.randomUUID()
    const expiresAt = new Date(Date.now() + 2 * 60 * 60 * 1000)

    return new AdminSession(sessionId, expiresAt)
  }

  public get sessionId(): string {
    return this._sessionId
  }

  public get expiresAt(): Date {
    return this._expiresAt
  }

  public isValid(): boolean {
    return Date.now() < this._expiresAt.getTime()
  }

  public touch(): void {
    if (!this.isValid()) {
      throw new Error('Cannot touch an expired session')
    }
    this._expiresAt = new Date(Date.now() + 2 * 60 * 60 * 1000)
  }
}
