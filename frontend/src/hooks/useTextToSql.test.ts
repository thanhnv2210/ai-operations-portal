/**
 * Unit tests for useTextToSql pure-logic exports.
 *
 * Tests cover:
 *   - applyEvent: state reducer for each SSE event type
 *   - friendlyError: user-facing error message lookup
 *   - SQL_SUGGESTED: sanity checks on the example chips list
 *
 * No React rendering or fetch mocking — all functions under test are
 * synchronous and pure.
 */

import { describe, expect, it } from 'vitest'

import {
  SQL_SUGGESTED,
  applyEvent,
  friendlyError,
  type TextToSqlState,
} from './useTextToSql'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const EMPTY_STATE: TextToSqlState = {
  status: '',
  sql: null,
  explanation: '',
  error: null,
  streaming: false,
}

// ---------------------------------------------------------------------------
// applyEvent — status events
// ---------------------------------------------------------------------------

describe('applyEvent — status', () => {
  it('sets status from text field', () => {
    const next = applyEvent(EMPTY_STATE, { type: 'status', text: 'Generating SQL…' })
    expect(next.status).toBe('Generating SQL…')
  })

  it('preserves other fields when status arrives', () => {
    const prev: TextToSqlState = { ...EMPTY_STATE, sql: 'SELECT 1', explanation: 'hi' }
    const next = applyEvent(prev, { type: 'status', text: 'Running…' })
    expect(next.sql).toBe('SELECT 1')
    expect(next.explanation).toBe('hi')
    expect(next.error).toBeNull()
  })

  it('uses empty string when text is undefined', () => {
    const next = applyEvent(EMPTY_STATE, { type: 'status' })
    expect(next.status).toBe('')
  })
})

// ---------------------------------------------------------------------------
// applyEvent — sql events
// ---------------------------------------------------------------------------

describe('applyEvent — sql', () => {
  it('sets sql from sql field', () => {
    const next = applyEvent(EMPTY_STATE, { type: 'sql', sql: 'SELECT COUNT(*) FROM remittance.transaction' })
    expect(next.sql).toBe('SELECT COUNT(*) FROM remittance.transaction')
  })

  it('clears status when sql event arrives', () => {
    const prev: TextToSqlState = { ...EMPTY_STATE, status: 'Generating SQL…' }
    const next = applyEvent(prev, { type: 'sql', sql: 'SELECT 1' })
    expect(next.status).toBe('')
  })

  it('sets sql to null when sql field is missing', () => {
    const next = applyEvent(EMPTY_STATE, { type: 'sql' })
    expect(next.sql).toBeNull()
  })

  it('preserves explanation when sql event arrives', () => {
    const prev: TextToSqlState = { ...EMPTY_STATE, explanation: 'existing text' }
    const next = applyEvent(prev, { type: 'sql', sql: 'SELECT 1' })
    expect(next.explanation).toBe('existing text')
  })
})

// ---------------------------------------------------------------------------
// applyEvent — token events
// ---------------------------------------------------------------------------

describe('applyEvent — token', () => {
  it('appends text to explanation', () => {
    const prev: TextToSqlState = { ...EMPTY_STATE, explanation: 'Hello' }
    const next = applyEvent(prev, { type: 'token', text: ' World' })
    expect(next.explanation).toBe('Hello World')
  })

  it('builds explanation from empty string', () => {
    const next = applyEvent(EMPTY_STATE, { type: 'token', text: 'First token' })
    expect(next.explanation).toBe('First token')
  })

  it('appends empty string when text is undefined', () => {
    const prev: TextToSqlState = { ...EMPTY_STATE, explanation: 'abc' }
    const next = applyEvent(prev, { type: 'token' })
    expect(next.explanation).toBe('abc')
  })

  it('accumulates multiple tokens in sequence', () => {
    let state = EMPTY_STATE
    for (const token of ['The ', 'query ', 'found ', '42 ', 'rows.']) {
      state = applyEvent(state, { type: 'token', text: token })
    }
    expect(state.explanation).toBe('The query found 42 rows.')
  })

  it('does not change status or sql on token event', () => {
    const prev: TextToSqlState = { ...EMPTY_STATE, status: 'Explaining…', sql: 'SELECT 1' }
    const next = applyEvent(prev, { type: 'token', text: 'text' })
    expect(next.status).toBe('Explaining…')
    expect(next.sql).toBe('SELECT 1')
  })
})

