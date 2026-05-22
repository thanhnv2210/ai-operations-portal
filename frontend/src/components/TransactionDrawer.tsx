import { X } from 'lucide-react'
import { useTransactionDetail } from '@/hooks/useTransactions'
import { StatusBadge } from '@/components/StatusBadge'
import { fmtSgt } from '@/lib/sgt'

interface Props {
  transactionId: number | null
  onClose: () => void
}

function Field({ label, value }: { label: string; value?: string | number | null }) {
  if (value == null || value === '') return null
  return (
    <div>
      <dt className="text-xs text-faint">{label}</dt>
      <dd className="mt-0.5 text-sm text-foreground break-all">{value}</dd>
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h3 className="mb-3 text-xs font-semibold uppercase tracking-widest text-faint">{title}</h3>
      <dl className="grid grid-cols-2 gap-x-4 gap-y-3">{children}</dl>
    </div>
  )
}

export function TransactionDrawer({ transactionId, onClose }: Props) {
  const { detail, audit, loading } = useTransactionDetail(transactionId)

  if (transactionId === null) return null

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm" onClick={onClose} />

      {/* Drawer */}
      <div className="fixed inset-y-0 right-0 z-50 flex w-full max-w-2xl flex-col border-l border-border bg-background shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border px-6 py-4">
          <div>
            <p className="text-xs text-faint">Transaction</p>
            <p className="font-mono text-sm font-medium text-foreground">#{transactionId}</p>
          </div>
          <button onClick={onClose} className="rounded-lg p-2 text-muted-foreground hover:bg-subtle hover:text-foreground transition-colors">
            <X size={18} />
          </button>
        </div>

        {loading && (
          <div className="flex flex-1 items-center justify-center">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-border border-t-primary" />
          </div>
        )}

        {!loading && detail && (
          <div className="flex-1 overflow-y-auto px-6 py-5 space-y-6">
            {/* Status */}
            <div className="flex flex-wrap gap-2">
              <StatusBadge status={detail.status} />
              {detail.fraud_status && detail.fraud_status !== 'APPROVE' && (
                <StatusBadge status={`FRAUD: ${detail.fraud_status}`} />
              )}
            </div>

            <Section title="Identity">
              <Field label="Payment Reference" value={detail.payment_reference_id} />
              <Field label="Hub Transaction ID" value={detail.hub_transaction_id_submit || detail.hub_transaction_id} />
              <Field label="Partner Transaction ID" value={detail.partner_transaction_id_submit} />
              <Field label="Hub" value={detail.hub_name_resolved || detail.hub_name} />
              <Field label="Service" value={detail.service_name_resolved || detail.service_name} />
              <Field label="Partner Channel" value={detail.partner_id} />
              <Field label="Created (SGT)" value={fmtSgt(detail.created_date)} />
              <Field label="Updated (SGT)" value={fmtSgt(detail.updated_date)} />
            </Section>

            <div className="border-t border-border" />

            <Section title="Amounts">
              <Field label={`Send (${detail.sender_currency ?? ''})`} value={detail.remittance_amount?.toFixed(2)} />
              <Field label={`Receive (${detail.recipient_currency ?? ''})`} value={detail.recipient_amount?.toFixed(2)} />
              <Field label="Retail Fee" value={detail.retail_fee != null ? `${detail.retail_fee.toFixed(2)} ${detail.sender_currency ?? ''}` : null} />
              <Field label="FX Rate (retail)" value={detail.retail_exchange_rate?.toFixed(6)} />
              <Field label="FX Rate (hub)" value={detail.hub_exchange_rate?.toFixed(6)} />
              <Field label="Payment Mode" value={detail.payment_mode} />
            </Section>

            <div className="border-t border-border" />

            <Section title="Route">
              <Field label="Sender Country" value={detail.sender_country} />
              <Field label="Recipient Country" value={detail.recipient_country} />
              <Field label="Sender Account" value={detail.sender_account_id} />
              <Field label="Recipient ID" value={detail.recipient_id} />
            </Section>

            {(detail.error_code || detail.hub_error_code || detail.hub_status) && (
              <>
                <div className="border-t border-border" />
                <Section title="Errors">
                  <Field label="Error Code" value={detail.error_code} />
                  <Field label="Error Message" value={detail.error_message} />
                  <Field label="Hub Status" value={detail.hub_status} />
                  <Field label="Hub Sub-Status" value={detail.hub_sub_status} />
                  <Field label="Hub Error Code" value={detail.hub_error_code} />
                  <Field label="Hub Error Message" value={detail.hub_error_message} />
                </Section>
              </>
            )}

            <div className="border-t border-border" />

            {/* Audit Timeline */}
            <div>
              <h3 className="mb-4 text-xs font-semibold uppercase tracking-widest text-faint">Audit Timeline</h3>
              {audit.length === 0 ? (
                <p className="text-sm text-muted-foreground">No audit records.</p>
              ) : (
                <ol className="relative border-l border-border pl-5 space-y-4">
                  {audit.map((entry, i) => (
                    <li key={entry.id} className="relative">
                      <span className={`absolute -left-[1.375rem] flex h-3 w-3 items-center justify-center rounded-full ring-2 ring-background ${i === audit.length - 1 ? 'bg-primary' : 'bg-subtle'}`} />
                      <div className="flex flex-col gap-0.5">
                        <time className="text-xs text-faint">
                          {fmtSgt(entry.audit_date)}
                        </time>
                        <StatusBadge status={entry.status} />
                        {entry.hub_status && (
                          <p className="text-xs text-muted-foreground">Hub: {entry.hub_status}{entry.hub_sub_status ? ` / ${entry.hub_sub_status}` : ''}</p>
                        )}
                        {entry.error_code && (
                          <p className="text-xs text-red-400">Error: {entry.error_code}</p>
                        )}
                        {entry.hub_error_code && (
                          <p className="text-xs text-red-400">Hub Error: {entry.hub_error_code}</p>
                        )}
                      </div>
                    </li>
                  ))}
                </ol>
              )}
            </div>
          </div>
        )}
      </div>
    </>
  )
}
