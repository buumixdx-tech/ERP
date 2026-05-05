import { useState, useEffect } from 'react'
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
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import {
  logisticsApi, Logistics, LogisticsDetail, LogisticsStatus, ExpressStatus, ExpressOrder,
  CreateLogisticsPlanSchema, AddressInfo,
  ExpressOrderGlobalItem, ExpressOrderGlobalParams,
  LogisticsGlobalItem, LogisticsGlobalParams,
} from '@/api/endpoints/logistics'
import { vcApi } from '@/api/endpoints/vc'
import { masterApi } from '@/api/endpoints/master'
import { formatDate } from '@/lib/utils'

const STATUS_COLORS: Record<string, string> = {
  待发货: 'bg-yellow-100 text-yellow-800',
  在途: 'bg-blue-100 text-blue-800',
  签收: 'bg-green-100 text-green-800',
  完成: 'bg-gray-100 text-gray-800',
  取消: 'bg-red-100 text-red-800',
}

// =============================================================================
// Create Logistics Dialog
// =============================================================================
function CreateLogisticsDialog({ onSuccess }: { onSuccess: () => void }) {
  const queryClient = useQueryClient()
  const [isOpen, setIsOpen] = useState(false)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [formData, setFormData] = useState({ vc_id: '' })

  const { data: vcs } = useQuery({
    queryKey: ['vcs-for-logistics'],
    queryFn: () => vcApi.list({ status: '执行', size: 100 }),
  })

  const createMutation = useMutation({
    mutationFn: () => logisticsApi.createPlan({ vc_id: parseInt(formData.vc_id), orders: [] }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['logistics-list'] })
      setIsOpen(false)
      setFormData({ vc_id: '' })
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
        <form onSubmit={(e) => { e.preventDefault(); setConfirmOpen(true) }} className="space-y-4">
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
            <Button type="button" disabled={!formData.vc_id || createMutation.isPending} onClick={() => setConfirmOpen(true)}>
              创建
            </Button>
          </div>
          <ConfirmDialog
            open={confirmOpen}
            onOpenChange={setConfirmOpen}
            title="确认创建物流任务"
            description={`将为 VC-${formData.vc_id} 创建一个新的物流任务，确定继续？`}
            confirmLabel="创建"
            onConfirm={() => { setConfirmOpen(false); createMutation.mutate() }}
            isPending={createMutation.isPending}
          />
        </form>
      </DialogContent>
    </Dialog>
  )
}

