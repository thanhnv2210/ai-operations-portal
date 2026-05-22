export interface TransactionRow {
  internal_transaction_id: number
  payment_reference_id: string | null
  status: string | null
  hub_name: string | null
  service_name: string | null
  remittance_amount: number | null
  recipient_amount: number | null
  sender_currency: string | null
  recipient_currency: string | null
  recipient_country: string | null
  error_code: string | null
  hub_error_code: string | null
  fraud_status: string | null
  payment_mode: string | null
  created_date: string | null
  updated_date: string | null
}

export interface TransactionPage {
  items: TransactionRow[]
  total: number
  page: number
  page_size: number
  pages: number
}

export interface TransactionDetail {
  internal_transaction_id: number
  payment_reference_id: string | null
  hub_transaction_id: string | null
  hub_transaction_id_submit: string | null
  partner_transaction_id_submit: string | null
  refund_reference_id: string | null
  status: string | null
  fraud_status: string | null
  proxy_refund_status: string | null
  hub_id: number | null
  hub_name: string | null
  hub_name_resolved: string | null
  service_id: number | null
  service_name: string | null
  service_name_resolved: string | null
  service_type: number | null
  partner_id: string | null
  remittance_amount: number | null
  recipient_amount: number | null
  retail_fee: number | null
  retail_tax_amount: number | null
  sender_currency: string | null
  recipient_currency: string | null
  currency_flag: number | null
  hub_exchange_rate: number | null
  retail_exchange_rate: number | null
  markup_rate: number | null
  markup_fee: number | null
  hub_gross_fee: number | null
  sender_account_id: string | null
  sender_country: string | null
  sender_nationality: string | null
  recipient_id: string | null
  recipient_country: string | null
  recipient_nationality: string | null
  error_code: string | null
  error_message: string | null
  hub_status: string | null
  hub_status_id: string | null
  hub_sub_status: string | null
  hub_error_code: string | null
  hub_error_message: string | null
  payment_mode: string | null
  source_of_fund_ref_id: string | null
  remit_purpose_id: string | null
  external_service_id: number | null
  created_date: string | null
  updated_date: string | null
  version: number | null
}

export interface AuditEntry {
  id: number
  audit_date: string | null
  status: string | null
  hub_status: string | null
  hub_sub_status: string | null
  error_code: string | null
  hub_error_code: string | null
  fraud_status: string | null
  proxy_refund_status: string | null
}

export interface TransactionFilters {
  from_date: string
  to_date: string
  status: string[]
  hub_id?: number
  service_id?: number
  error_code?: string
  payment_reference_id?: string
  sort_order: 'asc' | 'desc'
  page: number
  page_size: number
}

export interface RefItem {
  id: number
  name: string
  active: boolean
}
