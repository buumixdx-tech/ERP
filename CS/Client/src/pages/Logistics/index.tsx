import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Search, X, RefreshCw, Truck, Package, Check, AlertCircle } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { logisticsApi, Logistics, LogisticsDetail, LogisticsStatus, ExpressStatus, ExpressOrder, CreateLogisticsPlanSchema, AddressInfo } from '@/api/endpoints/logistics'
import { vcApi, VirtualContract } from '@/api/endpoints/vc'
import { masterApi, Point } from '@/api/endpoints/master'
import { formatDate } from '@/lib/utils'

const STATUS_COLORS: Record<string, string> = {
  待发货: 'bg-yellow-100 text-yellow-800',
  在途: 'bg-blue-100 text-blue-800',
  签收: 'bg-green-100 text-green-800',
  完成: 'bg-gray-100 text-gray-800',
  取消: 'bg-red-100 text-red-800',
}

function CreateLogisticsDialog({ onSuccess }: { onSuccess: () => void }) {
  const queryClient = useQueryClient()
  const [isOpen, setIsOpen] = useState(false)
  const [formData, setFormData] = useState({
    vc_id: '',
  })

  const { data: vcs } = useQuery({
    queryKey: ['vcs-for-logistics'],
    queryFn: () => vcApi.list({ status: '执行', size: 100 }),
  })

  const createMutation = useMutation({
    mutationFn: () => logisticsApi.createPlan({
      vc_id: parseInt(formData.vc_id),
      orders: [],
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['logistics-list'] })
      setIsOpen(false)
      onSuccess()
    },
  })

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button><Plus className="mr-2 h-4 w-4" />新建物流任务</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>新建物流任务</DialogTitle>
        </DialogHeader>
        <form onSubmit={(e) => { e.preventDefault(); createMutation.mutate() }} className="space-y-4">
          <div className="space-y-2">
            <Label>关联虚拟合同</Label>
            <Select value={formData.vc_id} onValueChange={(v) => setFormData({ ...formData, vc_id: v })}>
              <SelectTrigger>
                <SelectValue placeholder="选择合同" />
              </SelectTrigger>
              <SelectContent>
                {vcs?.items?.map(vc => (
                  <SelectItem key={vc.id} value={String(vc.id)}>
                    VC-{vc.id} - {vc.description?.slice(0, 30) || '无描述'}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => setIsOpen(false)}>取消</Button>
            <Button type="submit" disabled={!formData.vc_id || createMutation.isPending}>
              {createMutation.isPending ? '创建中...' : '创建'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}

interface ExpressOrderDraft {
  tracking_number: string
  items: { sku_id: number; sku_name: string; qty: number }[]
  receiving_point_id: number
  receiving_point_name: string
  receiving_address: string
  receiving_phone: string
  shipping_point_id: number
  shipping_point_name: string
  shipping_address: string
  shipping_phone: string
}

function CreateExpressOrdersDialog({ logistics, onSuccess }: { logistics: Logistics; onSuccess: () => void }) {
  const queryClient = useQueryClient()
  const [isOpen, setIsOpen] = useState(false)
  const [orders, setOrders] = useState<ExpressOrderDraft[]>([])
  const { toast } = { toast: (t: { title: string; variant?: string }) => {} } // placeholder

  const { data: points } = useQuery({
    queryKey: ['points-for-logistics'],
    queryFn: () => masterApi.points.list({ size: 500 }),
  })

  const { data: detail } = useQuery({
    queryKey: ['logistics-detail', logistics.id],
    queryFn: () => logisticsApi.getDetail(logistics.id),
    enabled: isOpen,
  })

  const createMutation = useMutation({
    mutationFn: async () => {
      const payload: CreateLogisticsPlanSchema = {
        vc_id: logistics.virtual_contract_id,
        orders: orders.filter(o => o.tracking_number).map(order => ({
          tracking_number: order.tracking_number,
          items: order.items.map(i => ({ sku_id: i.sku_id, qty: i.qty })),
          address_info: {
            收货点位Id: order.receiving_point_id,
            收货点位名称: order.receiving_point_name,
            收货地址: order.receiving_address,
            收货联系电话: order.receiving_phone,
            发货点位Id: order.shipping_point_id,
            发货点位名称: order.shipping_point_name,
            发货地址: order.shipping_address,
            发货联系电话: order.shipping_phone,
          },
        })),
      }
      return logisticsApi.createPlan(payload)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['logistics-list'] })
      queryClient.invalidateQueries({ queryKey: ['logistics-detail', logistics.id] })
      setIsOpen(false)
      onSuccess()
    },
  })

  const initializeOrders = () => {
    if (!detail?.elements || !detail?.vc_type) return

    const vcType = detail.vc_type
    let grouped: Record<string, typeof detail.elements> = {}

    if (vcType === 'MATERIAL_SUPPLY') {
      // Group by (shipping_point_id, receiving_point_id)
      detail.elements.forEach(el => {
        const spId = el.shipping_point_id || 0
        const rpId = el.receiving_point_id
        const key = `${spId}-${rpId}`
        if (!grouped[key]) grouped[key] = []
        grouped[key].push(el)
      })
    } else if (vcType === 'RETURN') {
      // Group by (shipping_point_name, receiving_point_name)
      detail.elements.forEach(el => {
        const spName = el.shipping_point_name || '未知'
        const rpName = el.receiving_point_name || '默认'
        const key = `${spName}|${rpName}`
        if (!grouped[key]) grouped[key] = []
        grouped[key].push(el)
      })
    } else {
      // EQUIPMENT_PROCUREMENT, STOCK_PROCUREMENT, MATERIAL_PROCUREMENT: group by receiving_point_id
      detail.elements.forEach(el => {
        const key = String(el.receiving_point_id)
        if (!grouped[key]) grouped[key] = []
        grouped[key].push(el)
      })
    }

    const newOrders: ExpressOrderDraft[] = Object.entries(grouped).map(([groupKey, els], idx) => {
      let receiving_point_id = 0
      let receiving_point_name = ''
      let receiving_address = ''
      let receiving_phone = ''
      let shipping_point_id = 0
      let shipping_point_name = ''
      let shipping_address = ''
      let shipping_phone = ''

      if (vcType === 'MATERIAL_SUPPLY') {
        const [spId, rpId] = groupKey.split('-').map(Number)
        receiving_point_id = rpId
        const rpPoint = points?.items?.find(p => p.id === rpId)
        receiving_point_name = rpPoint?.name || els[0]?.receiving_point_name || ''
        receiving_address = rpPoint?.address || ''
        receiving_phone = ''
        shipping_point_id = spId
        const spPoint = points?.items?.find(p => p.id === spId)
        shipping_point_name = spPoint?.name || els[0]?.shipping_point_name || ''
        shipping_address = spPoint?.address || ''
        shipping_phone = ''
      } else if (vcType === 'RETURN') {
        const [spName, rpName] = groupKey.split('|')
        shipping_point_name = spName
        receiving_point_name = rpName
        const spPoint = points?.items?.find(p => p.name === spName)
        if (spPoint) {
          shipping_point_id = spPoint.id
          shipping_address = spPoint.address || ''
          shipping_phone = ''
        } else {
          shipping_address = ''
          shipping_phone = ''
        }
        const rpPoint = points?.items?.find(p => p.name === rpName)
        if (rpPoint) {
          receiving_point_id = rpPoint.id
          receiving_address = rpPoint.address || ''
          receiving_phone = ''
        } else {
          receiving_address = ''
          receiving_phone = ''
        }
      } else {
        receiving_point_id = parseInt(groupKey)
        const rpPoint = points?.items?.find(p => p.id === receiving_point_id)
        receiving_point_name = rpPoint?.name || els[0]?.receiving_point_name || ''
        receiving_address = rpPoint?.address || ''
        receiving_phone = ''
        if (vcType === 'MATERIAL_PROCUREMENT' && els[0]?.shipping_point_id) {
          shipping_point_id = els[0].shipping_point_id!
          const spPoint = points?.items?.find(p => p.id === shipping_point_id)
          shipping_point_name = spPoint?.name || els[0]?.shipping_point_name || ''
          shipping_address = spPoint?.address || ''
          shipping_phone = ''
        }
      }

      return {
        tracking_number: `${vcType === 'RETURN' ? 'RET' : 'EXP'}-${Date.now().toString().slice(-6)}${idx}`,
        items: els.map(el => ({
          sku_id: el.sku_id,
          sku_name: el.sku_name || `SKU-${el.sku_id}`,
          qty: el.qty,
        })),
        receiving_point_id,
        receiving_point_name,
        receiving_address,
        receiving_phone,
        shipping_point_id,
        shipping_point_name,
        shipping_address,
        shipping_phone,
      }
    })

    setOrders(newOrders)
  }

  const updateOrderTracking = (idx: number, tracking: string) => {
    const updated = [...orders]
    updated[idx] = { ...updated[idx], tracking_number: tracking }
    setOrders(updated)
  }

  const updateOrderPoint = (idx: number, field: 'receiving_point_id' | 'receiving_point_name' | 'receiving_address' | 'receiving_phone', value: string) => {
    const updated = [...orders]
    const point = points?.items?.find(p => p.id === parseInt(value))
    if (field === 'receiving_point_id' && point) {
      updated[idx] = {
        ...updated[idx],
        receiving_point_id: parseInt(value),
        receiving_point_name: point.name,
        receiving_address: point.address || '',
        receiving_phone: '',
      }
    } else {
      updated[idx] = { ...updated[idx], [field]: value }
    }
    setOrders(updated)
  }

  const removeOrder = (idx: number) => {
    setOrders(orders.filter((_, i) => i !== idx))
  }

  const openWithData = () => {
    initializeOrders()
    setIsOpen(true)
  }

  return (
    <Dialog open={isOpen} onOpenChange={(open) => { setIsOpen(open); if (!open) setOrders([]) }}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" onClick={openWithData}>
          <Truck className="mr-2 h-4 w-4" />生成快递单
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>生成快递单</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">
            系统已根据合同明细自动分组，您可手动编辑快递单号、收货点位等信息
          </p>

          <div className="space-y-4">
            {orders.map((order, idx) => (
              <Card key={idx}>
                <CardContent className="pt-4">
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <Label className="text-base">快递单 #{idx + 1}</Label>
                      <Button type="button" variant="ghost" size="sm" onClick={() => removeOrder(idx)}>
                        <X className="h-4 w-4" />
                      </Button>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label className="text-xs">快递单号</Label>
                        <Input
                          value={order.tracking_number}
                          onChange={(e) => updateOrderTracking(idx, e.target.value)}
                          placeholder="输入快递单号"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label className="text-xs">收货点位</Label>
                        <Select
                          value={String(order.receiving_point_id)}
                          onValueChange={(v) => updateOrderPoint(idx, 'receiving_point_id', v)}
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="选择收货点位" />
                          </SelectTrigger>
                          <SelectContent>
                            {points?.items?.map(p => (
                              <SelectItem key={p.id} value={String(p.id)}>{p.name}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label className="text-xs">收货地址</Label>
                        <Input
                          value={order.receiving_address}
                          onChange={(e) => updateOrderPoint(idx, 'receiving_address', e.target.value)}
                          placeholder="收货地址"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label className="text-xs">联系电话</Label>
                        <Input
                          value={order.receiving_phone}
                          onChange={(e) => updateOrderPoint(idx, 'receiving_phone', e.target.value)}
                          placeholder="联系电话"
                        />
                      </div>
                    </div>
                    <div>
                      <Label className="text-xs mb-1 block">物品明细</Label>
                      <div className="bg-gray-50 rounded-md p-2 text-sm space-y-1">
                        {order.items.map((item, i) => (
                          <div key={i} className="flex justify-between">
                            <span>{item.sku_name}</span>
                            <span className="text-muted-foreground">x{item.qty}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {orders.length === 0 && (
            <div className="text-center py-8 text-muted-foreground">
              暂无快递单数据
            </div>
          )}

          <div className="flex justify-between">
            <Button
              type="button"
              variant="outline"
              onClick={initializeOrders}
              disabled={!detail?.elements}
            >
              重新生成
            </Button>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setIsOpen(false)}>取消</Button>
              <Button
                onClick={() => createMutation.mutate()}
                disabled={orders.length === 0 || orders.every(o => !o.tracking_number) || createMutation.isPending}
              >
                {createMutation.isPending ? '生成中...' : `确认生成 (${orders.filter(o => o.tracking_number).length})`}
              </Button>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}

function BulkProgressButton({ logistics, expressOrders }: { logistics: Logistics; expressOrders: ExpressOrder[] }) {
  const queryClient = useQueryClient()

  const statuses = expressOrders.map(o => o.status).filter((v, i, a) => a.indexOf(v) === i)
  const canProgress = statuses.length === 1 && statuses[0] !== '签收'

  const nextStatusMap: Record<string, ExpressStatus> = {
    待发货: '在途',
    在途: '签收',
  }

  const progressMutation = useMutation({
    mutationFn: () => logisticsApi.bulkProgress({
      order_ids: expressOrders.filter(o => o.status !== '签收').map(o => o.id),
      target_status: nextStatusMap[statuses[0]] || '在途',
      logistics_id: logistics.id,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['logistics-list'] })
      queryClient.invalidateQueries({ queryKey: ['logistics-detail', logistics.id] })
    },
  })

  if (!canProgress) return null

  const nextStatusLabel: Record<string, string> = {
    在途: '发货',
    签收: '签收',
  }

  return (
    <Button size="sm" onClick={() => progressMutation.mutate()} disabled={progressMutation.isPending}>
      批量{nextStatusLabel[nextStatusMap[statuses[0]]]}
    </Button>
  )
}

function ConfirmInboundDialog({ logistics, onSuccess }: { logistics: Logistics & { vc_type?: string }; onSuccess: () => void }) {
  const queryClient = useQueryClient()
  const [isOpen, setIsOpen] = useState(false)
  const [snList, setSnList] = useState('')
  const [snError, setSnError] = useState('')
  const [batchItems, setBatchItems] = useState<{
    sku_id: string
    production_date: string
    receiving_point_id: string
    qty: string
    certificate_filename: string
  }[]>([])

  const isMaterialProcurement = logistics.vc_type === 'MATERIAL_PROCUREMENT'

  const { data: points } = useQuery({
    queryKey: ['points'],
    queryFn: () => masterApi.points.list({ size: 100 }),
    enabled: isMaterialProcurement && isOpen,
  })

  const { data: skus } = useQuery({
    queryKey: ['skus'],
    queryFn: () => masterApi.skus.list({ size: 100 }),
    enabled: isMaterialProcurement && isOpen,
  })

  const validateSnList = (input: string): string[] => {
    const sns = input.split(',').map(s => s.trim()).filter(Boolean)
    const duplicates = sns.filter((s, i) => sns.indexOf(s) !== i)
    if (duplicates.length > 0) {
      return [`重复的序列号: ${[...new Set(duplicates)].join(', ')}`]
    }
    return []
  }

  const confirmMutation = useMutation({
    mutationFn: () => {
      if (isMaterialProcurement) {
        return logisticsApi.confirmInbound({
          log_id: logistics.id,
          sn_list: [],
          batch_items: batchItems.filter(i => i.sku_id).map(item => ({
            sku_id: parseInt(item.sku_id),
            production_date: item.production_date,
            receiving_point_id: parseInt(item.receiving_point_id),
            qty: parseFloat(item.qty),
            certificate_filename: item.certificate_filename || undefined,
          })),
        })
      } else {
        const sns = snList.split(',').map(s => s.trim()).filter(Boolean)
        return logisticsApi.confirmInbound({
          log_id: logistics.id,
          sn_list: sns,
        })
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['logistics-list'] })
      queryClient.invalidateQueries({ queryKey: ['logistics-detail', logistics.id] })
      setIsOpen(false)
      setSnList('')
      setSnError('')
      setBatchItems([])
      onSuccess()
    },
  })

  const handleSnChange = (value: string) => {
    setSnList(value)
    const errors = validateSnList(value)
    setSnError(errors.length > 0 ? errors[0] : '')
  }

  const addBatchItem = () => {
    setBatchItems([...batchItems, {
      sku_id: '',
      production_date: '',
      receiving_point_id: '',
      qty: '',
      certificate_filename: '',
    }])
  }

  const updateBatchItem = (index: number, field: string, value: string) => {
    const updated = [...batchItems]
    updated[index] = { ...updated[index], [field]: value }
    setBatchItems(updated)
  }

  return (
    <Dialog open={isOpen} onOpenChange={(open) => { setIsOpen(open); if (!open) { setSnList(''); setSnError(''); setBatchItems([]) } }}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" className="text-green-600">
          <Check className="mr-2 h-4 w-4" />入库确认
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>入库确认 {isMaterialProcurement ? '(物料采购)' : '(设备采购)'}</DialogTitle>
        </DialogHeader>

        {!isMaterialProcurement && (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>设备序列号</Label>
              <Textarea
                placeholder="输入SN序列号，多个用逗号分隔"
                value={snList}
                onChange={(e) => handleSnChange(e.target.value)}
              />
              {snError && (
                <div className="flex items-center gap-2 text-sm text-red-600">
                  <AlertCircle className="h-4 w-4" />
                  {snError}
                </div>
              )}
              <p className="text-sm text-muted-foreground">
                请输入设备序列号，每行一个或用逗号分隔
              </p>
            </div>
            <div className="flex justify-end gap-2">
              <Button
                onClick={() => confirmMutation.mutate()}
                disabled={!snList.trim() || !!snError || confirmMutation.isPending}
              >
                {confirmMutation.isPending ? '确认中...' : '确认入库'}
              </Button>
            </div>
          </div>
        )}

        {isMaterialProcurement && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <Label>批次明细</Label>
              <Button type="button" size="sm" variant="outline" onClick={addBatchItem}>
                <Plus className="mr-2 h-4 w-4" />添加批次
              </Button>
            </div>
            {batchItems.map((item, idx) => (
              <Card key={idx}>
                <CardContent className="pt-4">
                  <div className="grid grid-cols-5 gap-3">
                    <div className="space-y-2">
                      <Label className="text-xs">SKU</Label>
                      <Select value={item.sku_id} onValueChange={(v) => updateBatchItem(idx, 'sku_id', v)}>
                        <SelectTrigger>
                          <SelectValue placeholder="选择SKU" />
                        </SelectTrigger>
                        <SelectContent>
                          {skus?.items?.map(s => (
                            <SelectItem key={s.id} value={String(s.id)}>{s.name}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label className="text-xs">生产日期</Label>
                      <Input type="date" value={item.production_date} onChange={(e) => updateBatchItem(idx, 'production_date', e.target.value)} />
                    </div>
                    <div className="space-y-2">
                      <Label className="text-xs">收货点</Label>
                      <Select value={item.receiving_point_id} onValueChange={(v) => updateBatchItem(idx, 'receiving_point_id', v)}>
                        <SelectTrigger>
                          <SelectValue placeholder="选择" />
                        </SelectTrigger>
                        <SelectContent>
                          {points?.items?.map(p => (
                            <SelectItem key={p.id} value={String(p.id)}>{p.name}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label className="text-xs">数量</Label>
                      <Input type="number" value={item.qty} onChange={(e) => updateBatchItem(idx, 'qty', e.target.value)} />
                    </div>
                    <div className="space-y-2">
                      <Label className="text-xs">证书文件</Label>
                      <Input
                        value={item.certificate_filename}
                        onChange={(e) => updateBatchItem(idx, 'certificate_filename', e.target.value)}
                        placeholder="选填"
                      />
                    </div>
                  </div>
                  <div className="flex justify-end mt-2">
                    <Button type="button" variant="ghost" size="sm" onClick={() => setBatchItems(batchItems.filter((_, i) => i !== idx))}>
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
            {batchItems.length === 0 && (
              <div className="text-center py-4 text-muted-foreground">
                点击"添加批次"添加物料批次
              </div>
            )}
            <div className="flex justify-end gap-2">
              <Button
                onClick={() => confirmMutation.mutate()}
                disabled={batchItems.length === 0 || batchItems.some(i => !i.sku_id || !i.qty) || confirmMutation.isPending}
              >
                {confirmMutation.isPending ? '确认中...' : '确认入库'}
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}

function LogisticsDetailDialog({ logistics, onClose }: { logistics: Logistics; onClose: () => void }) {
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState('orders')
  const [editingOrder, setEditingOrder] = useState<ExpressOrder | null>(null)
  const [trackingNumber, setTrackingNumber] = useState('')

  const { data: detail, isLoading } = useQuery({
    queryKey: ['logistics-detail', logistics.id],
    queryFn: () => logisticsApi.getDetail(logistics.id),
  })

  const updateStatusMutation = useMutation({
    mutationFn: ({ orderId, status }: { orderId: number; status: ExpressStatus }) =>
      logisticsApi.updateExpressStatus({ order_id: orderId, target_status: status, logistics_id: logistics.id }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['logistics-detail', logistics.id] })
    },
  })

  const updateTrackingMutation = useMutation({
    mutationFn: ({ orderId, tracking }: { orderId: number; tracking: string }) =>
      logisticsApi.updateExpressOrder({
        order_id: orderId,
        tracking_number: tracking,
        address_info: editingOrder?.address_info || {
          收货点位Id: 0,
          收货点位名称: '',
          收货地址: '',
          收货联系电话: '',
          发货点位Id: 0,
          发货点位名称: '',
          发货地址: '',
          发货联系电话: '',
        },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['logistics-detail', logistics.id] })
      setEditingOrder(null)
      setTrackingNumber('')
    },
  })

  const expressOrders = detail?.express_orders || []

  return (
    <Dialog open onOpenChange={() => onClose()}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <span>物流任务-{logistics.id}</span>
            <Badge className={STATUS_COLORS[detail?.status || logistics.status]}>
              {detail?.status || logistics.status}
            </Badge>
          </DialogTitle>
        </DialogHeader>

        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList>
            <TabsTrigger value="orders">快递单 ({expressOrders.length})</TabsTrigger>
            <TabsTrigger value="elements">合同明细</TabsTrigger>
          </TabsList>

          <TabsContent value="orders" className="space-y-4">
            {isLoading ? (
              <div className="text-center py-4">加载中...</div>
            ) : expressOrders.length > 0 ? (
              <>
                <div className="flex justify-between items-center">
                  <BulkProgressButton logistics={logistics} expressOrders={expressOrders} />
                </div>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>快递单号</TableHead>
                      <TableHead>状态</TableHead>
                      <TableHead>收货人</TableHead>
                      <TableHead>收货地址</TableHead>
                      <TableHead>物品</TableHead>
                      <TableHead>操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {expressOrders.map(order => (
                      <TableRow key={order.id}>
                        <TableCell className="font-medium">
                          {editingOrder?.id === order.id ? (
                            <div className="flex gap-2">
                              <Input
                                value={trackingNumber}
                                onChange={(e) => setTrackingNumber(e.target.value)}
                                className="w-40"
                              />
                              <Button size="sm" onClick={() => updateTrackingMutation.mutate({ orderId: order.id, tracking: trackingNumber })}>
                                保存
                              </Button>
                            </div>
                          ) : (
                            order.tracking_number
                          )}
                        </TableCell>
                        <TableCell>
                          <Badge className={STATUS_COLORS[order.status]}>{order.status}</Badge>
                        </TableCell>
                        <TableCell>{order.address_info?.收货点位名称 || '-'}</TableCell>
                        <TableCell className="max-w-[200px] truncate">
                          {order.address_info?.收货地址 || '-'}
                        </TableCell>
                        <TableCell>
                          <div className="text-sm">
                            {order.items?.map((item, idx) => (
                              <div key={idx}>{item.sku_name} x{item.qty}</div>
                            ))}
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex gap-2">
                            {order.status === '待发货' && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => {
                                  setEditingOrder(order)
                                  setTrackingNumber(order.tracking_number)
                                }}
                              >
                                编辑单号
                              </Button>
                            )}
                            {order.status === '待发货' && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => updateStatusMutation.mutate({ orderId: order.id, status: '在途' })}
                              >
                                发货
                              </Button>
                            )}
                            {order.status === '在途' && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => updateStatusMutation.mutate({ orderId: order.id, status: '签收' })}
                              >
                                签收
                              </Button>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </>
            ) : (
              <div className="text-center py-4 text-muted-foreground">
                暂无快递单
              </div>
            )}
          </TabsContent>

          <TabsContent value="elements" className="space-y-4">
            {detail?.elements && detail.elements.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>SKU</TableHead>
                    <TableHead>收货点</TableHead>
                    <TableHead className="text-right">数量</TableHead>
                    <TableHead className="text-right">单价</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {detail.elements.map((el, idx) => (
                    <TableRow key={idx}>
                      <TableCell>{el.sku_name}</TableCell>
                      <TableCell>{el.receiving_point_name}</TableCell>
                      <TableCell className="text-right">{el.qty}</TableCell>
                      <TableCell className="text-right">{el.price}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <div className="text-center py-4 text-muted-foreground">无明细数据</div>
            )}
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  )
}

export function LogisticsPage() {
  const [statusFilter, setStatusFilter] = useState<LogisticsStatus | 'ALL'>('ALL')
  const [selectedLogistics, setSelectedLogistics] = useState<Logistics | null>(null)

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['logistics-list', statusFilter],
    queryFn: () => logisticsApi.list({
      status: statusFilter !== 'ALL' ? statusFilter : undefined,
      size: 100,
    }),
  })

  const { data: summary } = useQuery({
    queryKey: ['logistics-summary'],
    queryFn: () => logisticsApi.getDashboardSummary(),
  })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">物流管理</h2>
        <CreateLogisticsDialog onSuccess={() => refetch()} />
      </div>

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-5 gap-4">
          <Card>
            <CardContent className="pt-4">
              <div className="text-2xl font-bold">{summary.total_count}</div>
              <p className="text-sm text-muted-foreground">总任务</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4">
              <div className="text-2xl font-bold text-yellow-600">{summary.pending_count}</div>
              <p className="text-sm text-muted-foreground">待发货</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4">
              <div className="text-2xl font-bold text-blue-600">{summary.in_transit_count}</div>
              <p className="text-sm text-muted-foreground">在途</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4">
              <div className="text-2xl font-bold text-green-600">{summary.signed_count}</div>
              <p className="text-sm text-muted-foreground">已签收</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4">
              <div className="text-2xl font-bold text-gray-600">{summary.completed_count}</div>
              <p className="text-sm text-muted-foreground">已完成</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-4 flex-wrap">
        <Select value={statusFilter} onValueChange={(v) => setStatusFilter(v as LogisticsStatus | 'ALL')}>
          <SelectTrigger className="w-32">
            <SelectValue placeholder="状态" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="ALL">全部</SelectItem>
            <SelectItem value="待发货">待发货</SelectItem>
            <SelectItem value="在途">在途</SelectItem>
            <SelectItem value="签收">已签收</SelectItem>
            <SelectItem value="完成">已完成</SelectItem>
          </SelectContent>
        </Select>
        <Button variant="outline" onClick={() => refetch()}>
          <RefreshCw className="h-4 w-4" />
        </Button>
      </div>

      {/* Logistics List */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>关联合同</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>快递单数量</TableHead>
                <TableHead>创建时间</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data?.items?.map(log => (
                <TableRow key={log.id}>
                  <TableCell className="font-medium">LOG-{log.id}</TableCell>
                  <TableCell>
                    <Badge variant="outline">VC-{log.virtual_contract_id}</Badge>
                  </TableCell>
                  <TableCell>
                    <Badge className={STATUS_COLORS[log.status]}>{log.status}</Badge>
                  </TableCell>
                  <TableCell>{log.express_orders?.length || 0}</TableCell>
                  <TableCell>{formatDate(log.created_at || '')}</TableCell>
                  <TableCell>
                    <div className="flex gap-2">
                      <Button variant="ghost" size="sm" onClick={() => setSelectedLogistics(log)}>
                        详情
                      </Button>
                      {log.status !== '签收' && log.status !== '完成' && log.status !== '取消' && (
                        <CreateExpressOrdersDialog logistics={log} onSuccess={() => refetch()} />
                      )}
                      {log.status === '签收' && (
                        <ConfirmInboundDialog logistics={log} onSuccess={() => refetch()} />
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
              {!data?.items?.length && (
                <TableRow>
                  <TableCell colSpan={6} className="text-center text-muted-foreground">
                    {isLoading ? '加载中...' : '暂无数据'}
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {selectedLogistics && (
        <LogisticsDetailDialog logistics={selectedLogistics} onClose={() => setSelectedLogistics(null)} />
      )}
    </div>
  )
}