// =============================================================================
// Create Express Orders Dialog
// =============================================================================
function CreateExpressOrdersDialog({ logistics, onSuccess }: { logistics: Logistics; onSuccess: () => void }) {
  const queryClient = useQueryClient()
  const [isOpen, setIsOpen] = useState(false)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [orders, setOrders] = useState<ExpressOrderDraft[]>([])

  const { data: points } = useQuery({
    queryKey: ['points-for-logistics'],
    queryFn: () => masterApi.points.list({ size: 100 }),
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
      setOrders([])
      onSuccess()
    },
  })

  const initializeOrders = () => {
    if (!detail?.elements || !detail?.vc_type) return
    const vcType = detail.vc_type
    let grouped: Record<string, typeof detail.elements> = {}

    if (vcType === 'MATERIAL_SUPPLY') {
      detail.elements.forEach(el => {
        const key = `${el.shipping_point_id || 0}-${el.receiving_point_id}`
        if (!grouped[key]) grouped[key] = []
        grouped[key].push(el)
      })
    } else if (vcType === 'RETURN') {
      detail.elements.forEach(el => {
        const key = `${el.shipping_point_name || '未知'}|${el.receiving_point_name || '默认'}`
        if (!grouped[key]) grouped[key] = []
        grouped[key].push(el)
      })
    } else {
      detail.elements.forEach(el => {
        const key = String(el.receiving_point_id)
        if (!grouped[key]) grouped[key] = []
        grouped[key].push(el)
      })
    }

    const newOrders: ExpressOrderDraft[] = Object.entries(grouped).map(([groupKey, els], idx) => {
      let rpId = 0, rpName = '', rpAddr = '', rpPhone = ''
      let spId = 0, spName = '', spAddr = '', spPhone = ''

      if (vcType === 'MATERIAL_SUPPLY') {
        const [sId, rId] = groupKey.split('-').map(Number)
        rpId = rId
        const rp = points?.items?.find(p => p.id === rId)
        rpName = rp?.name || els[0]?.receiving_point_name || ''
        rpAddr = rp?.address || ''
        spId = sId
        const sp = points?.items?.find(p => p.id === sId)
        spName = sp?.name || els[0]?.shipping_point_name || ''
        spAddr = sp?.address || ''
      } else if (vcType === 'RETURN') {
        const [sName, rName] = groupKey.split('|')
        spName = sName
        const sp = points?.items?.find(p => p.name === sName)
        if (sp) { spId = sp.id; spAddr = sp.address || '' }
        rpName = rName
        const rp = points?.items?.find(p => p.name === rName)
        if (rp) { rpId = rp.id; rpAddr = rp.address || '' }
      } else {
        rpId = parseInt(groupKey)
        const rp = points?.items?.find(p => p.id === rpId)
        rpName = rp?.name || els[0]?.receiving_point_name || ''
        rpAddr = rp?.address || ''
        if (vcType === 'MATERIAL_PROCUREMENT' && els[0]?.shipping_point_id) {
          spId = els[0].shipping_point_id!
          const sp = points?.items?.find(p => p.id === spId)
          spName = sp?.name || els[0]?.shipping_point_name || ''
          spAddr = sp?.address || ''
        }
      }

      return {
        tracking_number: `${vcType === 'RETURN' ? 'RET' : 'EXP'}-${Date.now().toString().slice(-6)}${idx}`,
        items: els.map(el => ({ sku_id: el.sku_id, sku_name: el.sku_name || `SKU-${el.sku_id}`, qty: el.qty })),
        receiving_point_id: rpId, receiving_point_name: rpName, receiving_address: rpAddr, receiving_phone: rpPhone,
        shipping_point_id: spId, shipping_point_name: spName, shipping_address: spAddr, shipping_phone: spPhone,
      }
    })
    setOrders(newOrders)
  }

  const updateOrderTracking = (idx: number, tracking: string) => {
    const updated = [...orders]
    updated[idx] = { ...updated[idx], tracking_number: tracking }
    setOrders(updated)
  }

  const updateOrderPoint = (idx: number, field: string, value: string) => {
    const updated = [...orders]
    if (field === 'receiving_point_id' && value) {
      const point = points?.items?.find(p => p.id === parseInt(value))
      updated[idx] = { ...updated[idx], receiving_point_id: parseInt(value), receiving_point_name: point?.name || '', receiving_address: point?.address || '', receiving_phone: '' }
    } else {
      updated[idx] = { ...updated[idx], [field]: value }
    }
    setOrders(updated)
  }

  return (
    <Dialog open={isOpen} onOpenChange={(open) => { setIsOpen(open); if (!open) setOrders([]) }}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" onClick={() => { initializeOrders(); setIsOpen(true) }}>
          <Truck className="mr-2 h-4 w-4" />生成快递单
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>生成快递单</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">系统已根据合同明细自动分组，您可手动编辑快递单号、收货点位等信息</p>
          <div className="space-y-4">
            {orders.map((order, idx) => (
              <Card key={idx}>
                <CardContent className="pt-4">
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <Label className="text-base">快递单 #{idx + 1}</Label>
                      <Button type="button" variant="ghost" size="sm" onClick={() => setOrders(orders.filter((_, i) => i !== idx))}>
                        <X className="h-4 w-4" />
                      </Button>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label className="text-xs">快递单号</Label>
                        <Input value={order.tracking_number} onChange={(e) => updateOrderTracking(idx, e.target.value)} placeholder="输入快递单号" />
                      </div>
                      <div className="space-y-2">
                        <Label className="text-xs">收货点位</Label>
                        <Select value={String(order.receiving_point_id)} onValueChange={(v) => updateOrderPoint(idx, 'receiving_point_id', v)}>
                          <SelectTrigger><SelectValue placeholder="选择收货点位" /></SelectTrigger>
                          <SelectContent>
                            {points?.items?.map(p => (<SelectItem key={p.id} value={String(p.id)}>{p.name}</SelectItem>))}
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label className="text-xs">收货地址</Label>
                        <Input value={order.receiving_address} onChange={(e) => updateOrderPoint(idx, 'receiving_address', e.target.value)} placeholder="收货地址" />
                      </div>
                      <div className="space-y-2">
                        <Label className="text-xs">联系电话</Label>
                        <Input value={order.receiving_phone} onChange={(e) => updateOrderPoint(idx, 'receiving_phone', e.target.value)} placeholder="联系电话" />
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
          {orders.length === 0 && <div className="text-center py-8 text-muted-foreground">暂无快递单数据</div>}
          <div className="flex justify-between">
            <Button type="button" variant="outline" onClick={initializeOrders} disabled={!detail?.elements}>重新生成</Button>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setIsOpen(false)}>取消</Button>
              <Button onClick={() => setConfirmOpen(true)} disabled={orders.length === 0 || orders.every(o => !o.tracking_number) || createMutation.isPending}>
                确认生成 ({orders.filter(o => o.tracking_number).length})
              </Button>
            </div>
          </div>
          <ConfirmDialog
            open={confirmOpen}
            onOpenChange={setConfirmOpen}
            title="确认生成快递单"
            description={`将生成 ${orders.filter(o => o.tracking_number).length} 张快递单，确定继续？`}
            confirmLabel="生成"
            onConfirm={() => { setConfirmOpen(false); createMutation.mutate() }}
            isPending={createMutation.isPending}
          />
        </div>
      </DialogContent>
    </Dialog>
  )
}

interface ExpressOrderDraft {
  tracking_number: string
  items: { sku_id: number; sku_name: string; qty: number }[]
  receiving_point_id: number; receiving_point_name: string; receiving_address: string; receiving_phone: string
  shipping_point_id: number; shipping_point_name: string; shipping_address: string; shipping_phone: string
}

// =============================================================================
// Bulk Progress Button
// =============================================================================
function BulkProgressButton({ logistics, expressOrders }: { logistics: Logistics; expressOrders: ExpressOrder[] }) {
  const queryClient = useQueryClient()
  const [confirmOpen, setConfirmOpen] = useState(false)

  const statuses = expressOrders.map(o => o.status).filter((v, i, a) => a.indexOf(v) === i)
  const canProgress = statuses.length === 1 && statuses[0] !== '签收'

  const nextStatusMap: Record<string, ExpressStatus> = { 待发货: '在途', 在途: '签收' }

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

  const currentStatus = statuses[0]
  const targetStatus = nextStatusMap[currentStatus] || '在途'
  const nextStatusLabel: Record<string, string> = { 在途: '发货', 签收: '签收' }

  return (
    <>
      <Button size="sm" onClick={() => setConfirmOpen(true)} disabled={progressMutation.isPending}>
        批量{nextStatusLabel[nextStatusMap[currentStatus]]}
      </Button>
      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title={`确认批量${nextStatusLabel[nextStatusMap[currentStatus]]}`}
        description={`将对 ${expressOrders.filter(o => o.status !== '签收').length} 张快递单执行批量${nextStatusLabel[nextStatusMap[currentStatus]]}操作，状态将变更为"${targetStatus}"，确定继续？`}
        confirmLabel="确认"
        onConfirm={() => { setConfirmOpen(false); progressMutation.mutate() }}
        isPending={progressMutation.isPending}
      />
    </>
  )
}

// =============================================================================
// Confirm Inbound Dialog
// =============================================================================
function ConfirmInboundDialog({ logistics, onSuccess }: { logistics: Logistics & { vc_type?: string }; onSuccess: () => void }) {
  const queryClient = useQueryClient()
  const [isOpen, setIsOpen] = useState(false)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [snList, setSnList] = useState('')
  const [snError, setSnError] = useState('')
  const [batchItems, setBatchItems] = useState<{ sku_id: string; production_date: string; receiving_point_id: string; qty: string; certificate_filename: string }[]>([])

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
    if (duplicates.length > 0) return [`重复的序列号: ${[...new Set(duplicates)].join(', ')}`]
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
        return logisticsApi.confirmInbound({ log_id: logistics.id, sn_list: sns })
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
                onChange={(e) => { setSnList(e.target.value); setSnError(validateSnList(e.target.value)[0] || '') }}
              />
              {snError && <div className="flex items-center gap-2 text-sm text-red-600"><AlertCircle className="h-4 w-4" />{snError}</div>}
              <p className="text-sm text-muted-foreground">请输入设备序列号，每行一个或用逗号分隔</p>
            </div>
            <div className="flex justify-end gap-2">
              <Button onClick={() => setConfirmOpen(true)} disabled={!snList.trim() || !!snError || confirmMutation.isPending}>
                确认入库
              </Button>
            </div>
          </div>
        )}

        {isMaterialProcurement && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <Label>批次明细</Label>
              <Button type="button" size="sm" variant="outline" onClick={() => setBatchItems([...batchItems, { sku_id: '', production_date: '', receiving_point_id: '', qty: '', certificate_filename: '' }])}>
                <Plus className="mr-2 h-4 w-4" />添加批次
              </Button>
            </div>
            {batchItems.map((item, idx) => (
              <Card key={idx}>
                <CardContent className="pt-4">
                  <div className="grid grid-cols-5 gap-3">
                    <div className="space-y-2">
                      <Label className="text-xs">SKU</Label>
                      <Select value={item.sku_id} onValueChange={(v) => { const u = [...batchItems]; u[idx] = { ...u[idx], sku_id: v }; setBatchItems(u) }}>
                        <SelectTrigger><SelectValue placeholder="选择SKU" /></SelectTrigger>
                        <SelectContent>
                          {skus?.items?.map(s => (<SelectItem key={s.id} value={String(s.id)}>{s.name}</SelectItem>))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label className="text-xs">生产日期</Label>
                      <Input type="date" value={item.production_date} onChange={(e) => { const u = [...batchItems]; u[idx] = { ...u[idx], production_date: e.target.value }; setBatchItems(u) }} />
                    </div>
                    <div className="space-y-2">
                      <Label className="text-xs">收货点</Label>
                      <Select value={item.receiving_point_id} onValueChange={(v) => { const u = [...batchItems]; u[idx] = { ...u[idx], receiving_point_id: v }; setBatchItems(u) }}>
                        <SelectTrigger><SelectValue placeholder="选择" /></SelectTrigger>
                        <SelectContent>
                          {points?.items?.map(p => (<SelectItem key={p.id} value={String(p.id)}>{p.name}</SelectItem>))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label className="text-xs">数量</Label>
                      <Input type="number" value={item.qty} onChange={(e) => { const u = [...batchItems]; u[idx] = { ...u[idx], qty: e.target.value }; setBatchItems(u) }} />
                    </div>
                    <div className="space-y-2">
                      <Label className="text-xs">证书文件</Label>
                      <Input value={item.certificate_filename} onChange={(e) => { const u = [...batchItems]; u[idx] = { ...u[idx], certificate_filename: e.target.value }; setBatchItems(u) }} placeholder="选填" />
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
            {batchItems.length === 0 && <div className="text-center py-4 text-muted-foreground">点击"添加批次"添加物料批次</div>}
            <div className="flex justify-end gap-2">
              <Button onClick={() => setConfirmOpen(true)} disabled={batchItems.length === 0 || batchItems.some(i => !i.sku_id || !i.qty) || confirmMutation.isPending}>
                确认入库
              </Button>
            </div>
          </div>
        )}

        <ConfirmDialog
          open={confirmOpen}
          onOpenChange={setConfirmOpen}
          title="确认入库"
          description={isMaterialProcurement
            ? `将入库 ${batchItems.length} 个物料批次，确认后库存和财务凭证将被更新，确定继续？`
            : `将入库设备 SN：${snList}，确认后库存和财务凭证将被更新，确定继续？`
          }
          confirmLabel="确认入库"
          onConfirm={() => { setConfirmOpen(false); confirmMutation.mutate() }}
          isPending={confirmMutation.isPending}
          destructive
        />
      </DialogContent>
    </Dialog>
  )
}

// =============================================================================
// Logistics Detail Dialog
// =============================================================================
function LogisticsDetailDialog({ logistics, onClose }: { logistics: Logistics; onClose: () => void }) {
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState('orders')
  const [editingOrder, setEditingOrder] = useState<ExpressOrder | null>(null)
  const [trackingNumber, setTrackingNumber] = useState('')
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [pendingOrderId, setPendingOrderId] = useState<number | null>(null)
  const [pendingStatus, setPendingStatus] = useState<ExpressStatus | null>(null)

  const { data: detail, isLoading } = useQuery({
    queryKey: ['logistics-detail', logistics.id],
    queryFn: () => logisticsApi.getDetail(logistics.id),
  })

  const updateStatusMutation = useMutation({
    mutationFn: ({ orderId, status }: { orderId: number; status: ExpressStatus }) =>
      logisticsApi.updateExpressStatus({ order_id: orderId, target_status: status, logistics_id: logistics.id }),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['logistics-detail', logistics.id] }) },
  })

  const updateTrackingMutation = useMutation({
    mutationFn: ({ orderId, tracking }: { orderId: number; tracking: string }) =>
      logisticsApi.updateExpressOrder({
        order_id: orderId, tracking_number: tracking,
        address_info: editingOrder?.address_info || { 收货点位Id: 0, 收货点位名称: '', 收货地址: '', 收货联系电话: '', 发货点位Id: 0, 发货点位名称: '', 发货地址: '', 发货联系电话: '' },
      }),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['logistics-detail', logistics.id] }); setEditingOrder(null); setTrackingNumber('') },
  })

  const expressOrders = detail?.express_orders || []

  return (
    <Dialog open onOpenChange={() => onClose()}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <span>物流任务-{logistics.id}</span>
            <Badge className={STATUS_COLORS[detail?.status || logistics.status]}>{detail?.status || logistics.status}</Badge>
          </DialogTitle>
        </DialogHeader>

        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList>
            <TabsTrigger value="orders">快递单 ({expressOrders.length})</TabsTrigger>
            <TabsTrigger value="elements">合同明细</TabsTrigger>
          </TabsList>

          <TabsContent value="orders" className="space-y-4">
            {isLoading ? (<div className="text-center py-4">加载中...</div>) : expressOrders.length > 0 ? (
              <>
                <div className="flex justify-between items-center">
                  <BulkProgressButton logistics={logistics} expressOrders={expressOrders} />
                  {!isLoading && (detail?.status === '签收' || logistics.status === '签收') && (
                    <ConfirmInboundDialog
                      logistics={{ ...logistics, vc_type: detail?.vc_type }}
                      onSuccess={() => { queryClient.invalidateQueries({ queryKey: ['logistics-detail', logistics.id] }); queryClient.invalidateQueries({ queryKey: ['logistics-list'] }) }}
                    />
                  )}
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
                              <Input value={trackingNumber} onChange={(e) => setTrackingNumber(e.target.value)} className="w-40" />
                              <Button size="sm" onClick={() => updateTrackingMutation.mutate({ orderId: order.id, tracking: trackingNumber })}>保存</Button>
                            </div>
                          ) : order.tracking_number}
                        </TableCell>
                        <TableCell><Badge className={STATUS_COLORS[order.status]}>{order.status}</Badge></TableCell>
                        <TableCell>{order.address_info?.收货点位名称 || '-'}</TableCell>
                        <TableCell className="max-w-[200px] truncate">{order.address_info?.收货地址 || '-'}</TableCell>
                        <TableCell>
                          <div className="text-sm">
                            {order.items?.map((item, idx) => (<div key={idx}>{item.sku_name} x{item.qty}</div>))}
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex gap-2">
                            {order.status === '待发货' && (
                              <Button variant="ghost" size="sm" onClick={() => { setEditingOrder(order); setTrackingNumber(order.tracking_number) }}>
                                编辑单号
                              </Button>
                            )}
                            {order.status === '待发货' && (
                              <Button variant="ghost" size="sm" onClick={() => { setPendingOrderId(order.id); setPendingStatus('在途'); setConfirmOpen(true) }}>
                                发货
                              </Button>
                            )}
                            {order.status === '在途' && (
                              <Button variant="ghost" size="sm" onClick={() => { setPendingOrderId(order.id); setPendingStatus('签收'); setConfirmOpen(true) }}>
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
            ) : (<div className="text-center py-4 text-muted-foreground">暂无快递单</div>)}
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
            ) : (<div className="text-center py-4 text-muted-foreground">无明细数据</div>)}
          </TabsContent>
        </Tabs>

        <ConfirmDialog
          open={confirmOpen}
          onOpenChange={(open) => { setConfirmOpen(open); if (!open) { setPendingOrderId(null); setPendingStatus(null) } }}
          title={`确认${pendingStatus === '在途' ? '发货' : '签收'}`}
          description={`快递单将变更为"${pendingStatus}"，确定继续？`}
          confirmLabel="确认"
          onConfirm={() => {
            if (pendingOrderId && pendingStatus) updateStatusMutation.mutate({ orderId: pendingOrderId, status: pendingStatus })
            setConfirmOpen(false); setPendingOrderId(null); setPendingStatus(null)
          }}
          isPending={updateStatusMutation.isPending}
        />
      </DialogContent>
    </Dialog>
  )
}

