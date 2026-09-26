import { SignJWT, jwtVerify } from 'jose'

export interface SessionCookieOptions {
  httpOnly: boolean
  secure: boolean
  sameSite: 'strict' | 'lax' | 'none'
  path: string
  maxAge: number
}

export class SessionManager {
  public static readonly COOKIE_NAME = 'hm_admin_session'
  private readonly secretKey: Uint8Array

  public constructor(secret: string) {
    this.secretKey = new TextEncoder().encode(secret)
  }

  public async signSession(sessionId: string): Promise<string> {
    return new SignJWT({ sessionId })
      .setProtectedHeader({ alg: 'HS256' })
      .setIssuedAt()
      .setExpirationTime('2h')
      .sign(this.secretKey)
  }

  public async verifySession(jwtString: string): Promise<{ sessionId: string } | null> {
    try {
      const { payload } = await jwtVerify(jwtString, this.secretKey)
      if (typeof payload.sessionId === 'string') {
        return { sessionId: payload.sessionId }
      }
      return null
    } catch {
      return null
    }
  }

  public getCookieOptions(): SessionCookieOptions {
    return {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'strict',
      path: '/',
      maxAge: 7200, // 2 hours
    }
  }
}
