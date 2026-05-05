import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Search, X, ChevronRight, Package, Truck, RotateCcw, RefreshCw, Pencil, Trash2 } from 'lucide-react'
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
import { PointSelect, PointOption } from '@/components/ui/point-select'
import { vcApi, VCType, VCStatus, VirtualContract, VCDetailResponse, CashflowProgress, VCListResponse, VCGlobalSearchParams } from '@/api/endpoints/vc'
import { masterApi, Point, SKU } from '@/api/endpoints/master'
import { supplyChainApi } from '@/api/endpoints/supplyChain'
import { formatCurrency, formatDate } from '@/lib/utils'

const VC_TYPE_LABELS: Record<string, string> = {
  设备采购: '设备采购',
  '设备采购(库存)': '库存采购',
  物料采购: '物料采购',
  物料供应: '物料供应',
  库存拨付: '库存拨付',
  退货: '退货',
}

const VC_TYPE_COLORS: Record<string, string> = {
  设备采购: 'bg-blue-100 text-blue-800',
  '设备采购(库存)': 'bg-indigo-100 text-indigo-800',
  物料供应: 'bg-green-100 text-green-800',
  物料采购: 'bg-orange-100 text-orange-800',
  库存拨付: 'bg-purple-100 text-purple-800',
  退货: 'bg-red-100 text-red-800',
}

const STATUS_COLORS: Record<string, string> = {
  // 通用状态
  执行: 'bg-blue-100 text-blue-800',   // 进行中 - 蓝色
  完成: 'bg-green-100 text-green-800', // 完成 - 绿色
  终止: 'bg-red-100 text-red-800',     // 终止 - 红色
  取消: 'bg-gray-100 text-gray-800',    // 取消 - 灰色
  // 主体状态
  发货: 'bg-orange-100 text-orange-800', // 发货 - 橙色
  签收: 'bg-teal-100 text-teal-800',     // 签收 - 青色
  // 资金状态
  预付: 'bg-yellow-100 text-yellow-800',  // 预付 - 黄色
}

type ElementFormState = {
  sku_id: string
  shipping_point_id: string
  receiving_point_id: string
  qty: string
  price: string
  deposit: string
  sn_list: string
}

