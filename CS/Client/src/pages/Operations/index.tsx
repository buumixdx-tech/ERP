import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, RefreshCw, X, Pencil, Trash2, ChevronRight, AlertCircle } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import {
  businessApi, Business, BusinessStatus, AddonBusiness, AddonType,
  CreateAddonSchema, UpdateAddonSchema, StageTransition, BusinessListResponse,
} from '@/api/endpoints/business'
import { masterApi, Customer, SKU } from '@/api/endpoints/master'
import { vcApi } from '@/api/endpoints/vc'
import { rulesApi, TimeRule, RuleRelatedType, RuleParty, RuleUnit, RuleDirection, RuleInherit, RULE_EVENTS, CreateTimeRuleSchema } from '@/api/endpoints/rules'
import { formatDate, formatCurrency } from '@/lib/utils'

const STATUS_LABELS: Record<string, string> = {
  前期接洽: '前期接洽',
  业务评估: '业务评估',
  客户反馈: '客户反馈',
  合作落地: '合作落地',
  业务开展: '业务开展',
  暂停: '暂停',
  终止: '终止',
  业务完成: '业务完成',
}

const STATUS_COLORS: Record<string, string> = {
  前期接洽: 'bg-gray-100 text-gray-800',
  业务评估: 'bg-blue-100 text-blue-800',
  客户反馈: 'bg-indigo-100 text-indigo-800',
  合作落地: 'bg-orange-100 text-orange-800',
  业务开展: 'bg-green-100 text-green-800',
  暂停: 'bg-yellow-100 text-yellow-800',
  终止: 'bg-red-100 text-red-800',
  业务完成: 'bg-gray-100 text-gray-800',
}

const RULE_STATUS_COLORS: Record<string, string> = {
  '失效': 'bg-gray-100 text-gray-800',
  '模板': 'bg-purple-100 text-purple-800',
  '生效': 'bg-blue-100 text-blue-800',
  '有结果': 'bg-cyan-100 text-cyan-800',
  '结束': 'bg-gray-100 text-gray-800',
}

const INCLUSION_PHASE = ['前期接洽', '业务评估', '客户反馈', '合作落地']

const NEXT_STATUS_MAP: Record<string, string | null> = {
  前期接洽: '业务评估',
  业务评估: '客户反馈',
  客户反馈: '合作落地',
  合作落地: '业务开展',
  业务开展: '业务完成',
  暂停: null,
  终止: null,
  业务完成: null,
}

const ADDON_TYPE_LABELS: Record<string, string> = {
  PRICE_ADJUST: '价格调整',
  NEW_SKU: '新增SKU',
  PAYMENT_TERMS: '付款条款',
}

interface PricingRow {
  sku_id: number
  sku_name: string
  price: string
  deposit: string
}

// ─── Customer Inclusion Tab ────────────────────────────────────────────────────