// ---------------------------------------------------------------------------
// applyEvent — error events
// ---------------------------------------------------------------------------

describe('applyEvent — error', () => {
  it('sets error code and message', () => {
    const next = applyEvent(EMPTY_STATE, {
      type: 'error',
      code: 'sql_validation_rejected',
      message: 'Write ops are blocked.',
    })
    expect(next.error).toEqual({ code: 'sql_validation_rejected', message: 'Write ops are blocked.' })
  })

  it('clears status when error event arrives', () => {
    const prev: TextToSqlState = { ...EMPTY_STATE, status: 'Generating SQL…' }
    const next = applyEvent(prev, { type: 'error', code: 'internal_error', message: 'oops' })
    expect(next.status).toBe('')
  })

  it('uses unknown code when code field is missing', () => {
    const next = applyEvent(EMPTY_STATE, { type: 'error', message: 'something broke' })
    expect(next.error?.code).toBe('unknown')
  })

  it('uses Unknown error message when message field is missing', () => {
    const next = applyEvent(EMPTY_STATE, { type: 'error', code: 'internal_error' })
    expect(next.error?.message).toBe('Unknown error')
  })

  it('preserves sql when error event arrives', () => {
    const prev: TextToSqlState = { ...EMPTY_STATE, sql: 'SELECT 1' }
    const next = applyEvent(prev, { type: 'error', code: 'db_execution_error', message: 'failed' })
    expect(next.sql).toBe('SELECT 1')
  })
})

// ---------------------------------------------------------------------------
// applyEvent — unknown event type
// ---------------------------------------------------------------------------

describe('applyEvent — unknown type', () => {
  it('returns state unchanged for unknown event type', () => {
    // Cast to bypass TypeScript type check — real runtime defence
    const next = applyEvent(EMPTY_STATE, { type: 'unknown' as never })
    expect(next).toEqual(EMPTY_STATE)
  })
})

// ---------------------------------------------------------------------------
// friendlyError
// ---------------------------------------------------------------------------

describe('friendlyError', () => {
  it('returns mapped message for sql_validation_rejected', () => {
    const msg = friendlyError('sql_validation_rejected', 'fallback')
    expect(msg).toContain('read queries')
  })

  it('returns mapped message for sql_generation_failed', () => {
    const msg = friendlyError('sql_generation_failed', 'fallback')
    expect(msg).toContain('rephrasing')
  })

  it('returns mapped message for db_execution_error', () => {
    const msg = friendlyError('db_execution_error', 'fallback')
    expect(msg).toContain('execute')
  })

  it('returns mapped message for no_results', () => {
    const msg = friendlyError('no_results', 'fallback')
    expect(msg).toContain('No data')
  })

  it('returns mapped message for network_error', () => {
    const msg = friendlyError('network_error', 'fallback')
    expect(msg).toContain('Network')
  })

  it('returns mapped message for internal_error', () => {
    const msg = friendlyError('internal_error', 'fallback')
    expect(msg).toContain('unexpected')
  })

  it('returns fallback for unknown code', () => {
    const msg = friendlyError('totally_unknown_code', 'My fallback message')
    expect(msg).toBe('My fallback message')
  })

  it('returns fallback when code is empty string', () => {
    const msg = friendlyError('', 'default message')
    expect(msg).toBe('default message')
  })
})

// ---------------------------------------------------------------------------
// SQL_SUGGESTED
// ---------------------------------------------------------------------------

describe('SQL_SUGGESTED', () => {
  it('is a non-empty array', () => {
    expect(Array.isArray(SQL_SUGGESTED)).toBe(true)
    expect(SQL_SUGGESTED.length).toBeGreaterThan(0)
  })

  it('every entry is a non-empty string', () => {
    for (const s of SQL_SUGGESTED) {
      expect(typeof s).toBe('string')
      expect(s.trim().length).toBeGreaterThan(0)
    }
  })

  it('has no duplicate entries', () => {
    const unique = new Set(SQL_SUGGESTED)
    expect(unique.size).toBe(SQL_SUGGESTED.length)
  })
})