// =============================================================================
// Tab 1: 物流列表
// =============================================================================
function LogisticsListWithDetail() {
  const [statusFilter, setStatusFilter] = useState<LogisticsStatus | 'ALL' | '待处理'>('待处理')
  const [selectedLogistics, setSelectedLogistics] = useState<(Logistics & { vc_type?: string }) | null>(null)
  const [page, setPage] = useState(1)

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['logistics-list', statusFilter, page],
    queryFn: () => logisticsApi.list({ status: statusFilter !== 'ALL' ? statusFilter : undefined, page, size: 20 }),
  })

  const { data: summary } = useQuery({
    queryKey: ['logistics-summary'],
    queryFn: () => logisticsApi.getDashboardSummary(),
  })

  useEffect(() => { setPage(1) }, [statusFilter])
  const totalPages = data ? Math.ceil(data.total / data.size) : 0

  return (
    <div className="space-y-4">
      {summary && (
        <div className="grid grid-cols-5 gap-4">
          <Card><CardContent className="pt-4"><div className="text-2xl font-bold">{summary.logistics_summary.total}</div><p className="text-sm text-muted-foreground">总任务</p></CardContent></Card>
          <Card><CardContent className="pt-4"><div className="text-2xl font-bold text-yellow-600">{summary.logistics_summary.pending}</div><p className="text-sm text-muted-foreground">待发货</p></CardContent></Card>
          <Card><CardContent className="pt-4"><div className="text-2xl font-bold text-blue-600">{summary.logistics_summary.transit}</div><p className="text-sm text-muted-foreground">在途</p></CardContent></Card>
          <Card><CardContent className="pt-4"><div className="text-2xl font-bold text-green-600">{summary.logistics_summary.signed}</div><p className="text-sm text-muted-foreground">已签收</p></CardContent></Card>
          <Card><CardContent className="pt-4"><div className="text-2xl font-bold text-gray-600">{summary.logistics_summary.finish}</div><p className="text-sm text-muted-foreground">已完成</p></CardContent></Card>
        </div>
      )}

      <div className="flex gap-4 flex-wrap">
        <Select value={statusFilter} onValueChange={(v) => setStatusFilter(v as typeof statusFilter)}>
          <SelectTrigger className="w-32"><SelectValue placeholder="状态" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="待处理">待处理</SelectItem>
            <SelectItem value="ALL">全部</SelectItem>
            <SelectItem value="待发货">待发货</SelectItem>
            <SelectItem value="在途">在途</SelectItem>
            <SelectItem value="签收">已签收</SelectItem>
            <SelectItem value="完成">已完成</SelectItem>
          </SelectContent>
        </Select>
        <Button variant="outline" onClick={() => refetch()}><RefreshCw className="h-4 w-4" /></Button>
      </div>

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>关联VC</TableHead>
                <TableHead>VC类型</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>快递单数量</TableHead>
                <TableHead>创建时间</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data?.items?.map(log => (
                <LogisticsListRow key={log.id} log={log} onSelect={() => setSelectedLogistics(log as typeof log & { vc_type?: string })} onRefresh={() => refetch()} />
              ))}
              {!data?.items?.length && (
                <TableRow><TableCell colSpan={7} className="text-center text-muted-foreground">{isLoading ? '加载中...' : '暂无数据'}</TableCell></TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <Button variant="outline" size="sm" onClick={() => setPage(p => p - 1)} disabled={page <= 1}>上一页</Button>
          <span className="text-sm text-muted-foreground">第 {page} / {totalPages} 页，共 {data?.total} 条</span>
          <Button variant="outline" size="sm" onClick={() => setPage(p => p + 1)} disabled={page >= totalPages}>下一页</Button>
        </div>
      )}

      {selectedLogistics && (
        <LogisticsDetailDialog logistics={selectedLogistics} onClose={() => setSelectedLogistics(null)} />
      )}
    </div>
  )
}

