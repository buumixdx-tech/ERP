import { apiClient } from '../client'

// Backend constants (Chinese)
export type LogisticsStatus = '待发货' | '在途' | '签收' | '完成' | '取消'
export type ExpressStatus = '待发货' | '在途' | '签收'

export interface ExpressItem {
  sku_id: number
  sku_name: string
  qty: number
}

// 服务端实际返回的地址信息（中文 key）
export interface AddressInfo {
  收货点位Id: number
  收货点位名称: string
  收货地址: string
  收货联系电话: string | null
  发货点位Id: number
  发货点位名称: string
  发货地址: string
  发货联系电话: string | null
}

export interface ExpressOrder {
  id: number
  tracking_number: string
  status: string
  address_info: AddressInfo
  items: ExpressItem[]
}

export interface Logistics {
  id: number
  virtual_contract_id: number
  status: string
  timestamp: string
  express_orders: ExpressOrder[]
  created_at?: string
}

export interface LogisticsDetail extends Logistics {
  express_orders: ExpressOrder[]
  vc_type?: string
  elements?: Array<{
    shipping_point_id?: number
    shipping_point_name?: string
    receiving_point_id?: number
    receiving_point_name?: string
    sku_id: number
    sku_name: string
    qty: number
    price?: number
  }>
}

export interface LogisticsListResponse {
  items: Logistics[]
  total: number
  page: number
  size: number
}

export interface LogisticsDashboardSummary {
  total_count: number
  pending_count: number
  in_transit_count: number
  signed_count: number
  completed_count: number
  today_new_count: number
}

export interface CreateLogisticsPlanSchema {
  vc_id: number
  orders: {
    tracking_number: string
    items: { sku_id: number; qty: number }[]
    address_info: AddressInfo
  }[]
}

export interface BatchItem {
  sku_id: number
  production_date: string
  receiving_point_id: number
  qty: number
  certificate_filename?: string
}

export interface ConfirmInboundSchema {
  log_id: number
  sn_list: string[]
  batch_items?: BatchItem[]
}

export interface ExpressOrderStatusSchema {
  order_id: number
  target_status: ExpressStatus
  logistics_id: number
}

export const logisticsApi = {
  list: (params?: {
    ids?: number[]
    vc_id?: number
    status?: string
    date_from?: string
    date_to?: string
    tracking_number?: string
    page?: number
    size?: number
  }) => apiClient.get<LogisticsListResponse>('/logistics/list', { params }) as unknown as Promise<LogisticsListResponse>,

  getDetail: (logId: number) =>
    apiClient.get<LogisticsDetail>(`/logistics/${logId}`) as unknown as Promise<LogisticsDetail>,

  createPlan: (data: CreateLogisticsPlanSchema) =>
    apiClient.post<{ success: boolean }>('/logistics/create-plan', data) as unknown as Promise<{ success: boolean }>,

  confirmInbound: (data: ConfirmInboundSchema) =>
    apiClient.post<{ success: boolean }>('/logistics/confirm-inbound', data) as unknown as Promise<{ success: boolean }>,

  updateExpressOrder: (data: {
    order_id: number
    tracking_number: string
    address_info: AddressInfo
  }) => apiClient.put<{ success: boolean }>('/logistics/update-express', data) as unknown as Promise<{ success: boolean }>,

  updateExpressStatus: (data: ExpressOrderStatusSchema) =>
    apiClient.post<{ success: boolean }>('/logistics/update-express-status', data) as unknown as Promise<{ success: boolean }>,

  bulkProgress: (data: {
    order_ids: number[]
    target_status: ExpressStatus
    logistics_id: number
  }) => apiClient.post<{ success: boolean }>('/logistics/bulk-progress', data) as unknown as Promise<{ success: boolean }>,

  getDashboardSummary: () =>
    apiClient.get<LogisticsDashboardSummary>('/logistics/dashboard/summary') as unknown as Promise<LogisticsDashboardSummary>,
}
