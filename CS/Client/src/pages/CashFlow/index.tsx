import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Search, RefreshCw, RefreshCcw, Check, X, Info } from 'lucide-react'
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
import { financeApi, CashFlow, CashFlowType, CreateCashFlowSchema } from '@/api/endpoints/finance'
import { vcApi, VCStatus } from '@/api/endpoints/vc'
import { formatCurrency, formatDate } from '@/lib/utils'

const CASHFLOW_TYPE_LABELS: Record<string, string> = {
  PREPAYMENT: '预付款',
  FULFILLMENT: '履约款',
  DEPOSIT: '押金',
  RETURN_DEPOSIT: '退还押金',
  PENALTY: '罚款',
  REFUND: '退款',
  OFFSET_INFLOW: '核销流入',
  OFFSET_OUTFLOW: '核销流出',
  DEPOSIT_OFFSET_IN: '押金核销',
  预付: '预付',
  履约: '履约',
}

const CASHFLOW_TYPE_COLORS: Record<string, string> = {
  PREPAYMENT: 'bg-blue-100 text-blue-800',
  FULFILLMENT: 'bg-cyan-100 text-cyan-800',
  DEPOSIT: 'bg-purple-100 text-purple-800',
  RETURN_DEPOSIT: 'bg-orange-100 text-orange-800',
  PENALTY: 'bg-red-100 text-red-800',
  REFUND: 'bg-pink-100 text-pink-800',
  OFFSET_INFLOW: 'bg-green-100 text-green-800',
  OFFSET_OUTFLOW: 'bg-yellow-100 text-yellow-800',
  DEPOSIT_OFFSET_IN: 'bg-indigo-100 text-indigo-800',
  预付: 'bg-blue-100 text-blue-800',
  履约: 'bg-cyan-100 text-cyan-800',
}

