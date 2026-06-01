import { next } from '@vercel/edge'

export const config = {
  matcher: '/(.*)',
}

export default function middleware(request: Request) {
  const authHeader = request.headers.get('Authorization')

  if (authHeader?.startsWith('Basic ')) {
    const base64 = authHeader.slice(6)
    const decoded = atob(base64)
    const colonIdx = decoded.indexOf(':')
    const username = decoded.slice(0, colonIdx)
    const password = decoded.slice(colonIdx + 1)

    const validUser = process.env.BASIC_AUTH_USER
    const validPass = process.env.BASIC_AUTH_PASSWORD

    if (validUser && validPass && username === validUser && password === validPass) {
      return next()
    }
  }

  return new Response('Unauthorized', {
    status: 401,
    headers: {
      'WWW-Authenticate': 'Basic realm="AI Operations Portal", charset="UTF-8"',
    },
  })
}