function CustomerInclusionTab() {
  const queryClient = useQueryClient()
  const [customerId, setCustomerId] = useState('')
  const [advancingBiz, setAdvancingBiz] = useState<Business | null>(null)
  const [comment, setComment] = useState('')
  const [equipRows, setEquipRows] = useState<PricingRow[]>([{ sku_id: 0, sku_name: '', price: '0', deposit: '0' }])
  const [matRows, setMatRows] = useState<PricingRow[]>([{ sku_id: 0, sku_name: '', price: '0', deposit: '0' }])
  const [paymentTerms, setPaymentTerms] = useState({ prepayment_ratio: '0', balance_period: '30', day_rule: '自然日', start_trigger: '入库日' })
  const [contractNum, setContractNum] = useState('')

  const { data: customers } = useQuery({
    queryKey: ['customers'],
    queryFn: () => masterApi.customers.list({ size: 100 }),
  })

  const { data: inclusionBizData, isLoading, refetch } = useQuery<BusinessListResponse>({
    queryKey: ['business-inclusion'],
    queryFn: () => businessApi.list({ size: 500 }),
  })

  const filteredBiz = inclusionBizData?.items?.filter(b => INCLUSION_PHASE.includes(b.status)) || []

  const { data: allSkus } = useQuery({
    queryKey: ['skus-all'],
    queryFn: () => masterApi.skus.list({ size: 500 }),
    enabled: !!advancingBiz,
  })

  const equipSkus = allSkus?.items?.filter((s: SKU) => s.type_level1 === '设备') || []
  const matSkus = allSkus?.items?.filter((s: SKU) => s.type_level1 === '物料') || []

  const isLanding = advancingBiz?.status === '合作落地'
  const nextStatus = advancingBiz ? NEXT_STATUS_MAP[advancingBiz.status] : null

  const createMutation = useMutation({
    mutationFn: () => businessApi.create({ customer_id: parseInt(customerId) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['business-inclusion'] })
      setCustomerId('')
    },
  })

  const advanceMutation = useMutation({
    mutationFn: () => {
      if (!advancingBiz || !nextStatus) return Promise.reject()
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
        business_id: advancingBiz.id,
        next_status: nextStatus,
        comment: comment || undefined,
        ...(isLanding && {
          payment_terms: {
            prepayment_ratio: parseFloat(paymentTerms.prepayment_ratio) / 100 || 0,
            balance_period: parseInt(paymentTerms.balance_period) || 30,
            day_rule: paymentTerms.day_rule,
            start_trigger: paymentTerms.start_trigger,
          },
          pricing: Object.keys(pricing).length > 0 ? pricing : undefined,
          contract_num: contractNum || undefined,
        }),
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['business-inclusion'] })
      setAdvancingBiz(null)
      resetLandingForm()
    },
  })

  const pauseMutation = useMutation({
    mutationFn: (bizId: number) => businessApi.updateStatus({ business_id: bizId, status: 'PAUSED' as BusinessStatus }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['business-inclusion'] }),
  })

  const terminateMutation = useMutation({
    mutationFn: (bizId: number) => businessApi.updateStatus({ business_id: bizId, status: '终止' as BusinessStatus }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['business-inclusion'] }),
  })

  const resetLandingForm = () => {
    setEquipRows([{ sku_id: 0, sku_name: '', price: '0', deposit: '0' }])
    setMatRows([{ sku_id: 0, sku_name: '', price: '0', deposit: '0' }])
    setPaymentTerms({ prepayment_ratio: '0', balance_period: '30', day_rule: '自然日', start_trigger: '入库日' })
    setContractNum('')
    setComment('')
  }

  const openAdvance = (biz: Business) => {
    setAdvancingBiz(biz)
    resetLandingForm()
  }

  const handleEquipSkuChange = (idx: number, skuId: string) => {
    const sku = equipSkus.find((s: SKU) => String(s.id) === skuId)
    setEquipRows(prev => prev.map((r, i) => i === idx ? { ...r, sku_id: parseInt(skuId) || 0, sku_name: sku?.name || '', deposit: sku?.deposit ? String(sku.deposit) : r.deposit } : r))
  }

  const handleMatSkuChange = (idx: number, skuId: string) => {
    const sku = matSkus.find((s: SKU) => String(s.id) === skuId)
    setMatRows(prev => prev.map((r, i) => i === idx ? { ...r, sku_id: parseInt(skuId) || 0, sku_name: sku?.name || '', price: sku ? '0' : r.price } : r))
  }

  return (
    <div className="space-y-6">
      {/* New Business Creation */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">发起新业务条目</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-end gap-4">
            <div className="space-y-2 flex-1">
              <Label>选择目标客户主体</Label>
              <Select value={customerId} onValueChange={setCustomerId}>
                <SelectTrigger><SelectValue placeholder="选择客户" /></SelectTrigger>
                <SelectContent>
                  {(customers?.items || []).map((c: Customer) => (
                    <SelectItem key={c.id} value={String(c.id)}>{c.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Button onClick={() => createMutation.mutate()} disabled={!customerId || createMutation.isPending}>
              {createMutation.isPending ? '创建中...' : '建立业务关联'}
            </Button>
          </div>
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-sm text-blue-800">
            创建后，业务将默认进入【草稿】状态
          </div>
        </CardContent>
      </Card>

      <div>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">现有业务列表 (导入/评估阶段)</h3>
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>

        {isLoading ? (
          <div className="text-center py-8 text-muted-foreground">加载中...</div>
        ) : filteredBiz.length === 0 ? (
          <Card>
            <CardContent className="py-8 text-center text-muted-foreground">
              当前暂无处于导入/评估阶段的业务
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-4">
            <Card>
              <CardContent className="p-0">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>业务ID</TableHead>
                      <TableHead>客户主体</TableHead>
                      <TableHead>当前阶段</TableHead>
                      <TableHead>建立日期</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredBiz.map((b: Business) => (
                      <TableRow key={b.id}>
                        <TableCell className="font-medium">BIZ-{b.id}</TableCell>
                        <TableCell>{b.customer_name}</TableCell>
                        <TableCell><Badge className={STATUS_COLORS[b.status]}>{STATUS_LABELS[b.status]}</Badge></TableCell>
                        <TableCell>{b.created_at?.slice(0, 10) || '今日'}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>

            <h4 className="text-base font-medium">阶段推进操作</h4>
            <div className="space-y-4">
              {filteredBiz.map((biz: Business) => {
                const next = NEXT_STATUS_MAP[biz.status]
                return (
                  <Card key={biz.id}>
                    <CardHeader className="pb-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="font-medium">ID: {biz.id}</span>
                          <span>|</span>
                          <span>{biz.customer_name}</span>
                          <Badge className={STATUS_COLORS[biz.status]}>{STATUS_LABELS[biz.status]}</Badge>
                        </div>
                        <div className="flex gap-2">
                          {next && (
                            <Button variant="default" size="sm" onClick={() => openAdvance(biz)}>
                              推进至 {STATUS_LABELS[next]}
                            </Button>
                          )}
                          <Button variant="outline" size="sm" onClick={() => pauseMutation.mutate(biz.id)}>
                            业务暂缓
                          </Button>
                          <Button variant="destructive" size="sm" onClick={() => terminateMutation.mutate(biz.id)}>
                            业务终止
                          </Button>
                        </div>
                      </div>
                    </CardHeader>
                  </Card>
                )
              })}
            </div>
          </div>
        )}
      </div>

      <Dialog open={!!advancingBiz} onOpenChange={(open) => { if (!open) { setAdvancingBiz(null); resetLandingForm() } }}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {isLanding ? '确认并完成签约落地' : `推进至 ${nextStatus ? STATUS_LABELS[nextStatus] : ''}`}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-6">
            {isLanding && (
              <>
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-sm text-blue-800">
                  业务进入【业务开展】前，需完成商务结算协议的固化。
                </div>

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
                              <SelectTrigger><SelectValue placeholder="选择设备" /></SelectTrigger>
                              <SelectContent>
                                {equipSkus.map((s: SKU) => <SelectItem key={s.id} value={String(s.id)}>{s.name}</SelectItem>)}
                              </SelectContent>
                            </Select>
                          </TableCell>
                          <TableCell><Input type="number" min="0" value="1" readOnly className="bg-gray-50" /></TableCell>
                          <TableCell>
                            <Input type="number" min="0" step="0.01" value={row.deposit}
                              onChange={(e) => { const nr = [...equipRows]; nr[idx] = { ...nr[idx], deposit: e.target.value }; setEquipRows(nr) }} />
                          </TableCell>
                          <TableCell>
                            <Button type="button" variant="ghost" size="sm" onClick={() => setEquipRows(r => r.filter((_, i) => i !== idx))}><X className="h-4 w-4" /></Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                  <Button type="button" variant="outline" size="sm" onClick={() => setEquipRows(r => [...r, { sku_id: 0, sku_name: '', price: '0', deposit: '0' }])}>
                    <Plus className="mr-2 h-4 w-4" />添加设备
                  </Button>
                </div>

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
                              <SelectTrigger><SelectValue placeholder="选择物料" /></SelectTrigger>
                              <SelectContent>
                                {matSkus.map((s: SKU) => <SelectItem key={s.id} value={String(s.id)}>{s.name}</SelectItem>)}
                              </SelectContent>
                            </Select>
                          </TableCell>
                          <TableCell>
                            <Input type="number" min="0" step="0.01" value={row.price}
                              onChange={(e) => { const nr = [...matRows]; nr[idx] = { ...nr[idx], price: e.target.value }; setMatRows(nr) }} />
                          </TableCell>
                          <TableCell>
                            <Button type="button" variant="ghost" size="sm" onClick={() => setMatRows(r => r.filter((_, i) => i !== idx))}><X className="h-4 w-4" /></Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                  <Button type="button" variant="outline" size="sm" onClick={() => setMatRows(r => [...r, { sku_id: 0, sku_name: '', price: '0', deposit: '0' }])}>
                    <Plus className="mr-2 h-4 w-4" />添加物料
                  </Button>
                </div>

                <div className="space-y-3">
                  <Label className="text-base font-medium">财务结算条款</Label>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="space-y-2">
                      <Label className="text-xs">预付款比例 (%)</Label>
                      <Input type="number" min="0" max="100" value={paymentTerms.prepayment_ratio}
                        onChange={(e) => setPaymentTerms(p => ({ ...p, prepayment_ratio: e.target.value }))} />
                    </div>
                    <div className="space-y-2">
                      <Label className="text-xs">尾款账期 (天)</Label>
                      <Input type="number" min="0" value={paymentTerms.balance_period}
                        onChange={(e) => setPaymentTerms(p => ({ ...p, balance_period: e.target.value }))} />
                    </div>
                    <div className="space-y-2">
                      <Label className="text-xs">计日规则</Label>
                      <Select value={paymentTerms.day_rule} onValueChange={(v) => setPaymentTerms(p => ({ ...p, day_rule: v }))}>
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="自然日">自然日</SelectItem>
                          <SelectItem value="工作日">工作日</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label className="text-xs">起算锚点</Label>
                      <Select value={paymentTerms.start_trigger} onValueChange={(v) => setPaymentTerms(p => ({ ...p, start_trigger: v }))}>
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="入库日">入库日</SelectItem>
                          <SelectItem value="签收日">签收日</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label>正式合同编号</Label>
                  <Input value={contractNum} onChange={(e) => setContractNum(e.target.value)} placeholder="选填" />
                </div>
              </>
            )}

            <div className="space-y-2">
              <Label>阶段推进小结/备注</Label>
              <Textarea value={comment} onChange={(e) => setComment(e.target.value)} placeholder="请输入该阶段的关键信息..." />
            </div>

            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => { setAdvancingBiz(null); resetLandingForm() }}>取消</Button>
              <Button onClick={() => advanceMutation.mutate()} disabled={advanceMutation.isPending}>
                {advanceMutation.isPending ? '处理中...' : isLanding ? '确认并完成签约落地' : '确认推进'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}

// ─── Business Overview Panel ───────────────────────────────────────────────────

function BusinessOverviewPanel() {
  const [statusFilter, setStatusFilter] = useState<string[]>(['合作落地', '业务开展'])
  const [selectedBiz, setSelectedBiz] = useState<Business | null>(null)
  const [bizTab, setBizTab] = useState('detail')
  const [detailsJson, setDetailsJson] = useState('')
  const [editStatus, setEditStatus] = useState<string>('业务开展')
  const queryClient = useQueryClient()

  const ALL_STATUSES: BusinessStatus[] = ['前期接洽', '业务评估', '客户反馈', '合作落地', '业务开展', '暂停', '终止', '业务完成']

  const { data: businessesData, isLoading, refetch } = useQuery<BusinessListResponse>({
    queryKey: ['business-overview', statusFilter],
    queryFn: () => businessApi.list({ size: 500 }),
  })

  const filteredBiz = businessesData?.items?.filter((b: Business) => statusFilter.includes(b.status)) || []

  const { data: bizDetail } = useQuery({
    queryKey: ['business-detail', selectedBiz?.id],
    queryFn: () => selectedBiz ? businessApi.getDetail(selectedBiz.id) : Promise.reject(),
    enabled: !!selectedBiz && bizTab === 'detail',
  })

  const { data: bizVcs } = useQuery({
    queryKey: ['business-vcs', selectedBiz?.id],
    queryFn: () => selectedBiz ? vcApi.list({ business_id: selectedBiz.id, size: 100 }) : Promise.reject(),
    enabled: !!selectedBiz && bizTab === 'vcs',
  })

  const { data: bizRules } = useQuery({
    queryKey: ['business-rules', selectedBiz?.id],
    queryFn: () => selectedBiz ? rulesApi.list({ related_id: selectedBiz.id, related_type: '业务', size: 100 }) : Promise.reject(),
    enabled: !!selectedBiz && bizTab === 'rules',
  })

  const updateStatusMutation = useMutation({
    mutationFn: (data: { business_id: number; status: string; details?: object }) =>
      businessApi.updateStatus(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['business-overview'] })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (bizId: number) => businessApi.delete(bizId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['business-overview'] })
      setSelectedBiz(null)
    },
  })

  const { data: vcCount } = useQuery({
    queryKey: ['business-vc-count', selectedBiz?.id],
    queryFn: async () => {
      if (!selectedBiz) return 0
      const res = await vcApi.list({ business_id: selectedBiz.id, size: 1 })
      return res.total || 0
    },
    enabled: !!selectedBiz && bizTab === 'data',
  })

  const handleSelectBiz = (biz: Business) => {
    setSelectedBiz(biz)
    setBizTab('detail')
    businessApi.getDetail(biz.id).then(d => {
      setDetailsJson(JSON.stringify(d.details || {}, null, 2))
      setEditStatus(d.status)
    })
  }

  const handleSaveDetails = () => {
    if (!selectedBiz) return
    try {
      const details = JSON.parse(detailsJson)
      updateStatusMutation.mutate({ business_id: selectedBiz.id, status: editStatus, details })
    } catch {
      alert('JSON 格式错误')
    }
  }

  const toggleStatus = (s: BusinessStatus) => {
    setStatusFilter(prev => prev.includes(s) ? prev.filter(x => x !== s) : [...prev, s])
  }

  return (
    <div className="space-y-4">
      <div className="flex gap-2 flex-wrap">
        {ALL_STATUSES.map(s => (
          <Button
            key={s}
            variant={statusFilter.includes(s) ? 'default' : 'outline'}
            size="sm"
            onClick={() => toggleStatus(s)}
          >
            {STATUS_LABELS[s]}
          </Button>
        ))}
        <Button variant="outline" size="sm" onClick={() => refetch()}>
          <RefreshCw className="h-4 w-4" />
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ID</TableHead>
                  <TableHead>客户</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>创建时间</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredBiz.map((b: Business) => (
                  <TableRow
                    key={b.id}
                    className={`cursor-pointer ${selectedBiz?.id === b.id ? 'bg-muted' : ''}`}
                    onClick={() => handleSelectBiz(b)}
                  >
                    <TableCell className="font-medium">BIZ-{b.id}</TableCell>
                    <TableCell>{b.customer_name}</TableCell>
                    <TableCell><Badge className={STATUS_COLORS[b.status]}>{STATUS_LABELS[b.status]}</Badge></TableCell>
                    <TableCell className="text-sm">{formatDate(b.created_at || '')}</TableCell>
                  </TableRow>
                ))}
                {!filteredBiz.length && (
                  <TableRow>
                    <TableCell colSpan={4} className="text-center text-muted-foreground">
                      {isLoading ? '加载中...' : '暂无数据'}
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        {selectedBiz && (
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-base">业务详情 (ID: {selectedBiz.id})</CardTitle>
              <Button variant="ghost" size="sm" onClick={() => setSelectedBiz(null)}><X className="h-4 w-4" /></Button>
            </CardHeader>
            <CardContent>
              <Tabs value={bizTab} onValueChange={setBizTab}>
                <TabsList className="grid grid-cols-4 w-full">
                  <TabsTrigger value="detail">业务明细</TabsTrigger>
                  <TabsTrigger value="vcs">关联合同</TabsTrigger>
                  <TabsTrigger value="data">数据修正</TabsTrigger>
                  <TabsTrigger value="rules">规则管理</TabsTrigger>
                </TabsList>

                <TabsContent value="detail" className="space-y-4">
                  {bizDetail ? (
                    <>
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <Label className="text-muted-foreground">客户</Label>
                          <p className="font-medium">{bizDetail.customer_name}</p>
                        </div>
                        <div>
                          <Label className="text-muted-foreground">当前状态</Label>
                          <p className="font-medium">{STATUS_LABELS[bizDetail.status]}</p>
                        </div>
                      </div>

                      {bizDetail.details?.history && bizDetail.details.history.length > 0 && (
                        <div>
                          <Label className="mb-2 block">阶段历史</Label>
                          <div className="space-y-1">
                            {bizDetail.details.history.map((h: StageTransition, idx: number) => (
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

                      {bizDetail.details?.pricing && Object.keys(bizDetail.details.pricing).length > 0 && (
                        <div>
                          <Label className="mb-2 block">协议定价</Label>
                          <Table>
                            <TableHeader><TableRow><TableHead>SKU</TableHead><TableHead className="text-right">单价</TableHead><TableHead className="text-right">押金</TableHead></TableRow></TableHeader>
                            <TableBody>
                              {Object.entries(bizDetail.details.pricing).map(([skuId, p]) => (
                                <TableRow key={skuId}>
                                  <TableCell>SKU-{skuId}</TableCell>
                                  <TableCell className="text-right">{typeof p === 'object' && p.price !== undefined ? formatCurrency(p.price) : '-'}</TableCell>
                                  <TableCell className="text-right">{typeof p === 'object' && p.deposit !== undefined ? formatCurrency(p.deposit) : '-'}</TableCell>
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        </div>
                      )}

                      {bizDetail.details?.payment_terms && (
                        <div className="grid grid-cols-4 gap-2 text-sm">
                          <div>预付: {(bizDetail.details.payment_terms.prepayment_ratio * 100).toFixed(0)}%</div>
                          <div>账期: {bizDetail.details.payment_terms.balance_period}天</div>
                          <div>规则: {bizDetail.details.payment_terms.day_rule}</div>
                          <div>起算: {bizDetail.details.payment_terms.start_trigger}</div>
                        </div>
                      )}
                    </>
                  ) : <div className="text-center py-4">加载中...</div>}
                </TabsContent>

                <TabsContent value="vcs">
                  {bizVcs?.items && bizVcs.items.length > 0 ? (
                    <Table>
                      <TableHeader><TableRow><TableHead>ID</TableHead><TableHead>类型</TableHead><TableHead>描述</TableHead><TableHead>状态</TableHead></TableRow></TableHeader>
                      <TableBody>
                        {bizVcs.items.map(vc => (
                          <TableRow key={vc.id}>
                            <TableCell>VC-{vc.id}</TableCell>
                            <TableCell>{vc.type}</TableCell>
                            <TableCell>{vc.description?.slice(0, 30) || '-'}</TableCell>
                            <TableCell><Badge variant="outline">{vc.status}</Badge></TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  ) : (
                    <div className="text-center py-4 text-muted-foreground">暂无关联合同</div>
                  )}
                </TabsContent>

                <TabsContent value="data" className="space-y-4">
                  <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 text-sm text-yellow-800 flex items-start gap-2">
                    <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
                    此处修改直接影响数据库底层数据，请谨慎操作
                  </div>

                  <div className="space-y-2">
                    <Label>业务详情数据 (JSON 格式)</Label>
                    <Textarea
                      value={detailsJson}
                      onChange={(e) => setDetailsJson(e.target.value)}
                      className="font-mono text-sm"
                      rows={12}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label>业务状态</Label>
                    <Select value={editStatus} onValueChange={(v) => setEditStatus(v as BusinessStatus)}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {ALL_STATUSES.map(s => <SelectItem key={s} value={s}>{STATUS_LABELS[s]}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="flex gap-2">
                    <Button onClick={handleSaveDetails} disabled={updateStatusMutation.isPending}>
                      {updateStatusMutation.isPending ? '保存中...' : '确认并更新业务数据'}
                    </Button>
                    <Button
                      variant="destructive"
                      disabled={!!vcCount}
                      onClick={() => selectedBiz && deleteMutation.mutate(selectedBiz.id)}
                    >
                      删除此业务
                    </Button>
                    {vcCount !== undefined && vcCount > 0 && (
                      <span className="text-sm text-muted-foreground self-center">该业务下有 {vcCount} 个关联虚拟合同，无法删除</span>
                    )}
                  </div>
                </TabsContent>

                <TabsContent value="rules" className="space-y-4">
                  <RulesManagerPanel
                    relatedId={selectedBiz.id}
                    relatedType="业务"
                  />
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>
        )}

        {!selectedBiz && (
          <Card>
            <CardContent className="py-12 text-center text-muted-foreground">
              从左侧列表选择一个业务查看详情
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}

// ─── Rules Manager Panel ───────────────────────────────────────────────────────

function RulesManagerPanel({ relatedId, relatedType }: { relatedId: number; relatedType: RuleRelatedType }) {
  const queryClient = useQueryClient()
  const [mode, setMode] = useState<'list' | 'create' | 'edit'>('list')
  const [editingRule, setEditingRule] = useState<TimeRule | null>(null)

  const { data: rules, isLoading } = useQuery({
    queryKey: ['rules-list', relatedId, relatedType],
    queryFn: () => rulesApi.list({ related_id: relatedId, related_type: relatedType, size: 100 }),
  })

  const deleteMutation = useMutation({
    mutationFn: (ruleId: number) => rulesApi.delete(ruleId),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['rules-list', relatedId, relatedType] }) },
  })

  if (mode === 'list') {
    return (
      <div className="space-y-4">
        <div className="flex justify-end">
          <Button size="sm" onClick={() => setMode('create')}><Plus className="mr-2 h-4 w-4" />新建规则</Button>
        </div>
        {isLoading ? (
          <div className="text-center py-4">加载中...</div>
        ) : rules?.items?.length ? (
          <div className="space-y-2">
            {rules.items.map(rule => (
              <Card key={rule.id}>
                <CardContent className="pt-4">
                  <div className="flex items-start justify-between">
                    <div className="space-y-1 flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <Badge variant="outline">{rule.related_type}</Badge>
                        <Badge className={RULE_STATUS_COLORS[rule.status] || 'bg-gray-100'}>{rule.status}</Badge>
                      </div>
                      <p className="text-sm font-medium">
                        {RULE_EVENTS[rule.trigger_event as keyof typeof RULE_EVENTS] || rule.trigger_event} → {RULE_EVENTS[rule.target_event as keyof typeof RULE_EVENTS] || rule.target_event}
                      </p>
                      <p className="text-sm text-muted-foreground">
                        {rule.direction === 'after' ? '之后' : '之前'} {rule.offset} {rule.unit}
                      </p>
                    </div>
                    <div className="flex gap-2">
                      <Button variant="ghost" size="sm" onClick={() => { setEditingRule(rule); setMode('edit') }}>
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => deleteMutation.mutate(rule.id)}>
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <div className="text-center py-4 text-muted-foreground">暂无规则</div>
        )}
      </div>
    )
  }

  return (
    <RuleForm
      mode={mode as 'create' | 'edit'}
      rule={mode === 'edit' ? editingRule! : undefined}
      relatedId={relatedId}
      relatedType={relatedType}
      onSuccess={() => { setMode('list'); setEditingRule(null); queryClient.invalidateQueries({ queryKey: ['rules-list', relatedId, relatedType] }) }}
      onCancel={() => { setMode('list'); setEditingRule(null) }}
    />
  )
}

interface RuleFormProps {
  mode: 'create' | 'edit'
  rule?: TimeRule
  relatedId: number
  relatedType: RuleRelatedType
  onSuccess: () => void
  onCancel: () => void
}

function getEventLabel(eventKey: string): string {
  return RULE_EVENTS[eventKey as keyof typeof RULE_EVENTS] || eventKey
}

function RuleForm({ mode, rule, relatedId, relatedType, onSuccess, onCancel }: RuleFormProps) {
  const [formData, setFormData] = useState({
    trigger_event: rule?.trigger_event || '',
    target_event: rule?.target_event || '',
    offset: rule?.offset?.toString() || '0',
    unit: (rule?.unit || '自然日') as RuleUnit,
    direction: (rule?.direction || 'after') as RuleDirection,
    party: (rule?.party || '我方') as RuleParty,
    inherit: rule?.inherit?.toString() || '0',
    tge_param1: rule?.tge_param1 || '',
    tge_param2: rule?.tge_param2 || '',
    tae_param1: rule?.tae_param1 || '',
    tae_param2: rule?.tae_param2 || '',
  })

  const saveMutation = useMutation({
    mutationFn: () => {
      const inheritIdx = parseInt(formData.inherit)
      const status = inheritIdx === 0 ? '生效' : '模板'
      const payload: CreateTimeRuleSchema = {
        ...(mode === 'edit' && rule ? { id: rule.id } : {}),
        related_id: relatedId,
        related_type: relatedType,
        party: formData.party,
        trigger_event: formData.trigger_event,
        target_event: formData.target_event,
        offset: parseInt(formData.offset) || 0,
        unit: formData.unit,
        direction: formData.direction,
        inherit: inheritIdx as 0 | 1 | 2,
        status: status as '生效' | '模板',
        tge_param1: formData.tge_param1 || undefined,
        tge_param2: formData.tge_param2 || undefined,
        tae_param1: formData.tae_param1 || undefined,
        tae_param2: formData.tae_param2 || undefined,
      }
      return rulesApi.save(payload)
    },
    onSuccess,
  })

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label>触发事件</Label>
          <Select value={formData.trigger_event} onValueChange={(v) => setFormData({ ...formData, trigger_event: v })}>
            <SelectTrigger><SelectValue placeholder="选择触发事件" /></SelectTrigger>
            <SelectContent>
              {Object.entries(RULE_EVENTS).map(([value, label]) => (
                <SelectItem key={value} value={value}>{label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label>目标事件</Label>
          <Select value={formData.target_event} onValueChange={(v) => setFormData({ ...formData, target_event: v })}>
            <SelectTrigger><SelectValue placeholder="选择目标事件" /></SelectTrigger>
            <SelectContent>
              {Object.entries(RULE_EVENTS).map(([value, label]) => (
                <SelectItem key={value} value={value}>{label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-4">
        <div className="space-y-2">
          <Label>偏移量</Label>
          <Input type="number" value={formData.offset} onChange={(e) => setFormData({ ...formData, offset: e.target.value })} />
        </div>
        <div className="space-y-2">
          <Label>单位</Label>
          <Select value={formData.unit} onValueChange={(v) => setFormData({ ...formData, unit: v as RuleUnit })}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="自然日">自然日</SelectItem>
              <SelectItem value="工作日">工作日</SelectItem>
              <SelectItem value="小时">小时</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label>方向</Label>
          <Select value={formData.direction} onValueChange={(v) => setFormData({ ...formData, direction: v as RuleDirection })}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="after">之后</SelectItem>
              <SelectItem value="before">之前</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label>责任方</Label>
          <Select value={formData.party} onValueChange={(v) => setFormData({ ...formData, party: v as RuleParty })}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="我方">我方</SelectItem>
              <SelectItem value="客户">客户</SelectItem>
              <SelectItem value="供应商">供应商</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="space-y-2">
        <Label>继承层级</Label>
        <Select value={formData.inherit} onValueChange={(v) => setFormData({ ...formData, inherit: v })}>
          <SelectTrigger><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="0">自身</SelectItem>
            <SelectItem value="1">近亲</SelectItem>
            <SelectItem value="2">远亲</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label>触发参数1</Label>
          <Input value={formData.tge_param1} onChange={(e) => setFormData({ ...formData, tge_param1: e.target.value })} placeholder="选填" />
        </div>
        <div className="space-y-2">
          <Label>触发参数2</Label>
          <Input value={formData.tge_param2} onChange={(e) => setFormData({ ...formData, tge_param2: e.target.value })} placeholder="选填" />
        </div>
        <div className="space-y-2">
          <Label>目标参数1</Label>
          <Input value={formData.tae_param1} onChange={(e) => setFormData({ ...formData, tae_param1: e.target.value })} placeholder="选填" />
        </div>
        <div className="space-y-2">
          <Label>目标参数2</Label>
          <Input value={formData.tae_param2} onChange={(e) => setFormData({ ...formData, tae_param2: e.target.value })} placeholder="选填" />
        </div>
      </div>

      <div className="flex justify-end gap-2">
        <Button variant="outline" onClick={onCancel}>取消</Button>
        <Button onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending}>
          {saveMutation.isPending ? '保存中...' : mode === 'create' ? '创建' : '保存'}
        </Button>
      </div>
    </div>
  )
}

// ─── Addon Management Tab ─────────────────────────────────────────────────────

// ─── Addon Form Dialog ─────────────────────────────────────────────────────────

function AddonFormDialog({
  mode, addon, businessId, onSuccess, onCancel,
}: {
  mode: 'create' | 'edit'
  addon?: AddonBusiness
  businessId: number
  onSuccess: () => void
  onCancel: () => void
}) {
  const queryClient = useQueryClient()
  const [addonType, setAddonType] = useState<string>(addon?.addon_type || 'PRICE_ADJUST')
  const [skuId, setSkuId] = useState(String(addon?.sku_id || ''))
  const [startDate, setStartDate] = useState(addon?.start_date ? new Date(addon.start_date) : new Date())
  const [endDate, setEndDate] = useState(addon?.end_date ? new Date(addon.end_date) : undefined)
  const [overrideVal, setOverrideVal] = useState(addon?.override_price?.toString() || addon?.override_deposit?.toString() || '')
  const [remark, setRemark] = useState(addon?.remark || '')
  const [step, setStep] = useState<'type' | 'detail'>('type')

  const { data: allSkus } = useQuery({
    queryKey: ['skus-for-addon', businessId],
    queryFn: async () => {
      const skus = await masterApi.skus.list({ size: 500 })
      const detail = await businessApi.getDetail(businessId)
      const pricingSkuIds = new Set(Object.keys(detail.details?.pricing || {}).filter(k => !isNaN(parseInt(k))))
      return { skus: skus.items || [], pricingSkuIds }
    },
    enabled: mode === 'create',
  })

  const selectedSku = allSkus?.skus.find((s: SKU) => String(s.id) === skuId)
  const isEquipment = selectedSku?.type_level1 === '设备'
  const isMaterial = selectedSku?.type_level1 === '物料'

  const availableSkus = mode === 'create'
    ? (addonType === 'PRICE_ADJUST'
        ? (allSkus?.skus.filter((s: SKU) => allSkus.pricingSkuIds.has(String(s.id))) || [])
        : (allSkus?.skus.filter((s: SKU) => !allSkus.pricingSkuIds.has(String(s.id))) || []))
    : []

  const createMutation = useMutation({
    mutationFn: () => {
      const payload: CreateAddonSchema = {
        business_id: businessId,
        addon_type: addonType,
        sku_id: parseInt(skuId),
        start_date: startDate.toISOString(),
        end_date: endDate ? endDate.toISOString() : undefined,
        remark: remark || undefined,
      }
      if (isEquipment && overrideVal) payload.override_deposit = parseFloat(overrideVal)
      else if (isMaterial && overrideVal) payload.override_price = parseFloat(overrideVal)
      return businessApi.createAddon(payload)
    },
    onSuccess,
  })

  const updateMutation = useMutation({
    mutationFn: () => {
      if (!addon) return Promise.reject()
      const payload: UpdateAddonSchema = {
        addon_id: addon.id,
        start_date: startDate.toISOString(),
        end_date: endDate ? endDate.toISOString() : undefined,
        remark: remark || undefined,
      }
      if (overrideVal) {
        if (addon.addon_type === 'PRICE_ADJUST') {
          payload.override_price = parseFloat(overrideVal)
        } else {
          payload.override_deposit = parseFloat(overrideVal)
        }
      }
      return businessApi.updateAddon(payload)
    },
    onSuccess,
  })

  return (
    <Dialog open onOpenChange={(open) => { if (!open) onCancel() }}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>{mode === 'create' ? '新建附加项' : '编辑附加项'}</DialogTitle>
        </DialogHeader>
        {step === 'type' && mode === 'create' ? (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>附加项类型</Label>
              <Select value={addonType} onValueChange={(v) => { setAddonType(v as AddonType); setSkuId('') }}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="PRICE_ADJUST">价格调整</SelectItem>
                  <SelectItem value="NEW_SKU">新增 SKU</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>选择 SKU</Label>
              {availableSkus.length > 0 ? (
                <Select value={skuId} onValueChange={setSkuId}>
                  <SelectTrigger><SelectValue placeholder="选择 SKU" /></SelectTrigger>
                  <SelectContent>
                    {availableSkus.map((s: SKU) => <SelectItem key={s.id} value={String(s.id)}>{s.name} ({s.type_level1})</SelectItem>)}
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
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>开始日期</Label>
                <Input type="date" value={startDate.toISOString().slice(0, 10)}
                  onChange={(e) => setStartDate(e.target.value ? new Date(e.target.value) : new Date())} />
              </div>
              <div className="space-y-2">
                <Label>结束日期（留空=永久）</Label>
                <Input type="date" value={endDate ? endDate.toISOString().slice(0, 10) : ''}
                  onChange={(e) => setEndDate(e.target.value ? new Date(e.target.value) : undefined)} />
              </div>
            </div>
            {isEquipment && (
              <div className="space-y-2">
                <Label>覆盖押金（元）</Label>
                <Input type="number" min="0" step="0.01" value={overrideVal} onChange={(e) => setOverrideVal(e.target.value)} />
              </div>
            )}
            {isMaterial && (
              <div className="space-y-2">
                <Label>覆盖单价（元）</Label>
                <Input type="number" min="0" step="0.01" value={overrideVal} onChange={(e) => setOverrideVal(e.target.value)} />
              </div>
            )}
            <div className="space-y-2">
              <Label>备注</Label>
              <Textarea value={remark} onChange={(e) => setRemark(e.target.value)} placeholder="选填" />
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={mode === 'create' ? () => setStep('type') : onCancel}>返回</Button>
              <Button
                onClick={() => mode === 'create' ? createMutation.mutate() : updateMutation.mutate()}
                disabled={createMutation.isPending || updateMutation.isPending}
              >
                {createMutation.isPending || updateMutation.isPending ? '处理中...' : mode === 'create' ? '创建' : '保存'}
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}

function AddonManagementTab() {
  const queryClient = useQueryClient()
  const [selectedBizId, setSelectedBizId] = useState<string>('')
  const [showCreate, setShowCreate] = useState(false)
  const [editingAddon, setEditingAddon] = useState<AddonBusiness | null>(null)
  const [showAll, setShowAll] = useState(false)

  const { data: activeBizs } = useQuery({
    queryKey: ['business-active'],
    queryFn: () => businessApi.list({ status: '业务开展' as BusinessStatus, size: 100 }),
  })

  const bizOptions = (activeBizs?.items || []).map((b: Business) => ({ value: String(b.id), label: `${b.id} - ${b.customer_name}` }))

  const businessId = selectedBizId ? parseInt(selectedBizId) : 0

  const { data: addons, isLoading, refetch } = useQuery({
    queryKey: ['business-addons', businessId, showAll],
    queryFn: () => businessId ? businessApi.listAddons(businessId, showAll) : Promise.reject(),
    enabled: !!businessId,
  })

  const deactivateMutation = useMutation({
    mutationFn: (addonId: number) => businessApi.deactivateAddon(addonId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['business-addons', businessId, showAll] }),
  })

  if (!activeBizs?.items?.length) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-muted-foreground">
          当前无进行中的业务（ACTIVE 阶段），请先创建或推进业务至 ACTIVE
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex gap-4 items-end">
        <div className="space-y-2 flex-1">
          <Label>选择业务</Label>
          <Select value={selectedBizId} onValueChange={setSelectedBizId}>
            <SelectTrigger><SelectValue placeholder="选择业务" /></SelectTrigger>
            <SelectContent>
              {bizOptions.map(o => <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
        <Button variant="outline" size="sm" onClick={() => refetch()}><RefreshCw className="h-4 w-4" /></Button>
      </div>

      {businessId && (
        <>
          <div className="flex gap-2">
            <Button size="sm" onClick={() => setShowCreate(true)}><Plus className="mr-2 h-4 w-4" />新建附加项</Button>
            <Button
              variant={!showAll ? 'default' : 'outline'}
              size="sm"
              onClick={() => setShowAll(false)}
            >
              生效中 ({(addons || []).filter((a: AddonBusiness) => a.status === '生效').length})
            </Button>
            <Button
              variant={showAll ? 'default' : 'outline'}
              size="sm"
              onClick={() => setShowAll(true)}
            >
              全部记录 ({addons?.length || 0})
            </Button>
          </div>

          {isLoading ? (
            <div className="text-center py-4">加载中...</div>
          ) : !addons?.length ? (
            <Card>
              <CardContent className="py-8 text-center text-muted-foreground">暂无附加业务政策</CardContent>
            </Card>
          ) : (
            <div className="space-y-2">
              {addons.map((addon: AddonBusiness) => (
                <Card key={addon.id}>
                  <CardContent className="pt-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3 flex-1">
                        <Badge variant="outline">{ADDON_TYPE_LABELS[addon.addon_type]}</Badge>
                        <span>{addon.sku_name || `SKU-${addon.sku_id}`}</span>
                        <span className="text-sm text-muted-foreground">
                          {addon.start_date?.slice(0, 10)} ~ {addon.end_date?.slice(0, 10) || '永久'}
                        </span>
                        {(addon.override_price !== undefined || addon.override_deposit !== undefined) && (
                          <span className="text-sm text-muted-foreground">
                            {addon.override_price !== undefined ? `覆盖单价: ¥${addon.override_price}` : ''}
                            {addon.override_deposit !== undefined ? `覆盖押金: ¥${addon.override_deposit}` : ''}
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        <Button variant="ghost" size="sm" onClick={() => setEditingAddon(addon)}><Pencil className="h-4 w-4" /></Button>
                        <Button variant="outline" size="sm" className="text-orange-600" onClick={() => deactivateMutation.mutate(addon.id)}>失效</Button>
                        <Badge className={addon.status === '生效' ? 'bg-green-100 text-green-800' : 'bg-gray-100'}>{addon.status}</Badge>
                      </div>
                    </div>
                    {addon.remark && <p className="text-sm mt-2 text-muted-foreground">{addon.remark}</p>}
                  </CardContent>
                </Card>
              ))}
            </div>
          )}

          {(showCreate || editingAddon) && (
            <AddonFormDialog
              mode={editingAddon ? 'edit' : 'create'}
              addon={editingAddon || undefined}
              businessId={businessId}
              onSuccess={() => { setShowCreate(false); setEditingAddon(null); queryClient.invalidateQueries({ queryKey: ['business-addons', businessId, showAll] }) }}
              onCancel={() => { setShowCreate(false); setEditingAddon(null) }}
            />
          )}
        </>
      )}
    </div>
  )
}

// ─── Main Operations Page ─────────────────────────────────────────────────────

export function OperationsPage() {
  const [activeTab, setActiveTab] = useState('customer-inclusion')

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">业务运营</h2>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="customer-inclusion">客户导入</TabsTrigger>
          <TabsTrigger value="business-overview">业务概览</TabsTrigger>
          <TabsTrigger value="addon-management">附加业务</TabsTrigger>
        </TabsList>

        <TabsContent value="customer-inclusion">
          <CustomerInclusionTab />
        </TabsContent>

        <TabsContent value="business-overview">
          <BusinessOverviewPanel />
        </TabsContent>

        <TabsContent value="addon-management">
          <AddonManagementTab />
        </TabsContent>
      </Tabs>
    </div>
  )
}
