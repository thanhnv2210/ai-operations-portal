import { useEffect, useRef, useState } from 'react'

export type SseEventType = 'status' | 'sql' | 'token' | 'error'

interface SseEvent {
  type: SseEventType
  text?: string
  sql?: string
  code?: string
  message?: string
}

export interface TextToSqlError {
  code: string
  message: string
}

export interface TextToSqlState {
  status: string
  sql: string | null
  explanation: string
  error: TextToSqlError | null
  streaming: boolean
}

export const SQL_SUGGESTED = [
  'How many transactions failed today?',
  'Failure rate by hub this month',
  'Top 5 corridors by volume this week',
  'Most common error codes last 7 days',
  'Hourly transaction volume in the last 24 hours',
  'Which active corridors send to the Philippines?',
]

const ERROR_MESSAGES: Record<string, string> = {
  sql_validation_rejected: 'I can only run read queries on whitelisted tables.',
  sql_generation_failed:   'Could not generate valid SQL for that question — try rephrasing.',
  db_execution_error:      'The query failed to execute — try a more specific filter.',
  no_results:              'No data found for that query.',
  network_error:           'Network error — check that the API service is running.',
  internal_error:          'An unexpected error occurred.',
}

export function friendlyError(code: string, fallback: string): string {
  return ERROR_MESSAGES[code] ?? fallback
}

export function applyEvent(prev: TextToSqlState, event: SseEvent): TextToSqlState {
  switch (event.type) {
    case 'status':
      return { ...prev, status: event.text ?? '' }
    case 'sql':
      return { ...prev, sql: event.sql ?? null, status: '' }
    case 'token':
      return { ...prev, explanation: prev.explanation + (event.text ?? '') }
    case 'error':
      return { ...prev, error: { code: event.code ?? 'unknown', message: event.message ?? 'Unknown error' }, status: '' }
    default:
      return prev
  }
}

const INITIAL_STATE: TextToSqlState = {
  status: '',
  sql: null,
  explanation: '',
  error: null,
  streaming: false,
}

export function useTextToSql() {
  const [state, setState] = useState<TextToSqlState>(INITIAL_STATE)
  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => () => { abortRef.current?.abort() }, [])

  async function ask(question: string) {
    if (state.streaming) return

    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller

    setState({ status: 'Starting...', sql: null, explanation: '', error: null, streaming: true })

    try {
      const res = await fetch('/api/v1/assistant/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
        signal: controller.signal,
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
            const event = JSON.parse(data) as SseEvent
            setState(prev => applyEvent(prev, event))
          } catch { /* skip malformed */ }
        }
      }
    } catch (e) {
      if ((e as Error).name === 'AbortError') {
        setState(prev => ({ ...prev, streaming: false, status: '' }))
        return
      }
      setState(prev => ({
        ...prev,
        error: { code: 'network_error', message: String(e) },
        status: '',
      }))
    } finally {
      setState(prev => ({ ...prev, streaming: false, status: '' }))
    }
  }

  function reset() {
    abortRef.current?.abort()
    setState(INITIAL_STATE)
  }

  function cancel() {
    abortRef.current?.abort()
    setState(prev => ({ ...prev, streaming: false, status: '' }))
  }

  return { ...state, ask, reset, cancel }
}
