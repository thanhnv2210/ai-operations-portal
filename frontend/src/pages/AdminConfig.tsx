import { useEffect, useState } from 'react'
import { Check, Plus, Save, Settings, Trash2, X } from 'lucide-react'

// --- Types ---

interface Thresholds {
  failure_rate_warning: number
  failure_rate_critical: number
  processing_time_warning_s: number
  processing_time_critical_s: number
  min_transaction_volume_per_day: number
}

interface PromptTemplate {
  id: string
  name: string
  description: string
  template: string
  updated_at: string
}

// --- API helpers ---

async function fetchJson<T>(url: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(url, opts)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

// --- Sub-components ---

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-border bg-card p-6 space-y-5">
      <h2 className="text-xs font-semibold uppercase tracking-widest text-faint">{title}</h2>
      {children}
    </div>
  )
}

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-3 items-start gap-4">
      <div className="pt-1">
        <p className="text-sm font-medium text-foreground">{label}</p>
        {hint && <p className="text-xs text-muted-foreground mt-0.5">{hint}</p>}
      </div>
      <div className="col-span-2">{children}</div>
    </div>
  )
}

function NumberInput({ value, onChange, step = 1, suffix }: {
  value: number; onChange: (v: number) => void; step?: number; suffix?: string
}) {
  return (
    <div className="flex items-center gap-2">
      <input
        type="number" value={value} step={step}
        onChange={e => onChange(Number(e.target.value))}
        className="w-36 rounded-md border border-border bg-card px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
      />
      {suffix && <span className="text-sm text-muted-foreground">{suffix}</span>}
    </div>
  )
}

// --- Main page ---