function CreateCashFlowDialog({ onSuccess }: { onSuccess: () => void }) {
  const queryClient = useQueryClient()
  const [isOpen, setIsOpen] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const [formData, setFormData] = useState({
    vc_id: '',
    type: 'PREPAYMENT' as CashFlowType,
    amount: '',
    payer_id: '',
    payee_id: '',
    transaction_date: new Date().toISOString().split('T')[0],
    description: '',
  })
  const [cfTypes, setCfTypes] = useState<CashFlowType[]>(['PREPAYMENT', 'FULFILLMENT', 'DEPOSIT', 'RETURN_DEPOSIT', 'PENALTY'])

  const { data: vcs } = useQuery({
    queryKey: ['vcs-for-cf'],
    queryFn: () => vcApi.list({ status: '执行', size: 100 }),
  })

  const { data: bankAccounts } = useQuery({
    queryKey: ['bank-accounts'],
    queryFn: () => financeApi.getBankAccounts(),
  })

  const { data: suggestedParties } = useQuery({
    queryKey: ['suggested-parties', formData.vc_id, formData.type],
    queryFn: () => financeApi.getSuggestedParties(parseInt(formData.vc_id), formData.type),
    enabled: !!formData.vc_id && !!formData.type,
  })

  const { data: progress } = useQuery({
    queryKey: ['cf-progress', formData.vc_id],
    queryFn: () => vcApi.getCashflowProgress(parseInt(formData.vc_id)),
    enabled: !!formData.vc_id,
  })

  const createMutation = useMutation({
    mutationFn: () => financeApi.createCashflow({
      vc_id: parseInt(formData.vc_id),
      type: formData.type,
      amount: parseFloat(formData.amount) || 0,
      payer_id: formData.payer_id ? parseInt(formData.payer_id) : undefined,
      payee_id: formData.payee_id ? parseInt(formData.payee_id) : undefined,
      transaction_date: formData.transaction_date + 'T00:00:00',
      description: formData.description,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cashflow-list'] })
      setIsOpen(false)
      setShowConfirm(false)
      onSuccess()
    },
  })

  const handleVCSelect = (vcId: string) => {
    setFormData({ ...formData, vc_id: vcId })
    const vc = vcs?.items?.find(v => v.id === parseInt(vcId))
    if (vc) {
      if (vc.type === 'RETURN') {
        setCfTypes(['REFUND', 'RETURN_DEPOSIT'])
      } else {
        setCfTypes(['PREPAYMENT', 'FULFILLMENT', 'DEPOSIT', 'RETURN_DEPOSIT', 'PENALTY'])
      }
    }
  }

  const applySuggestedParties = () => {
    if (suggestedParties) {
      setFormData({
        ...formData,
        payer_id: String(suggestedParties.payer_id || ''),
        payee_id: String(suggestedParties.payee_id || ''),
      })
    }
  }

  const selectedVC = vcs?.items?.find(v => v.id === parseInt(formData.vc_id))
  const payerAccount = bankAccounts?.find(a => a.id === parseInt(formData.payer_id))
  const payeeAccount = bankAccounts?.find(a => a.id === parseInt(formData.payee_id))

  const handleClose = (open: boolean) => {
    setIsOpen(open)
    if (!open) setShowConfirm(false)
  }

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogTrigger asChild>
        <Button><Plus className="mr-2 h-4 w-4" />录入资金流</Button>
      </DialogTrigger>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>{showConfirm ? '确认资金流水' : '录入资金流'}</DialogTitle>
        </DialogHeader>

        {!showConfirm ? (
          <form onSubmit={(e) => { e.preventDefault(); setShowConfirm(true) }} className="space-y-6">
            <div className="space-y-2">
              <Label>关联虚拟合同</Label>
              <Select value={formData.vc_id} onValueChange={handleVCSelect}>
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

            {progress && (
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">付款进度</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-3 gap-4 text-sm">
                    <div>
                      <span className="text-muted-foreground">应付总额: </span>
                      <span className="font-medium">{formatCurrency(progress.total_amount)}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">已付金额: </span>
                      <span className="font-medium text-green-600">{formatCurrency(progress.paid_amount)}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">未付余额: </span>
                      <span className="font-medium text-orange-600">{formatCurrency(progress.balance)}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">应收押金: </span>
                      <span className="font-medium">{formatCurrency(progress.expected_deposit)}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">实收押金: </span>
                      <span className="font-medium text-blue-600">{formatCurrency(progress.actual_deposit)}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">核销池: </span>
                      <span className="font-medium">{formatCurrency(progress.offset_pool)}</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}

            <div className="space-y-2">
              <Label>款项类型</Label>
              <Select value={formData.type} onValueChange={(v) => setFormData({ ...formData, type: v as CashFlowType })}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {cfTypes.map(type => (
                    <SelectItem key={type} value={type}>{CASHFLOW_TYPE_LABELS[type]}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>金额</Label>
              <Input type="number" step="0.01" min="0" value={formData.amount} onChange={(e) => setFormData({ ...formData, amount: e.target.value })} />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label>付款方账户</Label>
                  {suggestedParties && (
                    <Button type="button" variant="ghost" size="sm" onClick={applySuggestedParties}>
                      <RefreshCcw className="h-3 w-3 mr-1" />自动填充
                    </Button>
                  )}
                </div>
                <Select value={formData.payer_id} onValueChange={(v) => setFormData({ ...formData, payer_id: v })}>
                  <SelectTrigger>
                    <SelectValue placeholder="选择付款方" />
                  </SelectTrigger>
                  <SelectContent>
                    {bankAccounts?.map(acc => (
                      <SelectItem key={acc.id} value={String(acc.id)}>{acc.bank_name} ({acc.owner_name})</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>收款方账户</Label>
                <Select value={formData.payee_id} onValueChange={(v) => setFormData({ ...formData, payee_id: v })}>
                  <SelectTrigger>
                    <SelectValue placeholder="选择收款方" />
                  </SelectTrigger>
                  <SelectContent>
                    {bankAccounts?.map(acc => (
                      <SelectItem key={acc.id} value={String(acc.id)}>{acc.bank_name} ({acc.owner_name})</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-2">
              <Label>交易日期</Label>
              <Input type="date" value={formData.transaction_date} onChange={(e) => setFormData({ ...formData, transaction_date: e.target.value })} />
            </div>

            <div className="space-y-2">
              <Label>备注</Label>
              <Textarea value={formData.description} onChange={(e) => setFormData({ ...formData, description: e.target.value })} />
            </div>

            <div className="flex justify-end gap-2">
              <Button type="button" variant="outline" onClick={() => setIsOpen(false)}>取消</Button>
              <Button type="submit" disabled={!formData.vc_id || !formData.amount || createMutation.isPending}>
                下一步
              </Button>
            </div>
          </form>
        ) : (
          <div className="space-y-6">
            <div className="bg-muted rounded-lg p-4 space-y-3">
              <div className="flex items-center gap-2 text-sm">
                <Info className="h-4 w-4 text-muted-foreground" />
                <span className="text-muted-foreground">请从财务审核角度核对以下流水信息</span>
              </div>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-muted-foreground">关联合同: </span>
                  <span className="font-medium">{selectedVC?.description?.slice(0, 30) || `VC-${formData.vc_id}`}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">资金类型: </span>
                  <Badge className={CASHFLOW_TYPE_COLORS[formData.type]}>{CASHFLOW_TYPE_LABELS[formData.type]}</Badge>
                </div>
                <div>
                  <span className="text-muted-foreground">操作金额: </span>
                  <span className="font-medium text-lg">{formatCurrency(parseFloat(formData.amount) || 0)}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">交易日期: </span>
                  <span className="font-medium">{formData.transaction_date}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">付款账户: </span>
                  <span className="font-medium">{payerAccount ? `${payerAccount.bank_name} (${payerAccount.owner_name})` : '未指定'}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">收款账户: </span>
                  <span className="font-medium">{payeeAccount ? `${payeeAccount.bank_name} (${payeeAccount.owner_name})` : '未指定'}</span>
                </div>
              </div>
              {formData.description && (
                <div className="text-sm">
                  <span className="text-muted-foreground">备注: </span>
                  <span>{formData.description}</span>
                </div>
              )}
            </div>

            <div className="flex justify-between">
              <Button type="button" variant="outline" onClick={() => setShowConfirm(false)}>
                返回修改
              </Button>
              <Button onClick={() => createMutation.mutate()} disabled={createMutation.isPending}>
                {createMutation.isPending ? '提交中...' : '确认执行并记账'}
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}

export function CashFlowPage() {
  const [activeTab, setActiveTab] = useState('entry')
  const [typeFilter, setTypeFilter] = useState<CashFlowType | 'ALL'>('ALL')
  const [search, setSearch] = useState('')
  const [overviewTypeFilter, setOverviewTypeFilter] = useState<string[]>([])
  const [overviewSearch, setOverviewSearch] = useState('')
  const [selectedCF, setSelectedCF] = useState<CashFlow | null>(null)

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['cashflow-list', typeFilter],
    queryFn: () => financeApi.getCashflows({
      type: typeFilter !== 'ALL' ? typeFilter : undefined,
      size: 100,
    }),
  })

  const { data: recentData } = useQuery({
    queryKey: ['cashflow-recent'],
    queryFn: () => financeApi.getCashflows({ size: 20 }),
    enabled: activeTab === 'entry',
  })

  const { data: overviewData } = useQuery({
    queryKey: ['cashflow-overview', overviewTypeFilter],
    queryFn: () => financeApi.getCashflows({ size: 100 }),
    enabled: activeTab === 'overview',
  })

  const filteredItems = data?.items?.filter(cf => {
    if (!search) return true
    return cf.description?.toLowerCase().includes(search.toLowerCase()) ||
           cf.vc_description?.toLowerCase().includes(search.toLowerCase())
  }) || []

  const overviewFiltered = overviewData?.items?.filter(cf => {
    if (overviewTypeFilter.length > 0 && !overviewTypeFilter.includes(cf.type)) return false
    if (overviewSearch) {
      const q = overviewSearch.toLowerCase()
      return cf.description?.toLowerCase().includes(q) ||
             cf.vc_description?.toLowerCase().includes(q) ||
             String(cf.id).includes(q)
    }
    return true
  }) || []

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">资金流管理</h2>
        {activeTab === 'entry' && <CreateCashFlowDialog onSuccess={() => refetch()} />}
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="entry">资金流录入</TabsTrigger>
          <TabsTrigger value="overview">资金全局概览</TabsTrigger>
        </TabsList>

        <TabsContent value="entry" className="space-y-4">
          <div className="flex gap-4 flex-wrap">
            <Input placeholder="搜索..." value={search} onChange={(e) => setSearch(e.target.value)} className="w-64" />
            <Select value={typeFilter} onValueChange={(v) => setTypeFilter(v as CashFlowType | 'ALL')}>
              <SelectTrigger className="w-32">
                <SelectValue placeholder="类型" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ALL">全部类型</SelectItem>
                {Object.entries(CASHFLOW_TYPE_LABELS).map(([value, label]) => (
                  <SelectItem key={value} value={value}>{label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button variant="outline" onClick={() => refetch()}>
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>

          <Card>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>ID</TableHead>
                    <TableHead>类型</TableHead>
                    <TableHead>金额</TableHead>
                    <TableHead>方向</TableHead>
                    <TableHead>付款方</TableHead>
                    <TableHead>收款方</TableHead>
                    <TableHead>关联合同</TableHead>
                    <TableHead>交易日期</TableHead>
                    <TableHead>备注</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredItems.map(cf => (
                    <TableRow key={cf.id}>
                      <TableCell className="font-medium">CF-{cf.id}</TableCell>
                      <TableCell>
                        <Badge className={CASHFLOW_TYPE_COLORS[cf.type]}>{CASHFLOW_TYPE_LABELS[cf.type]}</Badge>
                      </TableCell>
                      <TableCell className={`font-medium ${cf.direction === 'INFLOW' ? 'text-green-600' : 'text-red-600'}`}>
                        {cf.direction === 'INFLOW' ? '+' : '-'}{formatCurrency(cf.amount)}
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">{cf.direction === 'INFLOW' ? '流入' : '流出'}</Badge>
                      </TableCell>
                      <TableCell className="text-sm">{cf.payer_account_name || '-'}</TableCell>
                      <TableCell className="text-sm">{cf.payee_account_name || '-'}</TableCell>
                      <TableCell>
                        <Badge variant="outline">VC-{cf.virtual_contract_id}</Badge>
                      </TableCell>
                      <TableCell>{formatDate(cf.transaction_date)}</TableCell>
                      <TableCell className="max-w-[150px] truncate text-sm">
                        {cf.description || '-'}
                      </TableCell>
                    </TableRow>
                  ))}
                  {!filteredItems.length && (
                    <TableRow>
                      <TableCell colSpan={9} className="text-center text-muted-foreground">
                        {isLoading ? '加载中...' : '暂无数据'}
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2">
                <RefreshCw className="h-4 w-4" />最近资金收付记录
              </CardTitle>
            </CardHeader>
            <CardContent>
              {recentData?.items && recentData.items.length > 0 ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>时间</TableHead>
                      <TableHead>流水ID</TableHead>
                      <TableHead>关联合同</TableHead>
                      <TableHead>类型</TableHead>
                      <TableHead>金额</TableHead>
                      <TableHead>付款方</TableHead>
                      <TableHead>收款方</TableHead>
                      <TableHead>说明</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {recentData.items.slice(0, 10).map(cf => (
                      <TableRow key={cf.id}>
                        <TableCell className="text-sm">{formatDate(cf.transaction_date)}</TableCell>
                        <TableCell className="font-medium">CF-{cf.id}</TableCell>
                        <TableCell className="text-sm">{cf.vc_description || '-'}</TableCell>
                        <TableCell><Badge className={CASHFLOW_TYPE_COLORS[cf.type]}>{CASHFLOW_TYPE_LABELS[cf.type]}</Badge></TableCell>
                        <TableCell className={`font-medium ${cf.direction === 'INFLOW' ? 'text-green-600' : 'text-red-600'}`}>
                          {cf.direction === 'INFLOW' ? '+' : '-'}{formatCurrency(cf.amount)}
                        </TableCell>
                        <TableCell className="text-sm">{cf.payer_account_name || '-'}</TableCell>
                        <TableCell className="text-sm">{cf.payee_account_name || '-'}</TableCell>
                        <TableCell className="text-sm max-w-[150px] truncate">{cf.description || '-'}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <div className="text-center py-4 text-muted-foreground">暂无记录</div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="overview" className="space-y-4">
          <div className="flex gap-4 flex-wrap">
            <Select value={overviewTypeFilter[0] || 'ALL'} onValueChange={(v) => setOverviewTypeFilter(v === 'ALL' ? [] : [v as CashFlowType])}>
              <SelectTrigger className="w-36">
                <SelectValue placeholder="资金类型" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ALL">全部类型</SelectItem>
                {Object.entries(CASHFLOW_TYPE_LABELS).map(([value, label]) => (
                  <SelectItem key={value} value={value}>{label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Input
              placeholder="搜索流水..."
              value={overviewSearch}
              onChange={(e) => setOverviewSearch(e.target.value)}
              className="w-64"
            />
            <Button variant="outline" onClick={() => refetch()}>
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>

          <Card>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>流水ID</TableHead>
                    <TableHead>日期</TableHead>
                    <TableHead>关联合同</TableHead>
                    <TableHead>类型</TableHead>
                    <TableHead>金额</TableHead>
                    <TableHead>备注</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {overviewFiltered.map(cf => (
                    <TableRow
                      key={cf.id}
                      className={selectedCF?.id === cf.id ? 'bg-muted' : ''}
                      onClick={() => setSelectedCF(cf)}
                    >
                      <TableCell className="font-medium">CF-{cf.id}</TableCell>
                      <TableCell>{formatDate(cf.transaction_date)}</TableCell>
                      <TableCell className="text-sm">{cf.vc_description || '-'}</TableCell>
                      <TableCell><Badge className={CASHFLOW_TYPE_COLORS[cf.type]}>{CASHFLOW_TYPE_LABELS[cf.type]}</Badge></TableCell>
                      <TableCell className={`font-medium ${cf.direction === 'INFLOW' ? 'text-green-600' : 'text-red-600'}`}>
                        {cf.direction === 'INFLOW' ? '+' : '-'}{formatCurrency(cf.amount)}
                      </TableCell>
                      <TableCell className="text-sm max-w-[150px] truncate">{cf.description || '-'}</TableCell>
                    </TableRow>
                  ))}
                  {!overviewFiltered.length && (
                    <TableRow>
                      <TableCell colSpan={6} className="text-center text-muted-foreground">暂无数据</TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          {selectedCF && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">资金流水详情 (ID: {selectedCF.id})</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-3 gap-4 text-sm mb-4">
                  <div>
                    <span className="text-muted-foreground">交易金额: </span>
                    <span className="font-medium">{formatCurrency(selectedCF.amount)}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">资金类型: </span>
                    <Badge className={CASHFLOW_TYPE_COLORS[selectedCF.type]}>{CASHFLOW_TYPE_LABELS[selectedCF.type]}</Badge>
                  </div>
                  <div>
                    <span className="text-muted-foreground">交易时间: </span>
                    <span className="font-medium">{formatDate(selectedCF.transaction_date)}</span>
                  </div>
                </div>
                <div className="bg-muted rounded-lg p-3 text-sm">
                  <div className="text-muted-foreground mb-1">资金收付链路</div>
                  <div className="flex items-center gap-2">
                    <span>{selectedCF.payer_account_name || '未指定'}</span>
                    <span className="text-muted-foreground">→</span>
                    <span>{selectedCF.payee_account_name || '未指定'}</span>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4 mt-4 text-sm">
                  <div>
                    <span className="text-muted-foreground">关联合同: </span>
                    <span>{selectedCF.vc_description || '-'}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">备注: </span>
                    <span>{selectedCF.description || '无'}</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}
