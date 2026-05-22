import { useState } from 'react'

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  streaming?: boolean
}

export interface InsightsData {
  summary: string
  health: 'good' | 'warning' | 'critical'
  anomalies: { title: string; detail: string; severity: string }[]
  recommendations: { action: string; reason: string }[]
  context_period: string
}

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [streaming, setStreaming] = useState(false)

  async function send(message: string, fromDate?: string, toDate?: string) {
    if (streaming) return

    const userMsg: ChatMessage = { role: 'user', content: message }
    setMessages(prev => [...prev, userMsg, { role: 'assistant', content: '', streaming: true }])
    setStreaming(true)

    try {
      const res = await fetch('/api/v1/ai/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, from_date: fromDate, to_date: toDate }),
      })

      if (!res.ok || !res.body) throw new Error(`${res.status} ${res.statusText}`)

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })

        const lines = buffer.split('\n')
        buffer = lines.pop() ?? ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const data = line.slice(6)
          if (data === '[DONE]') break
          try {
            const parsed = JSON.parse(data)
            if (parsed.text) {
              setMessages(prev => {
                const msgs = [...prev]
                const last = msgs[msgs.length - 1]
                if (last?.role === 'assistant') {
                  msgs[msgs.length - 1] = { ...last, content: last.content + parsed.text }
                }
                return msgs
              })
            }
          } catch { /* skip malformed */ }
        }
      }
    } catch (e) {
      setMessages(prev => {
        const msgs = [...prev]
        const last = msgs[msgs.length - 1]
        if (last?.role === 'assistant') {
          msgs[msgs.length - 1] = { ...last, content: `Error: ${String(e)}` }
        }
        return msgs
      })
    } finally {
      setMessages(prev => {
        const msgs = [...prev]
        const last = msgs[msgs.length - 1]
        if (last?.role === 'assistant') {
          msgs[msgs.length - 1] = { ...last, streaming: false }
        }
        return msgs
      })
      setStreaming(false)
    }
  }

  function clear() { setMessages([]) }

  return { messages, streaming, send, clear }
}

export function useInsights() {
  const [data, setData] = useState<InsightsData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function generate(fromDate?: string, toDate?: string) {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch('/api/v1/ai/insights', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ from_date: fromDate, to_date: toDate }),
      })
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
      setData(await res.json())
    } catch (e) {
      setError(String(e))
    } finally {
      setLoading(false)
    }
  }

  return { data, loading, error, generate }
}