export function AdminConfig() {
  // Thresholds
  const [thresholds, setThresholds] = useState<Thresholds | null>(null)
  const [thresholdsDraft, setThresholdsDraft] = useState<Thresholds | null>(null)
  const [thresholdsSaving, setThresholdsSaving] = useState(false)
  const [thresholdsSaved, setThresholdsSaved]   = useState(false)

  // Prompt templates
  const [templates, setTemplates]         = useState<PromptTemplate[]>([])
  const [editingId, setEditingId]         = useState<string | null>(null)
  const [editDraft, setEditDraft]         = useState<Partial<PromptTemplate>>({})
  const [showNew, setShowNew]             = useState(false)
  const [newDraft, setNewDraft]           = useState({ name: '', description: '', template: '' })
  const [templatesError, setTemplatesError] = useState<string | null>(null)

  useEffect(() => {
    fetchJson<Thresholds>('/api/v1/admin/thresholds').then(t => {
      setThresholds(t)
      setThresholdsDraft(t)
    })
    fetchJson<PromptTemplate[]>('/api/v1/admin/prompts').then(setTemplates)
  }, [])

  async function saveThresholds() {
    if (!thresholdsDraft) return
    setThresholdsSaving(true)
    try {
      const updated = await fetchJson<Thresholds>('/api/v1/admin/thresholds', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(thresholdsDraft),
      })
      setThresholds(updated)
      setThresholdsSaved(true)
      setTimeout(() => setThresholdsSaved(false), 2000)
    } finally {
      setThresholdsSaving(false)
    }
  }

  function patchDraft(key: keyof Thresholds, value: number) {
    setThresholdsDraft(d => d ? { ...d, [key]: value } : d)
  }

  function startEdit(t: PromptTemplate) {
    setEditingId(t.id)
    setEditDraft({ name: t.name, description: t.description, template: t.template })
  }

  async function saveEdit(id: string) {
    const updated = await fetchJson<PromptTemplate>(`/api/v1/admin/prompts/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(editDraft),
    })
    setTemplates(ts => ts.map(t => t.id === id ? updated : t))
    setEditingId(null)
  }

  async function deleteTemplate(id: string) {
    await fetch(`/api/v1/admin/prompts/${id}`, { method: 'DELETE' })
    setTemplates(ts => ts.filter(t => t.id !== id))
  }

  async function createTemplate() {
    if (!newDraft.name.trim() || !newDraft.template.trim()) {
      setTemplatesError('Name and template are required.')
      return
    }
    setTemplatesError(null)
    const created = await fetchJson<PromptTemplate>('/api/v1/admin/prompts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(newDraft),
    })
    setTemplates(ts => [...ts, created])
    setNewDraft({ name: '', description: '', template: '' })
    setShowNew(false)
  }

  const inputCls = 'w-full rounded-md border border-border bg-card px-3 py-1.5 text-sm text-foreground placeholder:text-faint focus:outline-none focus:ring-2 focus:ring-primary/40'
  const textareaCls = `${inputCls} min-h-24 resize-y font-mono`

  return (
    <div className="min-h-screen bg-background p-6">
      <div className="mx-auto max-w-3xl space-y-6">
        <div className="flex items-center gap-3">
          <Settings size={22} className="text-primary" />
          <h1 className="text-2xl font-bold text-foreground">Admin Configuration</h1>
        </div>

        {/* ── Alert Thresholds ── */}
        <Section title="Alert Thresholds">
          {thresholdsDraft && (
            <div className="space-y-4">
              <Field label="Failure Rate — Warning" hint="e.g. 0.05 = 5%">
                <NumberInput value={thresholdsDraft.failure_rate_warning} step={0.01}
                  onChange={v => patchDraft('failure_rate_warning', v)} suffix="(0–1)" />
              </Field>
              <Field label="Failure Rate — Critical" hint="e.g. 0.10 = 10%">
                <NumberInput value={thresholdsDraft.failure_rate_critical} step={0.01}
                  onChange={v => patchDraft('failure_rate_critical', v)} suffix="(0–1)" />
              </Field>
              <Field label="Processing Time — Warning">
                <NumberInput value={thresholdsDraft.processing_time_warning_s}
                  onChange={v => patchDraft('processing_time_warning_s', v)} suffix="seconds" />
              </Field>
              <Field label="Processing Time — Critical">
                <NumberInput value={thresholdsDraft.processing_time_critical_s}
                  onChange={v => patchDraft('processing_time_critical_s', v)} suffix="seconds" />
              </Field>
              <Field label="Min Volume / Day" hint="Below this triggers a low-volume alert">
                <NumberInput value={thresholdsDraft.min_transaction_volume_per_day}
                  onChange={v => patchDraft('min_transaction_volume_per_day', v)} suffix="transactions" />
              </Field>

              <div className="pt-2 flex items-center gap-3">
                <button onClick={saveThresholds} disabled={thresholdsSaving}
                  className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50 transition-opacity">
                  {thresholdsSaved ? <Check size={14} /> : <Save size={14} />}
                  {thresholdsSaved ? 'Saved' : thresholdsSaving ? 'Saving…' : 'Save Thresholds'}
                </button>
                <button onClick={() => setThresholdsDraft(thresholds)}
                  className="text-sm text-muted-foreground hover:text-foreground transition-colors">
                  Reset
                </button>
              </div>
            </div>
          )}
        </Section>

        {/* ── Prompt Templates ── */}
        <Section title="Prompt Templates">
          <div className="space-y-4">
            {templates.map(t => (
              <div key={t.id} className="rounded-lg border border-border p-4 space-y-3">
                {editingId === t.id ? (
                  <>
                    <input value={editDraft.name ?? ''} placeholder="Name"
                      onChange={e => setEditDraft(d => ({ ...d, name: e.target.value }))}
                      className={inputCls} />
                    <input value={editDraft.description ?? ''} placeholder="Description"
                      onChange={e => setEditDraft(d => ({ ...d, description: e.target.value }))}
                      className={inputCls} />
                    <textarea value={editDraft.template ?? ''} placeholder="Template (use {{variable}} for placeholders)"
                      onChange={e => setEditDraft(d => ({ ...d, template: e.target.value }))}
                      className={textareaCls} />
                    <div className="flex gap-2">
                      <button onClick={() => saveEdit(t.id)}
                        className="flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:opacity-90">
                        <Check size={13} /> Save
                      </button>
                      <button onClick={() => setEditingId(null)}
                        className="flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-sm text-muted-foreground hover:bg-subtle">
                        <X size={13} /> Cancel
                      </button>
                    </div>
                  </>
                ) : (
                  <>
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-sm font-medium text-foreground">{t.name}</p>
                        {t.description && <p className="text-xs text-muted-foreground mt-0.5">{t.description}</p>}
                      </div>
                      <div className="flex gap-1 shrink-0">
                        <button onClick={() => startEdit(t)}
                          className="rounded-md px-2.5 py-1 text-xs text-muted-foreground border border-border hover:bg-subtle transition-colors">
                          Edit
                        </button>
                        <button onClick={() => deleteTemplate(t.id)}
                          className="rounded-md p-1.5 text-muted-foreground hover:text-red-400 hover:bg-red-500/10 transition-colors">
                          <Trash2 size={13} />
                        </button>
                      </div>
                    </div>
                    <pre className="rounded-md bg-muted px-3 py-2 text-xs text-muted-foreground whitespace-pre-wrap font-mono overflow-x-auto">
                      {t.template}
                    </pre>
                    <p className="text-xs text-faint">Updated {new Date(t.updated_at).toLocaleString()}</p>
                  </>
                )}
              </div>
            ))}

            {/* New template form */}
            {showNew ? (
              <div className="rounded-lg border border-primary/30 bg-primary/5 p-4 space-y-3">
                <p className="text-sm font-medium text-foreground">New Template</p>
                {templatesError && <p className="text-xs text-red-400">{templatesError}</p>}
                <input value={newDraft.name} placeholder="Name *"
                  onChange={e => setNewDraft(d => ({ ...d, name: e.target.value }))}
                  className={inputCls} />
                <input value={newDraft.description} placeholder="Description"
                  onChange={e => setNewDraft(d => ({ ...d, description: e.target.value }))}
                  className={inputCls} />
                <textarea value={newDraft.template} placeholder="Template text * (use {{variable}} for placeholders)"
                  onChange={e => setNewDraft(d => ({ ...d, template: e.target.value }))}
                  className={textareaCls} />
                <div className="flex gap-2">
                  <button onClick={createTemplate}
                    className="flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:opacity-90">
                    <Check size={13} /> Create
                  </button>
                  <button onClick={() => { setShowNew(false); setTemplatesError(null) }}
                    className="flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-sm text-muted-foreground hover:bg-subtle">
                    <X size={13} /> Cancel
                  </button>
                </div>
              </div>
            ) : (
              <button onClick={() => setShowNew(true)}
                className="flex items-center gap-2 rounded-lg border border-dashed border-border px-4 py-3 text-sm text-muted-foreground hover:border-primary/40 hover:text-foreground hover:bg-subtle transition-colors w-full">
                <Plus size={15} /> Add prompt template
              </button>
            )}
          </div>
        </Section>
      </div>
    </div>
  )
}
