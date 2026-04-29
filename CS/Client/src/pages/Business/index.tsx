import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Search, RefreshCw, ChevronRight, X, Pencil, Trash2, AlertTriangle } from 'lucide-react'
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
import { businessApi, Business, BusinessStatus, BusinessDetail, AddonBusiness, AddonType, AddonStatus, CreateAddonSchema, UpdateAddonSchema } from '@/api/endpoints/business'
import { masterApi, Customer, SKU, PaginatedResponse } from '@/api/endpoints/master'
import { vcApi } from '@/api/endpoints/vc'
import { formatDate, formatCurrency, cn } from '@/lib/utils'

const STATUS_LABELS: Record<string, string> = {
  DRAFT: '草稿',
  INITIAL_CONTACT: '前期接洽',
  EVALUATION: '业务评估',
  FEEDBACK: '客户反馈',
  LANDING: '落地阶段',
  ACTIVE: '业务开展',
  PAUSED: '业务暂缓',
  TERMINATED: '业务终止',
  COMPLETED: '业务完成',
  前期接洽: '前期接洽',
  业务评估: '业务评估',
  方案设计: '方案设计',
  合作落地: '合作落地',
  业务开展: '业务开展',
}

const STATUS_COLORS: Record<string, string> = {
  DRAFT: 'bg-gray-100 text-gray-800',
  INITIAL_CONTACT: 'bg-blue-100 text-blue-800',
  EVALUATION: 'bg-indigo-100 text-indigo-800',
  FEEDBACK: 'bg-purple-100 text-purple-800',
  LANDING: 'bg-orange-100 text-orange-800',
  ACTIVE: 'bg-green-100 text-green-800',
  PAUSED: 'bg-yellow-100 text-yellow-800',
  TERMINATED: 'bg-red-100 text-red-800',
  COMPLETED: 'bg-gray-100 text-gray-800',
}

const ADDON_TYPE_LABELS: Record<string, string> = {
  PRICE_ADJUST: '价格调整',
  NEW_SKU: '新增SKU',
  价格调整: '价格调整',
  新增SKU: '新增SKU',
}

