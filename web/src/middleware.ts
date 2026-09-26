import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'
import { jwtVerify } from 'jose'
import { SessionManager } from '@/infrastructure/auth/session-manager'

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl

  // Ignore static assets
  if (
    pathname.startsWith('/_next') ||
    pathname.startsWith('/api') ||
    pathname === '/favicon.ico'
  ) {
    return NextResponse.next()
  }

  const sessionCookie = request.cookies.get(SessionManager.COOKIE_NAME)
  let isAuthenticated = false

  if (sessionCookie?.value) {
    try {
      const secret =
        process.env.SESSION_SECRET ||
        process.env.API_ADMIN_TOKEN ||
        'fallback_insecure_secret_for_local_dev_only_12345678'
      const key = new TextEncoder().encode(secret)
      await jwtVerify(sessionCookie.value, key)
      isAuthenticated = true
    } catch {
      isAuthenticated = false
    }
  }

  // Redirect authenticated user from /login to /
  if (pathname === '/login' && isAuthenticated) {
    return NextResponse.redirect(new URL('/', request.url))
  }

  // Redirect unauthenticated user from protected routes to /login
  if (pathname !== '/login' && !isAuthenticated) {
    return NextResponse.redirect(new URL('/login', request.url))
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
}