function VCCreateDialog({ onSuccess }: { onSuccess: () => void }) {
  const queryClient = useQueryClient()
  const [isOpen, setIsOpen] = useState(false)
  const [selectedType, setSelectedType] = useState<VCType | null>(null)
  const [formData, setFormData] = useState({
    business_id: '',
    sc_id: '',
    description: '',
    total_amt: '',
    total_deposit: '',
    prepayment_ratio: '0.3',
    balance_period: '30',
    day_rule: '自然日',
    start_trigger: '入库日',
  })
  const [elements, setElements] = useState<ElementFormState[]>([])
  // 选中供应链后，该供应链约定的 SKU 列表（用于物料采购时过滤 SKU）
  const [scSkuIds, setScSkuIds] = useState<number[]>([])
  // 选中供应链后，默认发货仓库（供应商的仓，id 最小的）
  const [defaultShippingPointId, setDefaultShippingPointId] = useState<string>('')
  const [returnFormData, setReturnFormData] = useState({
    target_vc_id: '',
    return_direction: 'CUSTOMER_TO_US',
    goods_amount: '',
    deposit_amount: '',
    logistics_cost: '',
    logistics_bearer: 'SENDER',
    total_refund: '',
    reason: '',
    description: '',
  })
  const [returnElements, setReturnElements] = useState<{
    original_element_id: string
    sku_id: string
    qty: string
    sn_list: string
  }[]>([])

  const { data: businesses } = useQuery({
    queryKey: ['businesses-for-vc'],
    queryFn: () => masterApi.customers.list({ size: 100 }),
  })

  const { data: supplyChains } = useQuery({
    queryKey: ['supply-chains-for-vc'],
    queryFn: () => supplyChainApi.list({ size: 100 }),
  })

  const { data: points } = useQuery({
    queryKey: ['points-for-vc'],
    queryFn: () => masterApi.points.list({ size: 100 }),
  })

  const { data: skus } = useQuery({
    queryKey: ['skus-for-vc'],
    queryFn: () => masterApi.skus.list({ size: 100 }),
  })

  const { data: vcsForReturn } = useQuery({
    queryKey: ['vcs-for-return'],
    queryFn: () => vcApi.list({ status: '执行', size: 100 }),
  })

  const createMutation = useMutation({
    mutationFn: async () => {
      const totalAmt = parseFloat(formData.total_amt) || 0
      const totalDeposit = parseFloat(formData.total_deposit) || 0
      const payment = {
        prepayment_ratio: parseFloat(formData.prepayment_ratio) || 0,
        balance_period: parseInt(formData.balance_period) || 30,
        day_rule: formData.day_rule,
        start_trigger: formData.start_trigger,
      }

      const vcElements = elements.map(el => ({
        shipping_point_id: parseInt(el.shipping_point_id) || 0,
        receiving_point_id: parseInt(el.receiving_point_id) || 0,
        sku_id: parseInt(el.sku_id),
        qty: parseFloat(el.qty) || 0,
        price: parseFloat(el.price) || 0,
        deposit: parseFloat(el.deposit) || 0,
        subtotal: (parseFloat(el.qty) || 0) * (parseFloat(el.price) || 0),
        sn_list: el.sn_list ? el.sn_list.split(',').map(s => s.trim()).filter(Boolean) : undefined,
      }))

      switch (selectedType) {
        case '设备采购':
          return vcApi.createProcurement({
            business_id: parseInt(formData.business_id),
            sc_id: formData.sc_id ? parseInt(formData.sc_id) : undefined,
            elements: vcElements,
            total_amt: totalAmt,
            total_deposit: totalDeposit,
            payment,
            description: formData.description,
          })
        case '设备采购(库存)':
          return vcApi.createStockProcurement({
            sc_id: parseInt(formData.sc_id),
            elements: vcElements,
            total_amt: totalAmt,
            payment,
            description: formData.description,
          })
        case '物料供应':
          return vcApi.createMaterialSupply({
            business_id: parseInt(formData.business_id),
            elements: vcElements,
            total_amt: totalAmt,
            description: formData.description,
          })
        case '物料采购':
          return vcApi.createMatProcurement({
            sc_id: parseInt(formData.sc_id),
            elements: vcElements,
            total_amt: totalAmt,
            payment,
            description: formData.description,
          })
        case '库存拨付':
          return vcApi.allocateInventory({
            business_id: parseInt(formData.business_id),
            elements: vcElements.map(el => ({
              ...el,
              deposit: 0,
            })),
            description: formData.description,
          })
        case '退货':
          return vcApi.createReturn({
            target_vc_id: parseInt(returnFormData.target_vc_id),
            return_direction: returnFormData.return_direction as 'CUSTOMER_TO_US' | 'US_TO_SUPPLIER',
            elements: returnElements.map(el => ({
              shipping_point_id: 0,
              receiving_point_id: 0,
              sku_id: parseInt(el.sku_id),
              qty: parseFloat(el.qty),
              price: 0,
              deposit: 0,
              subtotal: 0,
              sn_list: el.sn_list ? el.sn_list.split(',').map(s => s.trim()).filter(Boolean) : [],
            })),
            goods_amount: parseFloat(returnFormData.goods_amount) || 0,
            deposit_amount: parseFloat(returnFormData.deposit_amount) || 0,
            logistics_cost: parseFloat(returnFormData.logistics_cost) || 0,
            logistics_bearer: returnFormData.logistics_bearer,
            total_refund: parseFloat(returnFormData.total_refund) || 0,
            reason: returnFormData.reason,
            description: returnFormData.description,
          })
        default:
          throw new Error('Unsupported VC type')
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vc-list'] })
      setIsOpen(false)
      setSelectedType(null)
      onSuccess()
    },
  })

  const addElement = () => {
    setElements([...elements, { sku_id: '', shipping_point_id: defaultShippingPointId, receiving_point_id: '', qty: '', price: '', deposit: '', sn_list: '' }])
  }

  const updateElement = (index: number, field: keyof ElementFormState, value: string) => {
    const updated = [...elements]
    updated[index] = { ...updated[index], [field]: value }

    // Auto-fill price from supply chain when SKU is selected
    if (field === 'sku_id' && formData.sc_id) {
      const sc = supplyChains?.items?.find(s => s.id === parseInt(formData.sc_id))
      const skuItem = sc?.items?.find((i: any) => i.sku_id === parseInt(value))
      if (skuItem?.price !== undefined) {
        updated[index].price = String(skuItem.price)
      }
    }

    setElements(updated)
  }

  const removeElement = (index: number) => {
    setElements(elements.filter((_, i) => i !== index))
  }

  const addReturnElement = () => {
    setReturnElements([...returnElements, { original_element_id: '', sku_id: '', qty: '', sn_list: '' }])
  }

  const updateReturnElement = (index: number, field: string, value: string) => {
    const updated = [...returnElements]
    updated[index] = { ...updated[index], [field]: value }
    setReturnElements(updated)
  }

  const removeReturnElement = (index: number) => {
    setReturnElements(returnElements.filter((_, i) => i !== index))
  }

  const totalAmount = elements.reduce((sum, el) => {
    return sum + (parseFloat(el.qty) || 0) * (parseFloat(el.price) || 0)
  }, 0)

  const isEquipment = selectedType === '设备采购' || selectedType === '设备采购(库存)'

  const resetForm = () => {
    setSelectedType(null)
    setFormData({
      business_id: '',
      sc_id: '',
      description: '',
      total_amt: '',
      total_deposit: '',
      prepayment_ratio: '0.3',
      balance_period: '30',
      day_rule: '自然日',
      start_trigger: '入库日',
    })
    setElements([])
    setScSkuIds([])
    setDefaultShippingPointId('')
  }

  const handleOpenChange = (open: boolean) => {
    setIsOpen(open)
    if (!open) resetForm()
  }

  return (
    <Dialog open={isOpen} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button>
          <Plus className="mr-2 h-4 w-4" />
          新建虚拟合同
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {selectedType ? `新建${VC_TYPE_LABELS[selectedType]}` : '选择合同类型'}
          </DialogTitle>
        </DialogHeader>

        {!selectedType ? (
          <div className="grid grid-cols-2 gap-4 py-4">
            {Object.entries(VC_TYPE_LABELS).map(([type, label]) => (
              <Button
                key={type}
                variant="outline"
                className="h-20 text-lg"
                onClick={() => setSelectedType(type as VCType)}
              >
                {label}
              </Button>
            ))}
          </div>
        ) : selectedType === '退货' ? (
          <form onSubmit={(e) => { e.preventDefault(); createMutation.mutate() }} className="space-y-6">
            <div className="space-y-2">
              <Label>原虚拟合同</Label>
              <Select value={returnFormData.target_vc_id} onValueChange={(v) => setReturnFormData({ ...returnFormData, target_vc_id: v })}>
                <SelectTrigger><SelectValue placeholder="选择原合同" /></SelectTrigger>
                <SelectContent>
                  {vcsForReturn?.items?.map(vc => (
                    <SelectItem key={vc.id} value={String(vc.id)}>VC-{vc.id} - {vc.description?.slice(0, 30) || '无描述'}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>退货方向</Label>
              <Select value={returnFormData.return_direction} onValueChange={(v) => setReturnFormData({ ...returnFormData, return_direction: v })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="CUSTOMER_TO_US">客户退货给我方</SelectItem>
                  <SelectItem value="US_TO_SUPPLIER">我方退货给供应商</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label>货款金额</Label>
                <Input type="number" value={returnFormData.goods_amount} onChange={(e) => setReturnFormData({ ...returnFormData, goods_amount: e.target.value })} />
              </div>
              <div className="space-y-2">
                <Label>押金金额</Label>
                <Input type="number" value={returnFormData.deposit_amount} onChange={(e) => setReturnFormData({ ...returnFormData, deposit_amount: e.target.value })} />
              </div>
              <div className="space-y-2">
                <Label>物流费用</Label>
                <Input type="number" value={returnFormData.logistics_cost} onChange={(e) => setReturnFormData({ ...returnFormData, logistics_cost: e.target.value })} />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>物流承担方</Label>
                <Select value={returnFormData.logistics_bearer} onValueChange={(v) => setReturnFormData({ ...returnFormData, logistics_bearer: v })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="SENDER">发货方</SelectItem>
                    <SelectItem value="RECEIVER">收货方</SelectItem>
                    <SelectItem value="BUYER">买方</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>退款总额</Label>
                <Input type="number" value={returnFormData.total_refund} onChange={(e) => setReturnFormData({ ...returnFormData, total_refund: e.target.value })} />
              </div>
            </div>

            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <Label>退货明细</Label>
                <Button type="button" variant="outline" size="sm" onClick={addReturnElement}>
                  <Plus className="mr-2 h-4 w-4" />添加
                </Button>
              </div>
              {returnElements.map((el, idx) => (
                <Card key={idx}>
                  <CardContent className="pt-4">
                    <div className="grid grid-cols-4 gap-3">
                      <div className="space-y-2">
                        <Label className="text-xs">SKU</Label>
                        <Select value={el.sku_id} onValueChange={(v) => updateReturnElement(idx, 'sku_id', v)}>
                          <SelectTrigger><SelectValue placeholder="选择SKU" /></SelectTrigger>
                          <SelectContent>
                            {skus?.items?.map(s => (
                              <SelectItem key={s.id} value={String(s.id)}>{s.name}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="space-y-2">
                        <Label className="text-xs">数量</Label>
                        <Input type="number" value={el.qty} onChange={(e) => updateReturnElement(idx, 'qty', e.target.value)} />
                      </div>
                      <div className="space-y-2">
                        <Label className="text-xs">SN列表</Label>
                        <Input placeholder="SN1,SN2" value={el.sn_list} onChange={(e) => updateReturnElement(idx, 'sn_list', e.target.value)} />
                      </div>
                      <div className="flex items-end">
                        <Button type="button" variant="ghost" onClick={() => removeReturnElement(idx)}>
                          <X className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
              {returnElements.length === 0 && <div className="text-center py-4 text-muted-foreground">点击添加退货明细</div>}
            </div>

            <div className="space-y-2">
              <Label>退货原因</Label>
              <Input value={returnFormData.reason} onChange={(e) => setReturnFormData({ ...returnFormData, reason: e.target.value })} />
            </div>

            <div className="space-y-2">
              <Label>备注</Label>
              <Textarea value={returnFormData.description} onChange={(e) => setReturnFormData({ ...returnFormData, description: e.target.value })} />
            </div>

            <div className="flex justify-end gap-2">
              <Button type="button" variant="outline" onClick={() => setSelectedType(null)}>返回</Button>
              <Button type="submit" disabled={createMutation.isPending || !returnFormData.target_vc_id}>
                {createMutation.isPending ? '创建中...' : '创建'}
              </Button>
            </div>
          </form>
        ) : (
        <form onSubmit={(e) => { e.preventDefault(); createMutation.mutate() }} className="space-y-6">
          {/* Business/Supply Chain Selection */}
          {(selectedType === '设备采购' || selectedType === '物料供应' || selectedType === '库存拨付') && (
            <div className="space-y-2">
              <Label>关联业务</Label>
              <Select value={formData.business_id} onValueChange={(v) => setFormData({ ...formData, business_id: v })}>
                <SelectTrigger>
                  <SelectValue placeholder="选择业务" />
                </SelectTrigger>
                <SelectContent>
                  {businesses?.items?.map(b => (
                    <SelectItem key={b.id} value={String(b.id)}>{b.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          {(selectedType === '设备采购' || selectedType === '设备采购(库存)' || selectedType === '物料采购') && (
            <div className="space-y-2">
              <Label>供应链协议</Label>
              <Select value={formData.sc_id} onValueChange={(v) => {
                setFormData({ ...formData, sc_id: v })
                setElements([]) // 清空已有明细，因为 SKU 列表可能变化
                const sc = supplyChains?.items?.find(s => s.id === parseInt(v))
                if (sc?.items) {
                  const skuIds = sc.items.map((i: any) => i.sku_id)
                  setScSkuIds(skuIds)
                } else {
                  setScSkuIds([])
                }
                // 找到供应商的仓库点（id 最小的）
                const supplierPoints = points?.items?.filter(p => p.supplier_id === sc?.supplier_id) || []
                const defaultPoint = supplierPoints.sort((a, b) => a.id - b.id)[0]
                setDefaultShippingPointId(defaultPoint ? String(defaultPoint.id) : '')
              }}>
                <SelectTrigger>
                  <SelectValue placeholder="选择供应链" />
                </SelectTrigger>
                <SelectContent>
                  {supplyChains?.items?.filter(sc => {
                    if (selectedType === '物料采购') return sc.type === 'MATERIAL' || sc.type === '物料'
                    if (selectedType === '设备采购' || selectedType === '设备采购(库存)') return sc.type === 'EQUIPMENT' || sc.type === '设备'
                    return false
                  }).map(sc => (
                    <SelectItem key={sc.id} value={String(sc.id)}>
                      <div className="flex flex-col gap-0.5">
                        <span>{sc.supplier_name || `供应商${sc.supplier_id}`} ({sc.type === 'EQUIPMENT' ? '设备' : sc.type === 'MATERIAL' ? '物料' : sc.type})</span>
                        <span className="text-xs text-muted-foreground">
                          SKU {sc.items?.length || 0} 种 {sc.contract_num ? `| 合同号: ${sc.contract_num}` : ''}
                        </span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          {/* Payment Terms */}
          {(selectedType === '设备采购' || selectedType === '设备采购(库存)' || selectedType === '物料采购') && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="space-y-2">
                <Label className="text-xs">预付款比例</Label>
                <Input type="number" step="0.01" min="0" max="1"
                  value={formData.prepayment_ratio}
                  onChange={(e) => setFormData({ ...formData, prepayment_ratio: e.target.value })} />
              </div>
              <div className="space-y-2">
                <Label className="text-xs">账期(天)</Label>
                <Input type="number"
                  value={formData.balance_period}
                  onChange={(e) => setFormData({ ...formData, balance_period: e.target.value })} />
              </div>
              <div className="space-y-2">
                <Label className="text-xs">日期规则</Label>
                <Select value={formData.day_rule} onValueChange={(v) => setFormData({ ...formData, day_rule: v })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="自然日">自然日</SelectItem>
                    <SelectItem value="工作日">工作日</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label className="text-xs">起算触发</Label>
                <Select value={formData.start_trigger} onValueChange={(v) => setFormData({ ...formData, start_trigger: v })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="入库日">入库日</SelectItem>
                    <SelectItem value="签收日">签收日</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          )}

          {/* Elements */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <Label>明细项目</Label>
              <Button type="button" variant="outline" size="sm" onClick={addElement}>
                <Plus className="mr-2 h-4 w-4" />添加项目
              </Button>
            </div>

            {elements.map((el, index) => (
              <Card key={index}>
                <CardContent className="pt-4">
                  <div className="grid grid-cols-3 md:grid-cols-9 gap-4">
                    <div className="space-y-2 md:col-span-2">
                      <Label className="text-xs">SKU{scSkuIds.length > 0 ? ` (${scSkuIds.length}种)` : ''}</Label>
                      <Select value={el.sku_id} onValueChange={(v) => updateElement(index, 'sku_id', v)}>
                        <SelectTrigger className="truncate"><SelectValue placeholder="选择SKU" /></SelectTrigger>
                        <SelectContent>
                          {skus?.items?.filter(s => scSkuIds.length === 0 || scSkuIds.includes(s.id)).map(s => (
                            <SelectItem key={s.id} value={String(s.id)} className="truncate">{s.name}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2 md:col-span-2">
                      <Label className="text-xs">发货点</Label>
                      <PointSelect
                        value={el.shipping_point_id}
                        onValueChange={(v) => updateElement(index, 'shipping_point_id', v)}
                        options={(points?.items || []) as PointOption[]}
                        placeholder="发货点"
                      />
                    </div>
                    <div className="space-y-2 md:col-span-2">
                      <Label className="text-xs">收货点</Label>
                      <PointSelect
                        value={el.receiving_point_id}
                        onValueChange={(v) => updateElement(index, 'receiving_point_id', v)}
                        options={(points?.items || []) as PointOption[]}
                        placeholder="收货点"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label className="text-xs">数量</Label>
                      <Input type="number" value={el.qty} onChange={(e) => updateElement(index, 'qty', e.target.value)} />
                    </div>
                    <div className="space-y-2">
                      <Label className="text-xs">单价</Label>
                      <Input type="number" value={el.price} onChange={(e) => updateElement(index, 'price', e.target.value)} />
                    </div>
                    {isEquipment && (
                      <div className="space-y-2">
                        <Label className="text-xs">押金</Label>
                        <Input type="number" value={el.deposit} onChange={(e) => updateElement(index, 'deposit', e.target.value)} />
                      </div>
                    )}
                    <div className="flex items-end">
                      <Button type="button" variant="ghost" size="icon" onClick={() => removeElement(index)}>
                        <X className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                  <div className="mt-2 text-right text-sm text-muted-foreground">
                    小计: {formatCurrency((parseFloat(el.qty) || 0) * (parseFloat(el.price) || 0))}
                  </div>
                </CardContent>
              </Card>
            ))}

            {elements.length === 0 && (
              <div className="text-center py-8 text-muted-foreground">
                点击"添加项目"添加明细
              </div>
            )}
          </div>

          {/* Total */}
          <div className="flex justify-between items-center text-lg">
            <span>总金额:</span>
            <span className="font-bold">{formatCurrency(totalAmount)}</span>
          </div>

          {/* Description */}
          <div className="space-y-2">
            <Label>备注</Label>
            <Textarea value={formData.description} onChange={(e) => setFormData({ ...formData, description: e.target.value })} />
          </div>

          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => setSelectedType(null)}>返回</Button>
            <Button type="submit" disabled={createMutation.isPending || elements.length === 0}>
              {createMutation.isPending ? '创建中...' : '创建'}
            </Button>
          </div>
        </form>
        )}
      </DialogContent>
    </Dialog>
  )
}

function AllocateInventoryDialog({ onSuccess }: { onSuccess: () => void }) {
  const queryClient = useQueryClient()
  const [isOpen, setIsOpen] = useState(false)
  const [formData, setFormData] = useState({ business_id: '', description: '' })
  const [elements, setElements] = useState<ElementFormState[]>([])

  const { data: businesses } = useQuery({
    queryKey: ['businesses-for-allocate'],
    queryFn: () => masterApi.customers.list({ size: 100 }),
  })

  const { data: points } = useQuery({
    queryKey: ['points-for-allocate'],
    queryFn: () => masterApi.points.list({ size: 100 }),
  })

  const { data: skus } = useQuery({
    queryKey: ['skus-for-allocate'],
    queryFn: () => masterApi.skus.list({ size: 100 }),
  })

  const createMutation = useMutation({
    mutationFn: () => vcApi.allocateInventory({
      business_id: parseInt(formData.business_id),
      elements: elements.map(el => ({
        shipping_point_id: parseInt(el.shipping_point_id) || 0,
        receiving_point_id: parseInt(el.receiving_point_id) || 0,
        sku_id: parseInt(el.sku_id),
        qty: parseFloat(el.qty) || 0,
        price: parseFloat(el.price) || 0,
        deposit: 0,
        subtotal: (parseFloat(el.qty) || 0) * (parseFloat(el.price) || 0),
      })),
      description: formData.description,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vc-list'] })
      setIsOpen(false)
      onSuccess()
    },
  })

  const addElement = () => {
    setElements([...elements, { sku_id: '', shipping_point_id: '', receiving_point_id: '', qty: '', price: '', deposit: '', sn_list: '' }])
  }

  const updateElement = (index: number, field: keyof ElementFormState, value: string) => {
    const updated = [...elements]
    updated[index] = { ...updated[index], [field]: value }
    setElements(updated)
  }

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button variant="outline">
          <Plus className="mr-2 h-4 w-4" />库存拨付
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>库存拨付</DialogTitle>
        </DialogHeader>
        <form onSubmit={(e) => { e.preventDefault(); createMutation.mutate() }} className="space-y-6">
          <div className="space-y-2">
            <Label>业务（客户）</Label>
            <Select value={formData.business_id} onValueChange={(v) => setFormData({ ...formData, business_id: v })}>
              <SelectTrigger><SelectValue placeholder="选择业务" /></SelectTrigger>
              <SelectContent>
                {businesses?.items?.map(b => (
                  <SelectItem key={b.id} value={String(b.id)}>{b.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <Label>拨付明细</Label>
              <Button type="button" variant="outline" size="sm" onClick={addElement}>
                <Plus className="mr-2 h-4 w-4" />添加
              </Button>
            </div>
            {elements.map((el, idx) => (
              <Card key={idx}>
                <CardContent className="pt-4">
                  <div className="grid grid-cols-5 gap-3">
                    <div className="space-y-2">
                      <Label className="text-xs">SKU</Label>
                      <Select value={el.sku_id} onValueChange={(v) => updateElement(idx, 'sku_id', v)}>
                        <SelectTrigger><SelectValue placeholder="选择SKU" /></SelectTrigger>
                        <SelectContent>
                          {skus?.items?.map(s => (
                            <SelectItem key={s.id} value={String(s.id)}>{s.name}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label className="text-xs">发货点</Label>
                      <PointSelect
                        value={el.shipping_point_id}
                        onValueChange={(v) => updateElement(idx, 'shipping_point_id', v)}
                        options={(points?.items || []) as PointOption[]}
                        placeholder="发货点"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label className="text-xs">收货点</Label>
                      <PointSelect
                        value={el.receiving_point_id}
                        onValueChange={(v) => updateElement(idx, 'receiving_point_id', v)}
                        options={(points?.items || []) as PointOption[]}
                        placeholder="收货点"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label className="text-xs">数量</Label>
                      <Input type="number" value={el.qty} onChange={(e) => updateElement(idx, 'qty', e.target.value)} />
                    </div>
                    <div className="space-y-2">
                      <Label className="text-xs">单价</Label>
                      <Input type="number" value={el.price} onChange={(e) => updateElement(idx, 'price', e.target.value)} />
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
            {elements.length === 0 && <div className="text-center py-4 text-muted-foreground">点击添加拨付明细</div>}
          </div>

          <div className="space-y-2">
            <Label>备注</Label>
            <Textarea value={formData.description} onChange={(e) => setFormData({ ...formData, description: e.target.value })} />
          </div>

          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => setIsOpen(false)}>取消</Button>
            <Button type="submit" disabled={!formData.business_id || elements.length === 0 || createMutation.isPending}>
              {createMutation.isPending ? '创建中...' : '创建'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function VCUpdateDialog({ vc, onSuccess }: { vc: VirtualContract; onSuccess: () => void }) {
  const queryClient = useQueryClient()
  const [isOpen, setIsOpen] = useState(false)
  const [formData, setFormData] = useState({ description: vc.description || '' })

  const updateMutation = useMutation({
    mutationFn: () => vcApi.update({ vc_id: vc.id, description: formData.description }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vc-list'] })
      queryClient.invalidateQueries({ queryKey: ['vc-detail', vc.id] })
      setIsOpen(false)
      onSuccess()
    },
  })

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="sm"><Pencil className="h-4 w-4" /></Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>编辑合同描述</DialogTitle>
        </DialogHeader>
        <form onSubmit={(e) => { e.preventDefault(); updateMutation.mutate() }} className="space-y-4">
          <div className="space-y-2">
            <Label>描述</Label>
            <Textarea value={formData.description} onChange={(e) => setFormData({ ...formData, description: e.target.value })} />
          </div>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => setIsOpen(false)}>取消</Button>
            <Button type="submit" disabled={updateMutation.isPending}>保存</Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function VCDetailDialog({ vc, onClose }: { vc: VirtualContract; onClose: () => void }) {
  const [activeTab, setActiveTab] = useState('detail')

  const { data: detail, isLoading } = useQuery({
    queryKey: ['vc-detail', vc.id],
    queryFn: () => vcApi.getDetail(vc.id),
    enabled: activeTab === 'detail',
  })

  const { data: progress } = useQuery({
    queryKey: ['vc-progress', vc.id],
    queryFn: () => vcApi.getCashflowProgress(vc.id),
    enabled: activeTab === 'payment',
  })

  return (
    <Dialog open onOpenChange={() => onClose()}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Badge className={VC_TYPE_COLORS[vc.type]}>{VC_TYPE_LABELS[vc.type]}</Badge>
            <span>VC-{vc.id}</span>
          </DialogTitle>
        </DialogHeader>

        {/* Status Badges */}
        <div className="flex gap-2 flex-wrap">
          <Badge className={STATUS_COLORS[vc.status] || 'bg-gray-100'}>状态: {vc.status}</Badge>
          <Badge className={STATUS_COLORS[vc.subject_status] || 'bg-gray-100'}>标的: {vc.subject_status}</Badge>
          <Badge className={STATUS_COLORS[vc.cash_status] || 'bg-gray-100'}>资金: {vc.cash_status}</Badge>
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList>
            <TabsTrigger value="detail">详情</TabsTrigger>
            <TabsTrigger value="payment">付款进度</TabsTrigger>
            <TabsTrigger value="logistics">物流</TabsTrigger>
          </TabsList>

          <TabsContent value="detail" className="space-y-4">
            {isLoading ? (
              <div className="text-center py-4">加载中...</div>
            ) : detail ? (
              <>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label className="text-muted-foreground">关联业务</Label>
                    <p>{detail.business_name || '-'}</p>
                  </div>
                  <div>
                    <Label className="text-muted-foreground">供应链</Label>
                    <p>{detail.supply_chain_name || '-'}</p>
                  </div>
                  <div>
                    <Label className="text-muted-foreground">总金额</Label>
                    <p>{formatCurrency(detail.total_amount || 0)}</p>
                  </div>
                  <div>
                    <Label className="text-muted-foreground">预付款比例</Label>
                    <p>{((detail.deposit_info?.prepayment_ratio || 0) * 100).toFixed(0)}%</p>
                  </div>
                  <div>
                    <Label className="text-muted-foreground">应收押金</Label>
                    <p>{formatCurrency(detail.deposit_info?.expected_deposit || 0)}</p>
                  </div>
                  <div>
                    <Label className="text-muted-foreground">实收押金</Label>
                    <p>{formatCurrency(detail.deposit_info?.actual_deposit || 0)}</p>
                  </div>
                  <div>
                    <Label className="text-muted-foreground">应付总额</Label>
                    <p>{formatCurrency(detail.total_amount || 0)}</p>
                  </div>
                  <div>
                    <Label className="text-muted-foreground">实付金额</Label>
                    <p>{formatCurrency(detail.deposit_info?.paid_amount || 0)}</p>
                  </div>
                </div>

                <div>
                  <Label className="text-muted-foreground">描述</Label>
                  <p>{detail.description || '-'}</p>
                </div>

                <div>
                  <Label className="mb-2">明细项目</Label>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>SKU</TableHead>
                        <TableHead>发货点</TableHead>
                        <TableHead>收货点</TableHead>
                        <TableHead className="text-right">数量</TableHead>
                        <TableHead className="text-right">单价</TableHead>
                        <TableHead className="text-right">押金</TableHead>
                        <TableHead className="text-right">小计</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {(((detail.elements as any)?.items) || ((detail.elements as any)?.elements) || [])?.map((el: any, idx: number) => (
                        <TableRow key={idx}>
                          <TableCell>{el.sku_name || el.sku_id}</TableCell>
                          <TableCell>{el.shipping_point_name || el.shipping_point_id}</TableCell>
                          <TableCell>{el.receiving_point_name || el.receiving_point_id}</TableCell>
                          <TableCell className="text-right">{el.qty}</TableCell>
                          <TableCell className="text-right">{formatCurrency(el.price)}</TableCell>
                          <TableCell className="text-right">{formatCurrency(el.deposit)}</TableCell>
                          <TableCell className="text-right">{formatCurrency(el.subtotal)}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>

                {/* Status History */}
                {detail.status_logs && detail.status_logs.length > 0 && (
                  <div>
                    <Label className="mb-2">状态历史</Label>
                    <div className="space-y-2">
                      {detail.status_logs.map((log) => (
                        <div key={log.id} className="flex items-center gap-2 text-sm">
                          <ChevronRight className="h-4 w-4 text-muted-foreground" />
                          <span className="text-muted-foreground">{formatDate(log.timestamp)}</span>
                          <Badge className={STATUS_COLORS[log.status_name] || 'bg-gray-100'}>{log.status_name}</Badge>
                          <span className="text-muted-foreground text-xs">[{(log.category || '').toUpperCase()}]</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div className="text-center py-4">无数据</div>
            )}
          </TabsContent>

          <TabsContent value="payment" className="space-y-4">
            {progress ? (
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <Card>
                  <CardContent className="pt-4">
                    <div className="text-2xl font-bold">{formatCurrency(progress.goods?.total || 0)}</div>
                    <p className="text-sm text-muted-foreground">应付总额</p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-4">
                    <div className="text-2xl font-bold text-green-600">{formatCurrency(progress.goods?.paid || 0)}</div>
                    <p className="text-sm text-muted-foreground">已付金额</p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-4">
                    <div className="text-2xl font-bold text-orange-600">{formatCurrency(progress.goods?.balance || 0)}</div>
                    <p className="text-sm text-muted-foreground">未付余额</p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-4">
                    <div className="text-2xl font-bold">{formatCurrency(progress.deposit?.should || 0)}</div>
                    <p className="text-sm text-muted-foreground">应收押金</p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-4">
                    <div className="text-2xl font-bold text-blue-600">{formatCurrency(progress.deposit?.received || 0)}</div>
                    <p className="text-sm text-muted-foreground">实收押金</p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-4">
                    <div className="text-2xl font-bold">{formatCurrency(progress.goods?.pool || 0)}</div>
                    <p className="text-sm text-muted-foreground">核销池余额</p>
                  </CardContent>
                </Card>
              </div>
            ) : (
              <div className="text-center py-4">加载中...</div>
            )}
          </TabsContent>

          <TabsContent value="logistics">
            {detail?.logistics && detail.logistics.length > 0 ? (
              <div className="space-y-4">
                {detail.logistics.map(log => (
                  <Card key={log.id}>
                    <CardHeader>
                      <CardTitle className="text-base flex items-center justify-between">
                        <span>物流-{log.id}</span>
                        <Badge>{log.status}</Badge>
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>快递单号</TableHead>
                            <TableHead>状态</TableHead>
                            <TableHead>物品</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {(log.express_orders || []).map(order => (
                            <TableRow key={order.id}>
                              <TableCell className="font-mono">{order.tracking_number}</TableCell>
                              <TableCell><Badge>{order.status}</Badge></TableCell>
                              <TableCell>
                                {order.items?.map((item, i) => (
                                  <span key={i} className="mr-2">{item.sku_name} x{item.qty}</span>
                                ))}
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </CardContent>
                  </Card>
                ))}
              </div>
            ) : (
              <div className="text-center py-4 text-muted-foreground">暂无物流记录</div>
            )}
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  )
}

function ReturnCreateDialog({ onSuccess }: { onSuccess: () => void }) {
  const queryClient = useQueryClient()
  const [isOpen, setIsOpen] = useState(false)
  const [formData, setFormData] = useState({
    target_vc_id: '',
    return_direction: 'CUSTOMER_TO_US',
    goods_amount: '',
    deposit_amount: '',
    logistics_cost: '',
    logistics_bearer: 'SENDER',
    total_refund: '',
    reason: '',
    description: '',
  })
  const [elements, setElements] = useState<{
    original_element_id: string
    sku_id: string
    qty: string
    sn_list: string
  }[]>([])

  const { data: vcs } = useQuery({
    queryKey: ['vcs-for-return'],
    queryFn: () => vcApi.list({ status: '执行', size: 100 }),
  })

  const { data: skus } = useQuery({
    queryKey: ['skus-for-return'],
    queryFn: () => masterApi.skus.list({ size: 100 }),
  })

  const createMutation = useMutation({
    mutationFn: async () => {
      return vcApi.createReturn({
        target_vc_id: parseInt(formData.target_vc_id),
        return_direction: formData.return_direction as 'CUSTOMER_TO_US' | 'US_TO_SUPPLIER',
        elements: elements.map(el => ({
          shipping_point_id: 0,
          receiving_point_id: 0,
          sku_id: parseInt(el.sku_id),
          qty: parseFloat(el.qty),
          price: 0,
          deposit: 0,
          subtotal: 0,
          sn_list: el.sn_list ? el.sn_list.split(',').map(s => s.trim()).filter(Boolean) : [],
        })),
        goods_amount: parseFloat(formData.goods_amount) || 0,
        deposit_amount: parseFloat(formData.deposit_amount) || 0,
        logistics_cost: parseFloat(formData.logistics_cost) || 0,
        logistics_bearer: formData.logistics_bearer,
        total_refund: parseFloat(formData.total_refund) || 0,
        reason: formData.reason,
        description: formData.description,
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vc-list'] })
      setIsOpen(false)
      onSuccess()
    },
  })

  const addElement = () => {
    setElements([...elements, { original_element_id: '', sku_id: '', qty: '', sn_list: '' }])
  }

  const updateElement = (index: number, field: string, value: string) => {
    const updated = [...elements]
    updated[index] = { ...updated[index], [field]: value }
    setElements(updated)
  }

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button><RotateCcw className="mr-2 h-4 w-4" />新建退货</Button>
      </DialogTrigger>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>新建退货</DialogTitle>
        </DialogHeader>
        <form onSubmit={(e) => { e.preventDefault(); createMutation.mutate() }} className="space-y-6">
          <div className="space-y-2">
            <Label>退货目标合同</Label>
            <Select value={formData.target_vc_id} onValueChange={(v) => setFormData({ ...formData, target_vc_id: v })}>
              <SelectTrigger><SelectValue placeholder="选择合同" /></SelectTrigger>
              <SelectContent>
                {vcs?.items?.map(vc => (
                  <SelectItem key={vc.id} value={String(vc.id)}>
                    VC-{vc.id} {VC_TYPE_LABELS[vc.type]} - {vc.description?.slice(0, 20)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label>退货方向</Label>
            <Select value={formData.return_direction} onValueChange={(v) => setFormData({ ...formData, return_direction: v })}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="CUSTOMER_TO_US">客户退给我们</SelectItem>
                <SelectItem value="US_TO_SUPPLIER">我们退给供应商</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label>退货明细</Label>
            <Button type="button" variant="outline" size="sm" onClick={addElement}>
              <Plus className="mr-2 h-4 w-4" />添加
            </Button>
            {elements.map((el, idx) => (
              <Card key={idx}>
                <CardContent className="pt-4">
                  <div className="grid grid-cols-4 gap-3">
                    <div className="space-y-2">
                      <Label className="text-xs">SKU</Label>
                      <Select value={el.sku_id} onValueChange={(v) => updateElement(idx, 'sku_id', v)}>
                        <SelectTrigger><SelectValue placeholder="选择SKU" /></SelectTrigger>
                        <SelectContent>
                          {skus?.items?.map(s => (
                            <SelectItem key={s.id} value={String(s.id)}>{s.name}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label className="text-xs">数量</Label>
                      <Input type="number" value={el.qty} onChange={(e) => updateElement(idx, 'qty', e.target.value)} />
                    </div>
                    <div className="space-y-2">
                      <Label className="text-xs">SN列表</Label>
                      <Input placeholder="SN1,SN2,..." value={el.sn_list} onChange={(e) => updateElement(idx, 'sn_list', e.target.value)} />
                    </div>
                    <div className="flex items-end">
                      <Button type="button" variant="ghost" onClick={() => setElements(elements.filter((_, i) => i !== idx))}>
                        <X className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>货款金额</Label>
              <Input type="number" value={formData.goods_amount} onChange={(e) => setFormData({ ...formData, goods_amount: e.target.value })} />
            </div>
            <div className="space-y-2">
              <Label>退还押金</Label>
              <Input type="number" value={formData.deposit_amount} onChange={(e) => setFormData({ ...formData, deposit_amount: e.target.value })} />
            </div>
            <div className="space-y-2">
              <Label>物流费用</Label>
              <Input type="number" value={formData.logistics_cost} onChange={(e) => setFormData({ ...formData, logistics_cost: e.target.value })} />
            </div>
            <div className="space-y-2">
              <Label>物流费承担方</Label>
              <Select value={formData.logistics_bearer} onValueChange={(v) => setFormData({ ...formData, logistics_bearer: v })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="SENDER">发货方</SelectItem>
                  <SelectItem value="RECEIVER">收货方</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-2">
            <Label>总退款金额</Label>
            <Input type="number" value={formData.total_refund} onChange={(e) => setFormData({ ...formData, total_refund: e.target.value })} />
          </div>

          <div className="space-y-2">
            <Label>退货原因</Label>
            <Textarea value={formData.reason} onChange={(e) => setFormData({ ...formData, reason: e.target.value })} />
          </div>

          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => setIsOpen(false)}>取消</Button>
            <Button type="submit" disabled={!formData.target_vc_id || elements.length === 0 || createMutation.isPending}>
              创建
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function VCDeleteButton({ vcId }: { vcId: number }) {
  const queryClient = useQueryClient()
  const deleteMutation = useMutation({
    mutationFn: () => vcApi.delete(vcId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['vc-list'] }),
  })

  return (
    <Button variant="ghost" size="sm" onClick={() => {
      if (confirm('确认删除此虚拟合同？删除后不可恢复。')) {
        deleteMutation.mutate()
      }
    }} className="text-destructive">
      <Trash2 className="h-4 w-4" />
    </Button>
  )
}

export function VCPager() {
  const [activeTab, setActiveTab] = useState('list')
  const [typeFilter, setTypeFilter] = useState<VCType | 'ALL'>('ALL')
  const [statusFilter, setStatusFilter] = useState<VCStatus | 'ALL'>('ALL')
  const [search, setSearch] = useState('')
  const [selectedVC, setSelectedVC] = useState<VirtualContract | null>(null)
  const [page, setPage] = useState(1)
  const pageSize = 20

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['vc-list', typeFilter, statusFilter, search, page],
    queryFn: () => vcApi.list({
      type: typeFilter !== 'ALL' ? typeFilter : undefined,
      status: statusFilter !== 'ALL' ? statusFilter : undefined,
      search: search || undefined,
      page,
      size: pageSize,
    }),
  })

  const totalPages = data ? Math.ceil(data.total / pageSize) : 0

  useEffect(() => { setPage(1) }, [typeFilter, statusFilter, search])

  // ========== 全局概览搜索状态 ==========
  // Store form values as strings (from <Input>), convert to numbers in queryFn
  const [overviewParams, setOverviewParams] = useState<Record<string, string | number | undefined>>({ size: 20, page: 1 })
  const [searchCount, setSearchCount] = useState(0)

  const { data: overviewData, isLoading: isOverviewSearching } = useQuery({
    queryKey: ['vc-global', overviewParams, searchCount],
    enabled: searchCount > 0,
    queryFn: () => {
      const p = { ...overviewParams }
      const numFields = ['vc_id', 'business_id', 'supply_chain_id', 'sku_id', 'shipping_point_id', 'receiving_point_id']
      Object.keys(p).forEach(k => {
        if (numFields.includes(k) && typeof p[k] === 'string' && p[k] !== '') {
          p[k] = Number(p[k])
        } else if (p[k] === '' || p[k] === undefined) {
          delete p[k]
        }
      })
      return vcApi.getGlobalOverview(p as VCGlobalSearchParams) as unknown as Promise<VCListResponse>
    },
  })

  const doOverviewSearch = () => {
    setSelectedVC(null)
    setSearchCount(c => c + 1)
  }

  const clearOverview = () => {
    setOverviewParams({ size: 20, page: 1 })
    setSelectedVC(null)
  }

  const overviewTotalPages = overviewData ? Math.ceil(overviewData.total / (overviewData.size || 20)) : 0

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">虚拟合同</h2>
        <div className="flex gap-2">
          <VCCreateDialog onSuccess={() => refetch()} />
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList>
          <TabsTrigger value="list">列表</TabsTrigger>
          <TabsTrigger value="global">全局概览</TabsTrigger>
        </TabsList>

        <TabsContent value="list" className="space-y-4">
          {/* Filters */}
          <div className="flex gap-4 flex-wrap">
            <Input placeholder="搜索合同..." value={search} onChange={(e) => setSearch(e.target.value)} className="w-64" />
            <Select value={typeFilter} onValueChange={(v) => setTypeFilter(v as VCType | 'ALL')}>
              <SelectTrigger className="w-40">
                <SelectValue placeholder="合同类型" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ALL">全部类型</SelectItem>
                {Object.entries(VC_TYPE_LABELS).map(([value, label]) => (
                  <SelectItem key={value} value={value}>{label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={statusFilter} onValueChange={(v) => setStatusFilter(v as VCStatus | 'ALL')}>
              <SelectTrigger className="w-32">
                <SelectValue placeholder="状态" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ALL">全部状态</SelectItem>
                <SelectItem value="执行">执行中</SelectItem>
                <SelectItem value="完成">已完成</SelectItem>
                <SelectItem value="终止">已终止</SelectItem>
                <SelectItem value="取消">已取消</SelectItem>
              </SelectContent>
            </Select>
            <Button variant="outline" onClick={() => refetch()}>
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>

          {/* VC List */}
          <Card>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>ID</TableHead>
                    <TableHead>类型</TableHead>
                    <TableHead>描述</TableHead>
                    <TableHead>状态</TableHead>
                    <TableHead>标的</TableHead>
                    <TableHead>资金</TableHead>
                    <TableHead>总金额</TableHead>
                    <TableHead>创建时间</TableHead>
                    <TableHead>操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data?.items?.map(vc => (
                    <TableRow key={vc.id}>
                      <TableCell className="font-medium">VC-{vc.id}</TableCell>
                      <TableCell>
                        <Badge className={VC_TYPE_COLORS[vc.type]}>{VC_TYPE_LABELS[vc.type]}</Badge>
                      </TableCell>
                      <TableCell className="max-w-[200px] truncate">{vc.description || '-'}</TableCell>
                      <TableCell><Badge className={STATUS_COLORS[vc.status]}>{vc.status}</Badge></TableCell>
                      <TableCell><Badge className={STATUS_COLORS[vc.subject_status] || 'bg-gray-100'}>{vc.subject_status}</Badge></TableCell>
                      <TableCell><Badge className={STATUS_COLORS[vc.cash_status] || 'bg-gray-100'}>{vc.cash_status}</Badge></TableCell>
                      <TableCell className="text-right">{formatCurrency(vc.total_amount || 0)}</TableCell>
                      <TableCell>{formatDate(vc.created_at || '')}</TableCell>
                      <TableCell>
                        <div className="flex gap-1">
                          <Button variant="ghost" size="sm" onClick={() => setSelectedVC(vc)}>详情</Button>
                          <VCUpdateDialog vc={vc} onSuccess={() => refetch()} />
                          <VCDeleteButton vcId={vc.id} />
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                  {!data?.items?.length && (
                    <TableRow>
                      <TableCell colSpan={9} className="text-center text-muted-foreground">
                        {isLoading ? '加载中...' : '暂无数据'}
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
              {totalPages > 1 && (
                <div className="flex items-center justify-between px-4 py-3 border-t">
                  <div className="text-sm text-muted-foreground">
                    共 {data?.total || 0} 条，第 {page} / {totalPages} 页
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage(p => Math.max(1, p - 1))}
                      disabled={page <= 1}
                    >
                      上一页
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                      disabled={page >= totalPages}
                    >
                      下一页
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="global" className="space-y-4">
          {/* 搜索表单 */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">多条件搜索</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-4 gap-4">
                <div className="space-y-1">
                  <Label className="text-xs">VC ID</Label>
                  <Input value={overviewParams.vc_id} onChange={e => setOverviewParams((prev) => ({ ...prev, vc_id: e.target.value }))} placeholder="VC ID" />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">VC类型</Label>
                  <Select value={String(overviewParams.vc_type || '')} onValueChange={v => setOverviewParams((prev) => ({ ...prev, vc_type: v === 'ALL' ? '' : v }))}>
                    <SelectTrigger><SelectValue placeholder="选择类型" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="ALL">全部</SelectItem>
                      {Object.entries(VC_TYPE_LABELS).map(([value, label]) => (
                        <SelectItem key={value} value={value}>{label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">VC状态</Label>
                  <Select value={String(overviewParams.vc_status || '')} onValueChange={v => setOverviewParams((prev) => ({ ...prev, vc_status: v === 'ALL' ? '' : v }))}>
                    <SelectTrigger><SelectValue placeholder="选择状态" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="ALL">全部</SelectItem>
                      <SelectItem value="执行">执行中</SelectItem>
                      <SelectItem value="完成">已完成</SelectItem>
                      <SelectItem value="终止">已终止</SelectItem>
                      <SelectItem value="取消">已取消</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">标的状态</Label>
                  <Select value={String(overviewParams.vc_subject_status || '')} onValueChange={v => setOverviewParams((prev) => ({ ...prev, vc_subject_status: v === 'ALL' ? '' : v }))}>
                    <SelectTrigger><SelectValue placeholder="选择标的状态" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="ALL">全部</SelectItem>
                      <SelectItem value="执行">执行</SelectItem>
                      <SelectItem value="发货">发货</SelectItem>
                      <SelectItem value="签收">签收</SelectItem>
                      <SelectItem value="完成">完成</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">资金状态</Label>
                  <Select value={String(overviewParams.vc_cash_status || '')} onValueChange={v => setOverviewParams((prev) => ({ ...prev, vc_cash_status: v === 'ALL' ? '' : v }))}>
                    <SelectTrigger><SelectValue placeholder="选择资金状态" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="ALL">全部</SelectItem>
                      <SelectItem value="执行">执行</SelectItem>
                      <SelectItem value="预付">预付</SelectItem>
                      <SelectItem value="完成">完成</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">Business ID</Label>
                  <Input value={overviewParams.business_id} onChange={e => setOverviewParams((prev) => ({ ...prev, business_id: e.target.value }))} placeholder="Business ID" />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">客户名称</Label>
                  <Input value={overviewParams.business_customer_name_kw} onChange={e => setOverviewParams((prev) => ({ ...prev, business_customer_name_kw: e.target.value }))} placeholder="精确包含" />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">供应链ID</Label>
                  <Input value={overviewParams.supply_chain_id} onChange={e => setOverviewParams((prev) => ({ ...prev, supply_chain_id: e.target.value }))} placeholder="供应链ID" />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">供应商名称</Label>
                  <Input value={overviewParams.supply_chain_supplier_name_kw} onChange={e => setOverviewParams((prev) => ({ ...prev, supply_chain_supplier_name_kw: e.target.value }))} placeholder="精确包含" />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">SKU ID</Label>
                  <Input value={overviewParams.sku_id} onChange={e => setOverviewParams((prev) => ({ ...prev, sku_id: e.target.value }))} placeholder="SKU ID" />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">SKU名称</Label>
                  <Input value={overviewParams.sku_name_kw} onChange={e => setOverviewParams((prev) => ({ ...prev, sku_name_kw: e.target.value }))} placeholder="精确包含" />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">发货点位ID</Label>
                  <Input value={overviewParams.shipping_point_id} onChange={e => setOverviewParams((prev) => ({ ...prev, shipping_point_id: e.target.value }))} placeholder="发货点位ID" />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">发货点位名称</Label>
                  <Input value={overviewParams.shipping_point_name_kw} onChange={e => setOverviewParams((prev) => ({ ...prev, shipping_point_name_kw: e.target.value }))} placeholder="精确包含" />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">收货点位ID</Label>
                  <Input value={overviewParams.receiving_point_id} onChange={e => setOverviewParams((prev) => ({ ...prev, receiving_point_id: e.target.value }))} placeholder="收货点位ID" />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">收货点位名称</Label>
                  <Input value={overviewParams.receiving_point_name_kw} onChange={e => setOverviewParams((prev) => ({ ...prev, receiving_point_name_kw: e.target.value }))} placeholder="精确包含" />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">物流单号</Label>
                  <Input value={overviewParams.tracking_number} onChange={e => setOverviewParams((prev) => ({ ...prev, tracking_number: e.target.value }))} placeholder="精确包含" />
                </div>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" onClick={clearOverview}>清空</Button>
                <Button onClick={doOverviewSearch} disabled={isOverviewSearching}>
                  {isOverviewSearching ? '搜索中...' : '搜索'}
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* 搜索结果 */}
          {overviewData && (
            <>
              <div className="text-sm text-muted-foreground">共 {overviewData.total} 条记录</div>
              <Card>
                <CardContent className="p-0">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>ID</TableHead>
                        <TableHead>类型</TableHead>
                        <TableHead>描述</TableHead>
                        <TableHead>状态</TableHead>
                        <TableHead>标的</TableHead>
                        <TableHead>资金</TableHead>
                        <TableHead>总金额</TableHead>
                        <TableHead>创建时间</TableHead>
                        <TableHead>操作</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {overviewData.items?.map((vc) => (
                        <TableRow key={vc.id}>
                          <TableCell className="font-medium">VC-{vc.id}</TableCell>
                          <TableCell>
                            <Badge className={VC_TYPE_COLORS[vc.type]}>{VC_TYPE_LABELS[vc.type]}</Badge>
                          </TableCell>
                          <TableCell className="max-w-[200px] truncate">{vc.description || '-'}</TableCell>
                          <TableCell><Badge className={STATUS_COLORS[vc.status]}>{vc.status}</Badge></TableCell>
                          <TableCell><Badge className={STATUS_COLORS[vc.subject_status] || 'bg-gray-100'}>{vc.subject_status}</Badge></TableCell>
                          <TableCell><Badge className={STATUS_COLORS[vc.cash_status] || 'bg-gray-100'}>{vc.cash_status}</Badge></TableCell>
                          <TableCell className="text-right">{formatCurrency(vc.total_amount || 0)}</TableCell>
                          <TableCell>{formatDate(vc.created_at || '')}</TableCell>
                          <TableCell>
                            <div className="flex gap-1">
                              <Button variant="ghost" size="sm" onClick={() => setSelectedVC(vc)}>详情</Button>
                              <VCUpdateDialog vc={vc} onSuccess={() => refetch()} />
                              <VCDeleteButton vcId={vc.id} />
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                      {!overviewData.items?.length && (
                        <TableRow>
                          <TableCell colSpan={9} className="text-center text-muted-foreground">暂无数据</TableCell>
                        </TableRow>
                      )}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>

              {/* 分页 */}
              {overviewTotalPages > 1 && (
                <div className="flex items-center justify-center gap-2">
                  <Button variant="outline" size="sm" onClick={() => setOverviewParams((prev) => ({ ...prev, page: Number(prev.page || 1) - 1 }))} disabled={(Number(overviewParams.page) || 1) <= 1}>上一页</Button>
                  <span className="text-sm text-muted-foreground">第 {Number(overviewParams.page) || 1} / {overviewTotalPages} 页</span>
                  <Button variant="outline" size="sm" onClick={() => setOverviewParams((prev) => ({ ...prev, page: Number(prev.page || 1) + 1 }))} disabled={(Number(overviewParams.page) || 1) >= overviewTotalPages}>下一页</Button>
                </div>
              )}
            </>
          )}
        </TabsContent>
      </Tabs>

      {selectedVC && (
        <VCDetailDialog vc={selectedVC} onClose={() => setSelectedVC(null)} />
      )}
    </div>
  )
}