function CreateBusinessDialog({ onSuccess }: { onSuccess: () => void }) {
  const queryClient = useQueryClient()
  const [isOpen, setIsOpen] = useState(false)
  const [customerId, setCustomerId] = useState('')

  const { data: customers } = useQuery({
    queryKey: ['customers'],
    queryFn: () => masterApi.customers.list({ size: 100 }),
  })

  const createMutation = useMutation({
    mutationFn: () => businessApi.create({ customer_id: parseInt(customerId) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['business-list'] })
      setIsOpen(false)
      setCustomerId('')
      onSuccess()
    },
  })

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button><Plus className="mr-2 h-4 w-4" />新建业务</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>新建业务</DialogTitle>
        </DialogHeader>
        <form onSubmit={(e) => { e.preventDefault(); createMutation.mutate() }} className="space-y-4">
          <div className="space-y-2">
            <Label>客户</Label>
            <Select value={customerId} onValueChange={setCustomerId}>
              <SelectTrigger>
                <SelectValue placeholder="选择客户" />
              </SelectTrigger>
              <SelectContent>
                {customers?.items?.map(c => (
                  <SelectItem key={c.id} value={String(c.id)}>{c.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => setIsOpen(false)}>取消</Button>
            <Button type="submit" disabled={!customerId || createMutation.isPending}>
              {createMutation.isPending ? '创建中...' : '创建'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function DeleteBusinessDialog({ business, onSuccess }: { business: Business; onSuccess: () => void }) {
  const queryClient = useQueryClient()
  const [isOpen, setIsOpen] = useState(false)

  const { data: vcCount } = useQuery({
    queryKey: ['business-vc-count', business.id],
    queryFn: async () => {
      const res = await vcApi.list({ business_id: business.id, size: 1 })
      return res.total || 0
    },
    enabled: isOpen,
  })

  const deleteMutation = useMutation({
    mutationFn: () => businessApi.delete(business.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['business-list'] })
      setIsOpen(false)
      onSuccess()
    },
  })

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="sm"><Trash2 className="h-4 w-4" /></Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>删除业务</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          {vcCount && vcCount > 0 ? (
            <div className="flex items-start gap-3 p-4 bg-destructive/10 rounded-lg">
              <AlertTriangle className="h-5 w-5 text-destructive shrink-0 mt-0.5" />
              <div>
                <p className="font-medium text-destructive">无法删除</p>
                <p className="text-sm mt-1">该业务已关联 {vcCount} 个虚拟合同，请先删除所有关联合同后再尝试删除。</p>
              </div>
            </div>
          ) : (
            <p>确定要删除业务 BIZ-{business.id} ({business.customer_name}) 吗？此操作不可撤销。</p>
          )}
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setIsOpen(false)}>取消</Button>
            <Button
              variant="destructive"
              disabled={vcCount !== undefined && vcCount > 0 || deleteMutation.isPending}
              onClick={() => deleteMutation.mutate()}
            >
              {deleteMutation.isPending ? '删除中...' : '删除'}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}

interface PricingRow {
  sku_id: number
  sku_name: string
  price: string
  deposit: string
}

function AdvanceBusinessDialog({ business, onSuccess }: { business: Business; onSuccess: () => void }) {
  const queryClient = useQueryClient()
  const [isOpen, setIsOpen] = useState(false)
  const [formData, setFormData] = useState({
    next_status: '',
    comment: '',
    prepayment_ratio: '0',
    balance_period: '30',
    day_rule: '自然日',
    start_trigger: '入库日',
    contract_num: '',
  })
  const [equipRows, setEquipRows] = useState<PricingRow[]>([{ sku_id: 0, sku_name: '', price: '0', deposit: '0' }])
  const [matRows, setMatRows] = useState<PricingRow[]>([{ sku_id: 0, sku_name: '', price: '0', deposit: '0' }])

  const isLanding = business.status === '合作落地'

  const { data: allSkus } = useQuery({
    queryKey: ['skus-all'],
    queryFn: () => masterApi.skus.list({ size: 500 }),
    enabled: isLanding && isOpen,
  })

  const equipSkus = allSkus?.items?.filter(s => s.type_level1 === '设备') || []
  const matSkus = allSkus?.items?.filter(s => s.type_level1 === '物料') || []

  const stageOrder = ['前期接洽', '业务评估', '客户反馈', '合作落地', '业务开展', '业务完成'] as const
  const currentIndex = stageOrder.indexOf(business.status as typeof stageOrder[number])
  const nextStatus = currentIndex >= 0 && currentIndex < stageOrder.length - 1 ? stageOrder[currentIndex + 1] : null

  const handleEquipSkuChange = (idx: number, skuId: string) => {
    const sku = equipSkus.find(s => String(s.id) === skuId)
    setEquipRows(prev => prev.map((r, i) => i === idx ? { ...r, sku_id: parseInt(skuId) || 0, sku_name: sku?.name || '', deposit: sku?.deposit ? String(sku.deposit) : r.deposit } : r))
  }

  const handleMatSkuChange = (idx: number, skuId: string) => {
    const sku = matSkus.find(s => String(s.id) === skuId)
    setMatRows(prev => prev.map((r, i) => i === idx ? { ...r, sku_id: parseInt(skuId) || 0, sku_name: sku?.name || '', price: sku ? '0' : r.price } : r))
  }

  const advanceMutation = useMutation({
    mutationFn: () => {
      const pricing: Record<string, { price: number; deposit: number }> = {}
      if (isLanding) {
        equipRows.forEach(r => {
          if (r.sku_id && r.deposit && parseFloat(r.deposit) > 0) {
            pricing[String(r.sku_id)] = { price: 0, deposit: parseFloat(r.deposit) }
          }
        })
        matRows.forEach(r => {
          if (r.sku_id && r.price && parseFloat(r.price) > 0) {
            pricing[String(r.sku_id)] = { price: parseFloat(r.price), deposit: 0 }
          }
        })
      }
      return businessApi.advanceStage({
        business_id: business.id,
        next_status: formData.next_status as BusinessStatus,
        comment: formData.comment || undefined,
        ...(isLanding && {
          payment_terms: {
            prepayment_ratio: parseFloat(formData.prepayment_ratio) / 100 || 0,
            balance_period: parseInt(formData.balance_period) || 30,
            day_rule: formData.day_rule,
            start_trigger: formData.start_trigger,
          },
          pricing: Object.keys(pricing).length > 0 ? pricing : undefined,
          contract_num: formData.contract_num || undefined,
        }),
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['business-list'] })
      setIsOpen(false)
      onSuccess()
    },
  })

  return (
    <Dialog open={isOpen} onOpenChange={(open) => {
      setIsOpen(open)
      if (open) {
        setFormData({
          next_status: nextStatus || '',
          comment: '',
          prepayment_ratio: '0',
          balance_period: '30',
          day_rule: '自然日',
          start_trigger: '入库日',
          contract_num: '',
        })
        setEquipRows([{ sku_id: 0, sku_name: '', price: '0', deposit: '0' }])
        setMatRows([{ sku_id: 0, sku_name: '', price: '0', deposit: '0' }])
      }
    }}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" disabled={!nextStatus}>
          推进阶段
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {isLanding ? '确认并完成签约落地' : '推进业务阶段'}
          </DialogTitle>
        </DialogHeader>
        <form onSubmit={(e) => { e.preventDefault(); advanceMutation.mutate() }} className="space-y-6">
          {!isLanding && (
            <div className="space-y-2">
              <Label>推进至</Label>
              <Select value={formData.next_status} onValueChange={(v) => setFormData({ ...formData, next_status: v })}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {nextStatus && <SelectItem value={nextStatus}>{STATUS_LABELS[nextStatus]}</SelectItem>}
                </SelectContent>
              </Select>
            </div>
          )}

          {isLanding && (
            <>
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-sm text-blue-800">
                业务进入【业务开展】前，需完成商务结算协议的固化。
              </div>

              {/* 设备投放约定 */}
              <div className="space-y-3">
                <Label className="text-base font-medium">设备投放约定 (押金模式)</Label>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[200px]">设备品类</TableHead>
                      <TableHead className="w-[120px]">计划投放量</TableHead>
                      <TableHead>单台押金 (元)</TableHead>
                      <TableHead className="w-[50px]"></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {equipRows.map((row, idx) => (
                      <TableRow key={idx}>
                        <TableCell>
                          <Select value={String(row.sku_id) || ''} onValueChange={(v) => handleEquipSkuChange(idx, v)}>
                            <SelectTrigger>
                              <SelectValue placeholder="选择设备" />
                            </SelectTrigger>
                            <SelectContent>
                              {equipSkus.map(s => (
                                <SelectItem key={s.id} value={String(s.id)}>{s.name}</SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </TableCell>
                        <TableCell>
                          <Input type="number" min="0" value={row.price === '0' && row.sku_id === 0 ? '' : '1'} readOnly className="bg-gray-50" />
                        </TableCell>
                        <TableCell>
                          <Input
                            type="number"
                            min="0"
                            step="0.01"
                            value={row.deposit}
                            onChange={(e) => {
                              const newRows = [...equipRows]
                              newRows[idx] = { ...newRows[idx], deposit: e.target.value }
                              setEquipRows(newRows)
                            }}
                          />
                        </TableCell>
                        <TableCell>
                          <Button type="button" variant="ghost" size="sm" onClick={() => setEquipRows(r => r.filter((_, i) => i !== idx))}>
                            <X className="h-4 w-4" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
                <Button type="button" variant="outline" size="sm" onClick={() => setEquipRows(r => [...r, { sku_id: 0, sku_name: '', price: '0', deposit: '0' }])}>
                  <Plus className="mr-2 h-4 w-4" />添加设备
                </Button>
              </div>

              {/* 物料供货约定 */}
              <div className="space-y-3">
                <Label className="text-base font-medium">物料供货约定 (供货价格)</Label>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[200px]">物料品类</TableHead>
                      <TableHead>供货单价 (元)</TableHead>
                      <TableHead className="w-[50px]"></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {matRows.map((row, idx) => (
                      <TableRow key={idx}>
                        <TableCell>
                          <Select value={String(row.sku_id) || ''} onValueChange={(v) => handleMatSkuChange(idx, v)}>
                            <SelectTrigger>
                              <SelectValue placeholder="选择物料" />
                            </SelectTrigger>
                            <SelectContent>
                              {matSkus.map(s => (
                                <SelectItem key={s.id} value={String(s.id)}>{s.name}</SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </TableCell>
                        <TableCell>
                          <Input
                            type="number"
                            min="0"
                            step="0.01"
                            value={row.price}
                            onChange={(e) => {
                              const newRows = [...matRows]
                              newRows[idx] = { ...newRows[idx], price: e.target.value }
                              setMatRows(newRows)
                            }}
                          />
                        </TableCell>
                        <TableCell>
                          <Button type="button" variant="ghost" size="sm" onClick={() => setMatRows(r => r.filter((_, i) => i !== idx))}>
                            <X className="h-4 w-4" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
                <Button type="button" variant="outline" size="sm" onClick={() => setMatRows(r => [...r, { sku_id: 0, sku_name: '', price: '0', deposit: '0' }])}>
                  <Plus className="mr-2 h-4 w-4" />添加物料
                </Button>
              </div>

              {/* 结算条款 */}
              <div className="space-y-3">
                <Label className="text-base font-medium">财务结算条款</Label>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="space-y-2">
                    <Label className="text-xs">预付款比例 (%)</Label>
                    <Input type="number" min="0" max="100"
                      value={formData.prepayment_ratio}
                      onChange={(e) => setFormData({ ...formData, prepayment_ratio: e.target.value })} />
                  </div>
                  <div className="space-y-2">
                    <Label className="text-xs">尾款账期 (天)</Label>
                    <Input type="number" min="0"
                      value={formData.balance_period}
                      onChange={(e) => setFormData({ ...formData, balance_period: e.target.value })} />
                  </div>
                  <div className="space-y-2">
                    <Label className="text-xs">计日规则</Label>
                    <Select value={formData.day_rule} onValueChange={(v) => setFormData({ ...formData, day_rule: v })}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="自然日">自然日</SelectItem>
                        <SelectItem value="工作日">工作日</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label className="text-xs">起算锚点</Label>
                    <Select value={formData.start_trigger} onValueChange={(v) => setFormData({ ...formData, start_trigger: v })}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="入库日">入库日</SelectItem>
                        <SelectItem value="签收日">签收日</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>

              {/* 合同编号 */}
              <div className="space-y-2">
                <Label>正式合同编号</Label>
                <Input
                  value={formData.contract_num}
                  onChange={(e) => setFormData({ ...formData, contract_num: e.target.value })}
                  placeholder="选填"
                />
              </div>
            </>
          )}

          <div className="space-y-2">
            <Label>阶段推进小结/备注</Label>
            <Textarea
              value={formData.comment}
              onChange={(e) => setFormData({ ...formData, comment: e.target.value })}
              placeholder="请输入该阶段的关键信息..."
            />
          </div>

          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => setIsOpen(false)}>取消</Button>
            <Button type="submit" disabled={!formData.next_status && !isLanding || advanceMutation.isPending}>
              {advanceMutation.isPending ? '处理中...' : isLanding ? '确认并完成签约落地' : '确认推进'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}

// Addon Business Dialogs
function CreateAddonDialog({ business, onSuccess }: { business: Business; onSuccess: () => void }) {
  const queryClient = useQueryClient()
  const [isOpen, setIsOpen] = useState(false)
  const [addonType, setAddonType] = useState<AddonType>('PRICE_ADJUST')
  const [skuId, setSkuId] = useState('')
  const [startDate, setStartDate] = useState<Date | undefined>(new Date())
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)
  const [overrideVal, setOverrideVal] = useState('')
  const [remark, setRemark] = useState('')
  const [step, setStep] = useState<'type' | 'detail'>('type')

  const { data: allSkus } = useQuery({
    queryKey: ['skus-for-addon', business.id],
    queryFn: async () => {
      const skus = await masterApi.skus.list({ size: 500 })
      const detail = await businessApi.getDetail(business.id)
      const pricingSkuIds = new Set(Object.keys(detail.details?.pricing || {}).filter(k => !isNaN(parseInt(k))))
      return {
        skus: skus.items || [],
        pricingSkuIds,
      }
    },
    enabled: isOpen && step === 'type',
  })

  const { data: originalPrice } = useQuery({
    queryKey: ['addon-original-price', business.id, skuId],
    queryFn: async () => {
      if (!skuId) return null
      const detail = await businessApi.getDetail(business.id)
      const pricing = detail.details?.pricing?.[skuId]
      return pricing || null
    },
    enabled: isOpen && !!skuId && addonType === 'PRICE_ADJUST',
  })

  const selectedSku = allSkus?.skus.find(s => String(s.id) === skuId)
  const isEquipment = selectedSku?.type_level1 === '设备'
  const isMaterial = selectedSku?.type_level1 === '物料'

  const availableSkus = addonType === 'PRICE_ADJUST'
    ? allSkus?.skus.filter(s => allSkus.pricingSkuIds.has(String(s.id))) || []
    : allSkus?.skus.filter(s => !allSkus.pricingSkuIds.has(String(s.id))) || []

  const createMutation = useMutation({
    mutationFn: () => {
      const payload: CreateAddonSchema = {
        business_id: business.id,
        addon_type: addonType,
        sku_id: parseInt(skuId),
        start_date: startDate ? new Date(startDate).toISOString() : new Date().toISOString(),
        end_date: endDate ? new Date(endDate).toISOString() : undefined,
        remark: remark || undefined,
      }
      if (isEquipment && overrideVal) {
        payload.override_deposit = parseFloat(overrideVal)
      } else if (isMaterial && overrideVal) {
        payload.override_price = parseFloat(overrideVal)
      }
      return businessApi.createAddon(payload)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['business-addons', business.id] })
      setIsOpen(false)
      resetForm()
      onSuccess()
    },
  })

  const resetForm = () => {
    setAddonType('PRICE_ADJUST')
    setSkuId('')
    setStartDate(new Date())
    setEndDate(undefined)
    setOverrideVal('')
    setRemark('')
    setStep('type')
  }

  return (
    <Dialog open={isOpen} onOpenChange={(open) => { setIsOpen(open); if (!open) resetForm() }}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm"><Plus className="mr-2 h-4 w-4" />新建附加项</Button>
      </DialogTrigger>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>新建附加项</DialogTitle>
        </DialogHeader>
        {step === 'type' ? (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>附加项类型</Label>
              <Select value={addonType} onValueChange={(v) => { setAddonType(v as AddonType); setSkuId('') }}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="PRICE_ADJUST">价格调整 (PRICE_ADJUST)</SelectItem>
                  <SelectItem value="NEW_SKU">新增 SKU (NEW_SKU)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>选择 SKU</Label>
              {availableSkus.length > 0 ? (
                <Select value={skuId} onValueChange={setSkuId}>
                  <SelectTrigger>
                    <SelectValue placeholder="选择 SKU" />
                  </SelectTrigger>
                  <SelectContent>
                    {availableSkus.map(s => (
                      <SelectItem key={s.id} value={String(s.id)}>{s.name} ({s.type_level1})</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              ) : (
                <p className="text-sm text-muted-foreground">
                  {addonType === 'PRICE_ADJUST' ? '该业务下暂无已定价 SKU' : '所有 SKU 均已在业务中'}
                </p>
              )}
            </div>
            <div className="flex justify-end">
              <Button onClick={() => setStep('detail')} disabled={!skuId}>下一步</Button>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="text-sm text-muted-foreground">
              类型：{ADDON_TYPE_LABELS[addonType]} | SKU：{selectedSku?.name}
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>开始日期</Label>
                <Input
                  type="date"
                  value={startDate ? startDate.toISOString().slice(0, 10) : ''}
                  onChange={(e) => setStartDate(e.target.value ? new Date(e.target.value) : undefined)}
                />
              </div>
              <div className="space-y-2">
                <Label>结束日期（留空=永久）</Label>
                <Input
                  type="date"
                  value={endDate ? endDate.toISOString().slice(0, 10) : ''}
                  onChange={(e) => setEndDate(e.target.value ? new Date(e.target.value) : undefined)}
                />
              </div>
            </div>

            {isEquipment && (
              <div className="space-y-2">
                <Label>覆盖押金（元）</Label>
                <Input
                  type="number"
                  min="0"
                  step="0.01"
                  value={overrideVal}
                  onChange={(e) => setOverrideVal(e.target.value)}
                  placeholder={originalPrice?.deposit ? `原价: ${originalPrice.deposit}` : '请输入'}
                />
              </div>
            )}

            {isMaterial && (
              <div className="space-y-2">
                <Label>覆盖单价（元）</Label>
                <Input
                  type="number"
                  min="0"
                  step="0.01"
                  value={overrideVal}
                  onChange={(e) => setOverrideVal(e.target.value)}
                  placeholder={originalPrice?.price ? `原价: ${originalPrice.price}` : '请输入'}
                />
              </div>
            )}

            <div className="space-y-2">
              <Label>备注（可选）</Label>
              <Textarea value={remark} onChange={(e) => setRemark(e.target.value)} placeholder="选填" />
            </div>

            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setStep('type')}>返回</Button>
              <Button
                onClick={() => createMutation.mutate()}
                disabled={createMutation.isPending || (!overrideVal && (isEquipment || isMaterial))}
              >
                {createMutation.isPending ? '创建中...' : '创建'}
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}

function UpdateAddonDialog({ business, addon, onSuccess }: { business: Business; addon: AddonBusiness; onSuccess: () => void }) {
  const queryClient = useQueryClient()
  const [isOpen, setIsOpen] = useState(false)
  const [startDate, setStartDate] = useState<Date | undefined>(new Date(addon.start_date))
  const [endDate, setEndDate] = useState<Date | undefined>(addon.end_date ? new Date(addon.end_date) : undefined)
  const [overridePrice, setOverridePrice] = useState(addon.override_price?.toString() || '')
  const [overrideDeposit, setOverrideDeposit] = useState(addon.override_deposit?.toString() || '')
  const [remark, setRemark] = useState(addon.remark || '')

  const { data: detail } = useQuery({
    queryKey: ['addon-detail', addon.id],
    queryFn: () => businessApi.getAddonDetail(addon.id),
    enabled: isOpen,
  })

  const originalPrice = detail?.sku_id
    ? (() => {
        const d = detail
        return d ? { price: d.override_price, deposit: d.override_deposit } : null
      })()
    : null

  const updateMutation = useMutation({
    mutationFn: () => {
      const payload: UpdateAddonSchema = {
        addon_id: addon.id,
        start_date: startDate ? new Date(startDate).toISOString() : undefined,
        end_date: endDate ? new Date(endDate).toISOString() : undefined,
        remark: remark || undefined,
      }
      if (overridePrice) payload.override_price = parseFloat(overridePrice)
      if (overrideDeposit) payload.override_deposit = parseFloat(overrideDeposit)
      return businessApi.updateAddon(payload)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['business-addons', business.id] })
      setIsOpen(false)
      onSuccess()
    },
  })

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="sm"><Pencil className="h-4 w-4" /></Button>
      </DialogTrigger>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>编辑附加项 #{addon.id}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div className="text-sm text-muted-foreground">
            类型：{ADDON_TYPE_LABELS[addon.addon_type]} | SKU：{addon.sku_name}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>开始日期</Label>
              <Input
                type="date"
                value={startDate ? startDate.toISOString().slice(0, 10) : ''}
                onChange={(e) => setStartDate(e.target.value ? new Date(e.target.value) : undefined)}
              />
            </div>
            <div className="space-y-2">
              <Label>结束日期（留空=永久）</Label>
              <Input
                type="date"
                value={endDate ? endDate.toISOString().slice(0, 10) : ''}
                onChange={(e) => setEndDate(e.target.value ? new Date(e.target.value) : undefined)}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>覆盖单价（元）</Label>
              <Input
                type="number"
                min="0"
                step="0.01"
                value={overridePrice}
                onChange={(e) => setOverridePrice(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label>覆盖押金（元）</Label>
              <Input
                type="number"
                min="0"
                step="0.01"
                value={overrideDeposit}
                onChange={(e) => setOverrideDeposit(e.target.value)}
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label>备注</Label>
            <Textarea value={remark} onChange={(e) => setRemark(e.target.value)} />
          </div>

          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setIsOpen(false)}>取消</Button>
            <Button onClick={() => updateMutation.mutate()} disabled={updateMutation.isPending}>
              {updateMutation.isPending ? '保存中...' : '保存'}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}

function DeactivateAddonButton({ business, addon, onSuccess }: { business: Business; addon: AddonBusiness; onSuccess: () => void }) {
  const queryClient = useQueryClient()
  const [isOpen, setIsOpen] = useState(false)

  const deactivateMutation = useMutation({
    mutationFn: () => businessApi.deactivateAddon(addon.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['business-addons', business.id] })
      setIsOpen(false)
      onSuccess()
    },
  })

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" className="text-orange-600">失效</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>使附加项失效</DialogTitle>
        </DialogHeader>
        <p>确定要让附加项 #{addon.id} ({addon.sku_name}) 失效吗？</p>
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={() => setIsOpen(false)}>取消</Button>
          <Button variant="destructive" onClick={() => deactivateMutation.mutate()} disabled={deactivateMutation.isPending}>
            {deactivateMutation.isPending ? '处理中...' : '确认失效'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}

function BusinessDetailDialog({ business, onClose }: { business: Business; onClose: () => void }) {
  const [activeTab, setActiveTab] = useState('detail')

  const { data: detail, isLoading } = useQuery({
    queryKey: ['business-detail', business.id],
    queryFn: () => businessApi.getDetail(business.id),
    enabled: activeTab === 'detail',
  })

  const { data: addonsData } = useQuery({
    queryKey: ['business-addons', business.id],
    queryFn: async () => {
      const res = await businessApi.listAddons(business.id, true)
      return res || []
    },
    enabled: activeTab === 'addons',
  })

  const { data: vcs } = useQuery({
    queryKey: ['business-vcs', business.id],
    queryFn: () => vcApi.list({ business_id: business.id, size: 100 }),
    enabled: activeTab === 'vcs',
  })

  const isActive = detail?.status === '业务开展'

  return (
    <Dialog open onOpenChange={() => onClose()}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <span>业务-{business.id}</span>
            <Badge className={STATUS_COLORS[business.status]}>{STATUS_LABELS[detail?.status || business.status]}</Badge>
          </DialogTitle>
        </DialogHeader>

        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList>
            <TabsTrigger value="detail">详情</TabsTrigger>
            <TabsTrigger value="vcs">关联合同</TabsTrigger>
            <TabsTrigger value="addons">附加业务</TabsTrigger>
          </TabsList>

          <TabsContent value="detail">
            {isLoading ? (
              <div className="text-center py-4">加载中...</div>
            ) : detail ? (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label className="text-muted-foreground">客户</Label>
                    <p>{detail.customer_name}</p>
                  </div>
                  <div>
                    <Label className="text-muted-foreground">当前状态</Label>
                    <p>{STATUS_LABELS[detail.status]}</p>
                  </div>
                </div>

                {/* Stage History */}
                {detail.details?.history && detail.details.history.length > 0 && (
                  <div>
                    <Label className="mb-2">阶段历史</Label>
                    <div className="space-y-2">
                      {detail.details.history.map((h, idx) => (
                        <div key={idx} className="flex items-center gap-2 text-sm">
                          <ChevronRight className="h-4 w-4 text-muted-foreground" />
                          <span className="text-muted-foreground">{formatDate(h.time)}</span>
                          <span>{STATUS_LABELS[h.from as BusinessStatus] || h.from} → {STATUS_LABELS[h.to as BusinessStatus] || h.to}</span>
                          {h.comment && <span className="text-muted-foreground">({h.comment})</span>}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Pricing */}
                {detail.details?.pricing && Object.keys(detail.details.pricing).length > 0 && (
                  <div>
                    <Label className="mb-2">协议定价</Label>
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>SKU</TableHead>
                          <TableHead className="text-right">单价</TableHead>
                          <TableHead className="text-right">押金</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {Object.entries(detail.details.pricing).map(([skuId, p]) => {
                          const price = typeof p === 'object' ? p.price : undefined
                          const deposit = typeof p === 'object' ? p.deposit : undefined
                          return (
                            <TableRow key={skuId}>
                              <TableCell>SKU-{skuId}</TableCell>
                              <TableCell className="text-right">{price !== undefined ? formatCurrency(price) : '-'}</TableCell>
                              <TableCell className="text-right">{deposit !== undefined ? formatCurrency(deposit) : '-'}</TableCell>
                            </TableRow>
                          )
                        })}
                      </TableBody>
                    </Table>
                  </div>
                )}

                {/* Payment Terms */}
                {detail.details?.payment_terms && (
                  <div>
                    <Label className="mb-2">结算条款</Label>
                    <div className="grid grid-cols-4 gap-2 text-sm">
                      <div>预付款比例: {(detail.details.payment_terms.prepayment_ratio * 100).toFixed(0)}%</div>
                      <div>账期: {detail.details.payment_terms.balance_period}天</div>
                      <div>日期规则: {detail.details.payment_terms.day_rule}</div>
                      <div>起算: {detail.details.payment_terms.start_trigger}</div>
                    </div>
                  </div>
                )}

                {detail.details?.notes && (
                  <div>
                    <Label className="text-muted-foreground">备注</Label>
                    <p>{detail.details.notes}</p>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-4">无数据</div>
            )}
          </TabsContent>

          <TabsContent value="vcs">
            {vcs?.items && vcs.items.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>ID</TableHead>
                    <TableHead>类型</TableHead>
                    <TableHead>描述</TableHead>
                    <TableHead>状态</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {vcs.items.map(vc => (
                    <TableRow key={vc.id}>
                      <TableCell>VC-{vc.id}</TableCell>
                      <TableCell>{vc.type}</TableCell>
                      <TableCell>{vc.description?.slice(0, 30) || '-'}</TableCell>
                      <TableCell><Badge>{vc.status}</Badge></TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <div className="text-center py-4 text-muted-foreground">暂无关联合同</div>
            )}
          </TabsContent>

          <TabsContent value="addons">
            {isActive && (
              <div className="mb-4">
                <CreateAddonDialog business={business} onSuccess={() => {}} />
              </div>
            )}
            {addonsData && addonsData.length > 0 ? (
              <div className="space-y-2">
                {addonsData.map(addon => (
                  <Card key={addon.id}>
                    <CardContent className="pt-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <Badge variant="outline">{ADDON_TYPE_LABELS[addon.addon_type]}</Badge>
                          <span>{addon.sku_name || `SKU-${addon.sku_id}`}</span>
                          <span className="text-sm text-muted-foreground">
                            {addon.start_date?.slice(0, 10)} ~ {addon.end_date?.slice(0, 10) || '永久'}
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          {isActive && (
                            <>
                              <UpdateAddonDialog business={business} addon={addon} onSuccess={() => {}} />
                              <DeactivateAddonButton business={business} addon={addon} onSuccess={() => {}} />
                            </>
                          )}
                          <Badge className={addon.status === '生效' ? 'bg-green-100 text-green-800' : 'bg-gray-100'}>
                            {addon.status}
                          </Badge>
                        </div>
                      </div>
                      {(addon.override_price || addon.override_deposit) && (
                        <div className="flex gap-4 mt-2 text-sm text-muted-foreground">
                          {addon.override_price !== undefined && <span>覆盖单价: {formatCurrency(addon.override_price)}</span>}
                          {addon.override_deposit !== undefined && <span>覆盖押金: {formatCurrency(addon.override_deposit)}</span>}
                        </div>
                      )}
                      {addon.remark && <p className="text-sm mt-2">{addon.remark}</p>}
                    </CardContent>
                  </Card>
                ))}
              </div>
            ) : (
              <div className="text-center py-4 text-muted-foreground">暂无附加业务</div>
            )}
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  )
}

export function BusinessPage() {
  const [statusFilter, setStatusFilter] = useState<BusinessStatus | 'ALL'>('ALL')
  const [selectedBusiness, setSelectedBusiness] = useState<Business | null>(null)

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['business-list', statusFilter],
    queryFn: () => businessApi.list({
      status: statusFilter !== 'ALL' ? statusFilter : undefined,
      size: 100,
    }),
  })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">业务管理</h2>
        <CreateBusinessDialog onSuccess={() => refetch()} />
      </div>

      {/* Filters */}
      <div className="flex gap-4 flex-wrap">
        <Select value={statusFilter} onValueChange={(v) => setStatusFilter(v as BusinessStatus | 'ALL')}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="状态" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="ALL">全部状态</SelectItem>
            {Object.entries(STATUS_LABELS).map(([value, label]) => (
              <SelectItem key={value} value={value}>{label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button variant="outline" onClick={() => refetch()}>
          <RefreshCw className="h-4 w-4" />
        </Button>
      </div>

      {/* Business List */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>客户</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>创建时间</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data?.items?.map(b => (
                <TableRow key={b.id}>
                  <TableCell className="font-medium">BIZ-{b.id}</TableCell>
                  <TableCell>{b.customer_name}</TableCell>
                  <TableCell>
                    <Badge className={STATUS_COLORS[b.status]}>{STATUS_LABELS[b.status]}</Badge>
                  </TableCell>
                  <TableCell>{formatDate(b.created_at || '')}</TableCell>
                  <TableCell>
                    <div className="flex gap-2">
                      <Button variant="ghost" size="sm" onClick={() => setSelectedBusiness(b)}>
                        详情
                      </Button>
                      <AdvanceBusinessDialog business={b} onSuccess={() => refetch()} />
                      <DeleteBusinessDialog business={b} onSuccess={() => refetch()} />
                    </div>
                  </TableCell>
                </TableRow>
              ))}
              {!data?.items?.length && (
                <TableRow>
                  <TableCell colSpan={5} className="text-center text-muted-foreground">
                    {isLoading ? '加载中...' : '暂无数据'}
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {selectedBusiness && (
        <BusinessDetailDialog business={selectedBusiness} onClose={() => setSelectedBusiness(null)} />
      )}
    </div>
  )
}