function LogisticsListRow({ log, onSelect, onRefresh }: { log: Logistics; onSelect: () => void; onRefresh: () => void }) {
  const { data: detail } = useQuery({
    queryKey: ['logistics-detail', log.id],
    queryFn: () => logisticsApi.getDetail(log.id),
    enabled: true,
  })

  return (
    <TableRow>
      <TableCell className="font-medium">LOG-{log.id}</TableCell>
      <TableCell><Badge variant="outline">VC-{log.virtual_contract_id}</Badge></TableCell>
      <TableCell>{detail?.vc_type || '-'}</TableCell>
      <TableCell><Badge className={STATUS_COLORS[log.status]}>{log.status}</Badge></TableCell>
      <TableCell>{log.express_orders_count || 0}</TableCell>
      <TableCell>{formatDate(log.created_at)}</TableCell>
      <TableCell>
        <div className="flex gap-2">
          <Button variant="ghost" size="sm" onClick={onSelect}>详情</Button>
          {log.status === '待发货' && <CreateExpressOrdersDialog logistics={log} onSuccess={onRefresh} />}
          {log.status === '签收' && <ConfirmInboundDialog logistics={log as typeof log & { vc_type?: string }} onSuccess={onRefresh} />}
        </div>
      </TableCell>
    </TableRow>
  )
}

// =============================================================================
// Tab 2: 快递单全局概览
// =============================================================================
function ExpressOrderGlobalTab() {
  const [params, setParams] = useState<ExpressOrderGlobalParams>({ page: 1, size: 20 })
  const [searchCount, setSearchCount] = useState(0)
  const [selected, setSelected] = useState<ExpressOrderGlobalItem | null>(null)

  const buildApiParams = (p: ExpressOrderGlobalParams) => {
    const numFields = ['ids', 'sku_id', 'shipping_point_id', 'receiving_point_id', 'vc_id', 'business_id', 'supply_chain_id']
    const result: Record<string, unknown> = { ...p, size: 20 }
    Object.entries(result).forEach(([k, v]) => {
      if (v === '' || v === undefined) { delete result[k]; return }
      if (numFields.includes(k) && typeof v === 'string') { result[k] = parseInt(v, 10) }
    })
    return result
  }

  const { data: results, isLoading: isSearching, error } = useQuery({
    queryKey: ['logistics-express-global', params, searchCount],
    enabled: searchCount > 0,
    queryFn: () => logisticsApi.getExpressOrdersGlobal(buildApiParams(params)),
  })

  const doSearch = () => { setSelected(null); setSearchCount(c => c + 1) }

  const clearSearch = () => {
    setParams({ page: 1, size: 20 })
    setSelected(null)
  }

  const setParam = (key: keyof ExpressOrderGlobalParams, value: string) => {
    setParams(p => ({ ...p, [key]: value || undefined }))
  }

  const totalPages = results ? Math.ceil(results.total / results.size) : 0

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="pb-2"><CardTitle className="text-base">多条件搜索</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-4 gap-4">
            <div className="space-y-1"><Label className="text-xs">快递单号</Label><Input value={params.tracking_number || ''} onChange={e => setParam('tracking_number', e.target.value)} placeholder="模糊匹配" /></div>
            <div className="space-y-1"><Label className="text-xs">快递单ID</Label><Input type="number" value={params.ids || ''} onChange={e => setParam('ids', e.target.value)} placeholder="ID" /></div>
            <div className="space-y-1"><Label className="text-xs">快递单状态</Label>
              <Select value={params.status || 'ALL'} onValueChange={v => setParam('status', v === 'ALL' ? '' : v)}>
                <SelectTrigger><SelectValue placeholder="全部" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">全部</SelectItem>
                  <SelectItem value="待发货">待发货</SelectItem>
                  <SelectItem value="在途">在途</SelectItem>
                  <SelectItem value="签收">签收</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1"><Label className="text-xs">创建时间起</Label><Input type="date" value={params.date_from || ''} onChange={e => setParam('date_from', e.target.value)} /></div>
            <div className="space-y-1"><Label className="text-xs">创建时间止</Label><Input type="date" value={params.date_to || ''} onChange={e => setParam('date_to', e.target.value)} /></div>
            <div className="space-y-1"><Label className="text-xs">SKU ID</Label><Input type="number" value={params.sku_id || ''} onChange={e => setParam('sku_id', e.target.value)} placeholder="SKU ID" /></div>
            <div className="space-y-1"><Label className="text-xs">SKU名称</Label><Input value={params.sku_name_kw || ''} onChange={e => setParam('sku_name_kw', e.target.value)} placeholder="精确包含" /></div>
            <div className="space-y-1"><Label className="text-xs">发货点位ID</Label><Input type="number" value={params.shipping_point_id || ''} onChange={e => setParam('shipping_point_id', e.target.value)} /></div>
            <div className="space-y-1"><Label className="text-xs">发货点位名称</Label><Input value={params.shipping_point_name_kw || ''} onChange={e => setParam('shipping_point_name_kw', e.target.value)} placeholder="精确包含" /></div>
            <div className="space-y-1"><Label className="text-xs">收货点位ID</Label><Input type="number" value={params.receiving_point_id || ''} onChange={e => setParam('receiving_point_id', e.target.value)} /></div>
            <div className="space-y-1"><Label className="text-xs">收货点位名称</Label><Input value={params.receiving_point_name_kw || ''} onChange={e => setParam('receiving_point_name_kw', e.target.value)} placeholder="精确包含" /></div>
            <div className="space-y-1"><Label className="text-xs">关联VC ID</Label><Input type="number" value={params.vc_id || ''} onChange={e => setParam('vc_id', e.target.value)} /></div>
            <div className="space-y-1"><Label className="text-xs">关联VC类型</Label>
              <Select value={params.vc_type || 'ALL'} onValueChange={v => setParam('vc_type', v === 'ALL' ? '' : v)}>
                <SelectTrigger><SelectValue placeholder="全部" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">全部</SelectItem>
                  <SelectItem value="设备采购">设备采购</SelectItem>
                  <SelectItem value="物料供应">物料供应</SelectItem>
                  <SelectItem value="物料采购">物料采购</SelectItem>
                  <SelectItem value="库存拨付">库存拨付</SelectItem>
                  <SelectItem value="退货">退货</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1"><Label className="text-xs">关联VC状态</Label>
              <Select
                value={(params.vc_status_type && params.vc_status_value) ? `${params.vc_status_type}-${params.vc_status_value}` : 'ALL'}
                onValueChange={v => {
                  if (v === 'ALL') {
                    setParams((p: any) => ({ ...p, vc_status_type: undefined, vc_status_value: undefined }))
                  } else {
                    const [type, val] = v.split('-')
                    setParams((p: any) => ({ ...p, vc_status_type: type, vc_status_value: val }))
                  }
                }}
              >
                <SelectTrigger><SelectValue placeholder="全部" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">全部</SelectItem>
                  <SelectItem value="主状态-执行">主状态-执行</SelectItem>
                  <SelectItem value="主状态-完成">主状态-完成</SelectItem>
                  <SelectItem value="主状态-终止">主状态-终止</SelectItem>
                  <SelectItem value="主状态-取消">主状态-取消</SelectItem>
                  <SelectItem value="合同状态-执行">合同状态-执行</SelectItem>
                  <SelectItem value="合同状态-发货">合同状态-发货</SelectItem>
                  <SelectItem value="合同状态-签收">合同状态-签收</SelectItem>
                  <SelectItem value="合同状态-完成">合同状态-完成</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1"><Label className="text-xs">Business ID</Label><Input type="number" value={params.business_id || ''} onChange={e => setParam('business_id', e.target.value)} /></div>
            <div className="space-y-1"><Label className="text-xs">客户名称</Label><Input value={params.business_customer_name_kw || ''} onChange={e => setParam('business_customer_name_kw', e.target.value)} placeholder="精确包含" /></div>
            <div className="space-y-1"><Label className="text-xs">SupplyChain ID</Label><Input type="number" value={params.supply_chain_id || ''} onChange={e => setParam('supply_chain_id', e.target.value)} /></div>
            <div className="space-y-1"><Label className="text-xs">供应商名称</Label><Input value={params.supply_chain_supplier_name_kw || ''} onChange={e => setParam('supply_chain_supplier_name_kw', e.target.value)} placeholder="精确包含" /></div>
          </div>
          <div className="flex gap-2 ml-auto">
            <Button variant="outline" onClick={clearSearch}>清空</Button>
            <Button onClick={doSearch} disabled={isSearching}>{isSearching ? '搜索中...' : '搜索'}</Button>
          </div>
          {error && <div className="text-sm text-red-600">{error.message}</div>}
        </CardContent>
      </Card>

      {error && !results && (
        <Card><CardContent className="py-4 text-center text-red-600">{typeof error === 'string' ? error : '加载失败'}</CardContent></Card>
      )}

      {results && (
        <>
          <div className="text-sm text-muted-foreground">共 {results.total} 条记录</div>
          <Card>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>快递单号</TableHead>
                    <TableHead>状态</TableHead>
                    <TableHead>创建时间</TableHead>
                    <TableHead>SKU</TableHead>
                    <TableHead>发货点位</TableHead>
                    <TableHead>收货点位</TableHead>
                    <TableHead>物流单ID</TableHead>
                    <TableHead>VC ID</TableHead>
                    <TableHead>VC类型</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {results.items?.map(order => (
                    <TableRow key={order.id} className={selected?.id === order.id ? 'bg-muted' : ''} onClick={() => setSelected(order)}>
                      <TableCell className="font-medium">{order.tracking_number}</TableCell>
                      <TableCell><Badge className={STATUS_COLORS[order.status]}>{order.status}</Badge></TableCell>
                      <TableCell>{formatDate(order.created_at)}</TableCell>
                      <TableCell>{order.items?.map((item, idx) => (<div key={idx}>{item.sku_name} x{item.qty}</div>))}</TableCell>
                      <TableCell>{order.address_info?.发货点位名称 || '-'}</TableCell>
                      <TableCell>{order.address_info?.收货点位名称 || '-'}</TableCell>
                      <TableCell>LOG-{order.logistics_id}</TableCell>
                      <TableCell>{order.vc_id ? `VC-${order.vc_id}` : '-'}</TableCell>
                      <TableCell>{order.vc_type || '-'}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2">
              <Button variant="outline" size="sm" onClick={() => setParams(p => ({ ...p, page: (p.page || 1) - 1 }))} disabled={(params.page || 1) <= 1}>上一页</Button>
              <span className="text-sm text-muted-foreground">第 {params.page} / {totalPages} 页</span>
              <Button variant="outline" size="sm" onClick={() => setParams(p => ({ ...p, page: (p.page || 1) + 1 }))} disabled={(params.page || 1) >= totalPages}>下一页</Button>
            </div>
          )}
        </>
      )}
    </div>
  )
}

// =============================================================================
// Tab 3: 物流全局概览
// =============================================================================
function LogisticsGlobalTab() {
  const [params, setParams] = useState<LogisticsGlobalParams>({ page: 1, size: 20 })
  const [searchCount, setSearchCount] = useState(0)
  const [selected, setSelected] = useState<LogisticsGlobalItem | null>(null)
  const [detailLogistics, setDetailLogistics] = useState<(Logistics & { vc_type?: string }) | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)

  const buildApiParams = (p: LogisticsGlobalParams) => {
    const numFields = ['ids', 'sku_id', 'shipping_point_id', 'receiving_point_id', 'vc_id', 'business_id', 'supply_chain_id', 'express_order_id']
    const result: Record<string, unknown> = { ...p, size: 20 }
    Object.entries(result).forEach(([k, v]) => {
      if (v === '' || v === undefined) { delete result[k]; return }
      if (numFields.includes(k) && typeof v === 'string') { result[k] = parseInt(v, 10) }
    })
    return result
  }

  const { data: results, isLoading: isSearching, error } = useQuery({
    queryKey: ['logistics-global', params, searchCount],
    enabled: searchCount > 0,
    queryFn: () => logisticsApi.getLogisticsGlobal(buildApiParams(params)),
  })

  const doSearch = () => { setSelected(null); setSearchCount(c => c + 1) }

  const clearSearch = () => {
    setParams({ page: 1, size: 20 })
    setSelected(null)
  }

  const setParam = (key: keyof LogisticsGlobalParams, value: string) => {
    setParams(p => ({ ...p, [key]: value || undefined }))
  }

  const totalPages = results ? Math.ceil(results.total / results.size) : 0

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="pb-2"><CardTitle className="text-base">多条件搜索</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-4 gap-4">
            <div className="space-y-1"><Label className="text-xs">物流单ID</Label><Input type="number" value={params.ids || ''} onChange={e => setParam('ids', e.target.value)} placeholder="ID" /></div>
            <div className="space-y-1"><Label className="text-xs">物流单状态</Label>
              <Select value={params.status || 'ALL'} onValueChange={v => setParam('status', v === 'ALL' ? '' : v)}>
                <SelectTrigger><SelectValue placeholder="全部" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">全部</SelectItem>
                  <SelectItem value="待发货">待发货</SelectItem>
                  <SelectItem value="在途">在途</SelectItem>
                  <SelectItem value="签收">已签收</SelectItem>
                  <SelectItem value="完成">已完成</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1"><Label className="text-xs">创建时间起</Label><Input type="date" value={params.date_from || ''} onChange={e => setParam('date_from', e.target.value)} /></div>
            <div className="space-y-1"><Label className="text-xs">创建时间止</Label><Input type="date" value={params.date_to || ''} onChange={e => setParam('date_to', e.target.value)} /></div>
            <div className="space-y-1"><Label className="text-xs">快递单号</Label><Input value={params.tracking_number || ''} onChange={e => setParam('tracking_number', e.target.value)} placeholder="模糊匹配" /></div>
            <div className="space-y-1"><Label className="text-xs">快递单ID</Label><Input type="number" value={params.express_order_id || ''} onChange={e => setParam('express_order_id', e.target.value)} /></div>
            <div className="space-y-1"><Label className="text-xs">SKU ID</Label><Input type="number" value={params.sku_id || ''} onChange={e => setParam('sku_id', e.target.value)} /></div>
            <div className="space-y-1"><Label className="text-xs">SKU名称</Label><Input value={params.sku_name_kw || ''} onChange={e => setParam('sku_name_kw', e.target.value)} placeholder="精确包含" /></div>
            <div className="space-y-1"><Label className="text-xs">发货点位ID</Label><Input type="number" value={params.shipping_point_id || ''} onChange={e => setParam('shipping_point_id', e.target.value)} /></div>
            <div className="space-y-1"><Label className="text-xs">发货点位名称</Label><Input value={params.shipping_point_name_kw || ''} onChange={e => setParam('shipping_point_name_kw', e.target.value)} placeholder="精确包含" /></div>
            <div className="space-y-1"><Label className="text-xs">收货点位ID</Label><Input type="number" value={params.receiving_point_id || ''} onChange={e => setParam('receiving_point_id', e.target.value)} /></div>
            <div className="space-y-1"><Label className="text-xs">收货点位名称</Label><Input value={params.receiving_point_name_kw || ''} onChange={e => setParam('receiving_point_name_kw', e.target.value)} placeholder="精确包含" /></div>
            <div className="space-y-1"><Label className="text-xs">关联VC ID</Label><Input type="number" value={params.vc_id || ''} onChange={e => setParam('vc_id', e.target.value)} /></div>
            <div className="space-y-1"><Label className="text-xs">关联VC类型</Label>
              <Select value={params.vc_type || 'ALL'} onValueChange={v => setParam('vc_type', v === 'ALL' ? '' : v)}>
                <SelectTrigger><SelectValue placeholder="全部" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">全部</SelectItem>
                  <SelectItem value="设备采购">设备采购</SelectItem>
                  <SelectItem value="物料供应">物料供应</SelectItem>
                  <SelectItem value="物料采购">物料采购</SelectItem>
                  <SelectItem value="库存拨付">库存拨付</SelectItem>
                  <SelectItem value="退货">退货</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1"><Label className="text-xs">关联VC状态</Label>
              <Select
                value={(params.vc_status_type && params.vc_status_value) ? `${params.vc_status_type}-${params.vc_status_value}` : 'ALL'}
                onValueChange={v => {
                  if (v === 'ALL') {
                    setParams((p: any) => ({ ...p, vc_status_type: undefined, vc_status_value: undefined }))
                  } else {
                    const [type, val] = v.split('-')
                    setParams((p: any) => ({ ...p, vc_status_type: type, vc_status_value: val }))
                  }
                }}
              >
                <SelectTrigger><SelectValue placeholder="全部" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">全部</SelectItem>
                  <SelectItem value="主状态-执行">主状态-执行</SelectItem>
                  <SelectItem value="主状态-完成">主状态-完成</SelectItem>
                  <SelectItem value="主状态-终止">主状态-终止</SelectItem>
                  <SelectItem value="主状态-取消">主状态-取消</SelectItem>
                  <SelectItem value="合同状态-执行">合同状态-执行</SelectItem>
                  <SelectItem value="合同状态-发货">合同状态-发货</SelectItem>
                  <SelectItem value="合同状态-签收">合同状态-签收</SelectItem>
                  <SelectItem value="合同状态-完成">合同状态-完成</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1"><Label className="text-xs">Business ID</Label><Input type="number" value={params.business_id || ''} onChange={e => setParam('business_id', e.target.value)} /></div>
            <div className="space-y-1"><Label className="text-xs">客户名称</Label><Input value={params.business_customer_name_kw || ''} onChange={e => setParam('business_customer_name_kw', e.target.value)} placeholder="精确包含" /></div>
            <div className="space-y-1"><Label className="text-xs">SupplyChain ID</Label><Input type="number" value={params.supply_chain_id || ''} onChange={e => setParam('supply_chain_id', e.target.value)} /></div>
            <div className="space-y-1"><Label className="text-xs">供应商名称</Label><Input value={params.supply_chain_supplier_name_kw || ''} onChange={e => setParam('supply_chain_supplier_name_kw', e.target.value)} placeholder="精确包含" /></div>
          </div>
          <div className="flex gap-2 ml-auto">
            <Button variant="outline" onClick={clearSearch}>清空</Button>
            <Button onClick={doSearch} disabled={isSearching}>{isSearching ? '搜索中...' : '搜索'}</Button>
          </div>
          {error && <div className="text-sm text-red-600">{error.message}</div>}
        </CardContent>
      </Card>

      {error && !results && (
        <Card><CardContent className="py-4 text-center text-red-600">{typeof error === 'string' ? error : '加载失败'}</CardContent></Card>
      )}

      {results && (
        <>
          <div className="text-sm text-muted-foreground">共 {results.total} 条记录</div>
          <Card>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>ID</TableHead>
                    <TableHead>关联VC</TableHead>
                    <TableHead>VC类型</TableHead>
                    <TableHead>状态</TableHead>
                    <TableHead>快递单数量</TableHead>
                    <TableHead>创建时间</TableHead>
                    <TableHead>操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {results.items?.map(item => (
                    <TableRow key={item.id} className={selected?.id === item.id ? 'bg-muted' : ''}>
                      <TableCell className="font-medium">LOG-{item.id}</TableCell>
                      <TableCell><Badge variant="outline">VC-{item.virtual_contract_id}</Badge></TableCell>
                      <TableCell>{item.vc_type || '-'}</TableCell>
                      <TableCell><Badge className={STATUS_COLORS[item.status]}>{item.status}</Badge></TableCell>
                      <TableCell>{item.express_orders_count}</TableCell>
                      <TableCell>{formatDate(item.created_at)}</TableCell>
                      <TableCell>
                        <Button variant="ghost" size="sm" onClick={() => { setDetailLoading(true); logisticsApi.getDetail(item.id).then(d => { setDetailLogistics(d as Logistics & { vc_type?: string }); setDetailLoading(false) }).catch(() => setDetailLoading(false)) }} disabled={detailLoading}>
                          {detailLoading ? '...' : '详情'}
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2">
              <Button variant="outline" size="sm" onClick={() => setParams(p => ({ ...p, page: (p.page || 1) - 1 }))} disabled={(params.page || 1) <= 1}>上一页</Button>
              <span className="text-sm text-muted-foreground">第 {params.page} / {totalPages} 页</span>
              <Button variant="outline" size="sm" onClick={() => setParams(p => ({ ...p, page: (p.page || 1) + 1 }))} disabled={(params.page || 1) >= totalPages}>下一页</Button>
            </div>
          )}
        </>
      )}

      {detailLogistics && (
        <LogisticsDetailDialog logistics={detailLogistics} onClose={() => setDetailLogistics(null)} />
      )}
    </div>
  )
}

// =============================================================================
// Main Logistics Page
// =============================================================================
export function LogisticsPage() {
  const [activeTab, setActiveTab] = useState<'list' | 'express-global' | 'logistics-global'>('list')

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">物流管理</h2>
        <CreateLogisticsDialog onSuccess={() => {}} />
      </div>

      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as typeof activeTab)}>
        <TabsList>
          <TabsTrigger value="list">物流列表</TabsTrigger>
          <TabsTrigger value="express-global">快递单全局概览</TabsTrigger>
          <TabsTrigger value="logistics-global">物流全局概览</TabsTrigger>
        </TabsList>

        <TabsContent value="list"><LogisticsListWithDetail /></TabsContent>
        <TabsContent value="express-global"><ExpressOrderGlobalTab /></TabsContent>
        <TabsContent value="logistics-global"><LogisticsGlobalTab /></TabsContent>
      </Tabs>
    </div>
  )
}
