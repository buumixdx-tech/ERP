import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, RefreshCw, AlertTriangle, Pencil, Trash2, Calendar } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import {
  rulesApi, TimeRule, RuleRelatedType, RuleParty, RuleUnit, RuleDirection,
  RULE_EVENTS, ALL_EVENTS, VC_EVENTS, LOGISTICS_EVENTS,
  CreateTimeRuleSchema
} from '@/api/endpoints/rules'
import { formatDate } from '@/lib/utils'

const WARNING_COLORS: Record<string, string> = {
  GREEN: 'bg-green-100 text-green-800',
  YELLOW: 'bg-yellow-100 text-yellow-800',
  ORANGE: 'bg-orange-100 text-orange-800',
  RED: 'bg-red-100 text-red-800',
}

const STATUS_COLORS: Record<string, string> = {
  '失效': 'bg-gray-100 text-gray-800',
  '模板': 'bg-purple-100 text-purple-800',
  '生效': 'bg-blue-100 text-blue-800',
  '有结果': 'bg-cyan-100 text-cyan-800',
  '结束': 'bg-gray-100 text-gray-800',
}

const STATUS_LABELS: Record<string, string> = {
  '失效': '未激活',
  '模板': '模板',
  '生效': '生效中',
  '有结果': '已触发',
  '结束': '已结束',
}

function getEventLabel(eventKey: string): string {
  return RULE_EVENTS[eventKey as keyof typeof RULE_EVENTS] || eventKey
}

function getInheritOptions(relatedType: RuleRelatedType): { value: string; label: string }[] {
  if (relatedType === '虚拟合同') return [
    { value: '0', label: '本级定制 (合同级)' },
    { value: '1', label: '近继承 (至物流)' },
  ]
  if (relatedType === '物流') return [
    { value: '0', label: '本级定制 (物流级)' },
  ]
  return [
    { value: '0', label: '本级定制 (项目级)' },
    { value: '1', label: '近继承 (至虚拟合同)' },
    { value: '2', label: '远继承 (至物流)' },
  ]
}

function getEventsForType(relatedType: RuleRelatedType) {
  if (relatedType === '虚拟合同') return VC_EVENTS
  if (relatedType === '物流') return LOGISTICS_EVENTS
  return ALL_EVENTS
}

interface RuleFormData {
  related_id: string
  related_type: RuleRelatedType
  party: RuleParty
  trigger_event: string
  target_event: string
  offset: string
  unit: RuleUnit
  direction: RuleDirection
  inherit: string
  tge_param1: string
  tge_param2: string
  tae_param1: string
  tae_param2: string
  flag_time: string
}

function RuleFormDialog({
  mode,
  rule,
  relatedId,
  relatedType,
  onSuccess,
}: {
  mode: 'create' | 'update'
  rule?: TimeRule
  relatedId?: string
  relatedType?: RuleRelatedType
  onSuccess: () => void
}) {
  const queryClient = useQueryClient()
  const [isOpen, setIsOpen] = useState(false)

  const defaultFormData: RuleFormData = {
    related_id: rule?.related_id?.toString() || relatedId || '',
    related_type: (rule?.related_type || relatedType || '业务') as RuleRelatedType,
    party: (rule?.party || '我方') as RuleParty,
    trigger_event: rule?.trigger_event || '',
    target_event: rule?.target_event || '',
    offset: rule?.offset?.toString() || '0',
    unit: (rule?.unit || '自然日') as RuleUnit,
    direction: (rule?.direction || 'after') as RuleDirection,
    inherit: rule?.inherit?.toString() || '0',
    tge_param1: rule?.tge_param1 || '',
    tge_param2: rule?.tge_param2 || '',
    tae_param1: rule?.tae_param1 || '',
    tae_param2: rule?.tae_param2 || '',
    flag_time: rule?.flag_time?.split('T')[0] || '',
  }

  const [formData, setFormData] = useState<RuleFormData>(defaultFormData)

  const createMutation = useMutation({
    mutationFn: () => {
      const inheritIdx = parseInt(formData.inherit)
      const status = inheritIdx === 0 ? '生效' : '模板'
      const payload: CreateTimeRuleSchema = {
        ...(mode === 'update' && rule ? { id: rule.id } : {}),
        related_id: parseInt(formData.related_id) || 0,
        related_type: formData.related_type,
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
        flag_time: formData.trigger_event === '绝对日期' && formData.flag_time
          ? formData.flag_time + ' 00:00:00' : undefined,
      }
      return rulesApi.save(payload)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rules-list'] })
      setIsOpen(false)
      onSuccess()
    },
  })

  const deleteMutation = useMutation({
    mutationFn: () => rule ? rulesApi.delete(rule.id) : Promise.reject(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rules-list'] })
      setIsOpen(false)
      onSuccess()
    },
  })

  const openDialog = () => {
    setFormData(defaultFormData)
    setIsOpen(true)
  }

  const availableEvents = getEventsForType(formData.related_type)
  const isAbsoluteDate = formData.trigger_event === '绝对日期'

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        {mode === 'create' ? (
          <Button><Plus className="mr-2 h-4 w-4" />新建规则</Button>
        ) : (
          <Button variant="ghost" size="sm"><Pencil className="h-4 w-4" /></Button>
        )}
      </DialogTrigger>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {mode === 'create' ? '新建时间规则' : '编辑时间规则'}
            {formData.related_type && formData.related_id && (
              <span className="ml-2 text-sm font-normal text-muted-foreground">
                — {formData.related_type} (ID: {formData.related_id})
              </span>
            )}
          </DialogTitle>
        </DialogHeader>
        <form onSubmit={(e) => { e.preventDefault(); createMutation.mutate() }} className="space-y-6">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>关联类型</Label>
              <Select
                value={formData.related_type}
                onValueChange={(v) => {
                  const rt = v as RuleRelatedType
                  setFormData({
                    ...formData,
                    related_type: rt,
                    inherit: getInheritOptions(rt)[0].value,
                    trigger_event: '',
                    target_event: '',
                  })
                }}
                disabled={mode === 'update'}
              >
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="业务">业务</SelectItem>
                  <SelectItem value="供应链">供应链</SelectItem>
                  <SelectItem value="虚拟合同">虚拟合同</SelectItem>
                  <SelectItem value="物流">物流</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>关联ID</Label>
              <Input
                type="number"
                value={formData.related_id}
                onChange={(e) => setFormData({ ...formData, related_id: e.target.value })}
                disabled={mode === 'update'}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>触发事件</Label>
              <Select value={formData.trigger_event} onValueChange={(v) => setFormData({ ...formData, trigger_event: v })}>
                <SelectTrigger><SelectValue placeholder="选择触发事件" /></SelectTrigger>
                <SelectContent>
                  {availableEvents.map(({ key, label }) => (
                    <SelectItem key={key} value={key}>{label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            {isAbsoluteDate ? (
              <div className="space-y-2">
                <Label>设定标杆日期</Label>
                <Input
                  type="date"
                  value={formData.flag_time}
                  onChange={(e) => setFormData({ ...formData, flag_time: e.target.value })}
                />
              </div>
            ) : (
              <div className="space-y-2">
                <Label>触发参数1</Label>
                <Input value={formData.tge_param1} onChange={(e) => setFormData({ ...formData, tge_param1: e.target.value })} placeholder="选填，如付款比例 0.5" />
              </div>
            )}
          </div>

          {!isAbsoluteDate && (
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>触发参数2</Label>
                <Input value={formData.tge_param2} onChange={(e) => setFormData({ ...formData, tge_param2: e.target.value })} placeholder="选填" />
              </div>
              <div className="space-y-2">
                <Label>目标事件</Label>
                <Select value={formData.target_event} onValueChange={(v) => setFormData({ ...formData, target_event: v })}>
                  <SelectTrigger><SelectValue placeholder="选择目标事件" /></SelectTrigger>
                  <SelectContent>
                    {availableEvents.map(({ key, label }) => (
                      <SelectItem key={key} value={key}>{label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          )}

          {isAbsoluteDate && (
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>目标事件</Label>
                <Select value={formData.target_event} onValueChange={(v) => setFormData({ ...formData, target_event: v })}>
                  <SelectTrigger><SelectValue placeholder="选择目标事件" /></SelectTrigger>
                  <SelectContent>
                    {availableEvents.map(({ key, label }) => (
                      <SelectItem key={key} value={key}>{label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>目标参数1</Label>
              <Input value={formData.tae_param1} onChange={(e) => setFormData({ ...formData, tae_param1: e.target.value })} placeholder="选填" />
            </div>
            <div className="space-y-2">
              <Label>目标参数2</Label>
              <Input value={formData.tae_param2} onChange={(e) => setFormData({ ...formData, tae_param2: e.target.value })} placeholder="选填" />
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
            <Label>作用范围</Label>
            <Select value={formData.inherit} onValueChange={(v) => setFormData({ ...formData, inherit: v })}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {getInheritOptions(formData.related_type).map(opt => (
                  <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              {formData.inherit === '0' ? '将自动设为"生效"' : '将自动设为"模板"'}
            </p>
          </div>

          <div className="flex justify-between">
            <div>
              {mode === 'update' && rule && (
                <Button
                  type="button"
                  variant="destructive"
                  onClick={() => deleteMutation.mutate()}
                  disabled={deleteMutation.isPending}
                >
                  <Trash2 className="mr-2 h-4 w-4" />删除
                </Button>
              )}
            </div>
            <div className="flex gap-2">
              <Button type="button" variant="outline" onClick={() => setIsOpen(false)}>取消</Button>
              <Button type="submit" disabled={createMutation.isPending}>
                {createMutation.isPending ? '保存中...' : mode === 'create' ? '创建' : '保存'}
              </Button>
            </div>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function RuleCard({ rule, onUpdate }: { rule: TimeRule; onUpdate: () => void }) {
  return (
    <Card className="relative group">
      <CardContent className="pt-4">
        <div className="flex items-start justify-between">
          <div className="space-y-1 flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              <Badge variant="outline">{rule.related_type}</Badge>
              <Badge variant="outline">#{rule.related_id}</Badge>
              <Badge className={STATUS_COLORS[rule.status] || 'bg-gray-100'}>{STATUS_LABELS[rule.status] || rule.status}</Badge>
              {rule.warning && <Badge className={WARNING_COLORS[rule.warning]}><AlertTriangle className="h-3 w-3 mr-1" />{rule.warning}</Badge>}
            </div>
            <p className="text-sm font-medium">
              {getEventLabel(rule.trigger_event)} → {getEventLabel(rule.target_event)}
            </p>
            <p className="text-sm text-muted-foreground">
              {rule.direction === 'after' ? '之后' : '之前'} {rule.offset} {rule.unit}
            </p>
            {(rule.tge_param1 || rule.tge_param2 || rule.tae_param1 || rule.tae_param2 || rule.flag_time) && (
              <p className="text-xs text-muted-foreground mt-1">
                {rule.flag_time && <span>标杆日期: {rule.flag_time.split(' ')[0]} </span>}
                {rule.tge_param1 && <span>TGE({rule.tge_param1}) </span>}
                {rule.tae_param1 && <span>TAE({rule.tae_param1})</span>}
              </p>
            )}
          </div>
          <div className="opacity-0 group-hover:opacity-100 transition-opacity">
            <RuleFormDialog mode="update" rule={rule} onSuccess={onUpdate} />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

export function TimeRulesPage() {
  const [activeTab, setActiveTab] = useState('rules')
  const [statusFilter, setStatusFilter] = useState<string>('ALL')

  const { data: rules, isLoading, refetch } = useQuery({
    queryKey: ['rules-list', statusFilter],
    queryFn: () => rulesApi.list({
      status: statusFilter !== 'ALL' ? statusFilter as any : undefined,
      size: 100,
    }),
  })

  const { data: events } = useQuery({
    queryKey: ['system-events'],
    queryFn: () => rulesApi.getRecentEvents(50),
    enabled: activeTab === 'events',
  })

  const filteredRules = rules?.items?.filter(r => {
    if (statusFilter === 'ALL') return true
    return r.status === statusFilter
  }) || []

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">时间规则</h2>
        <RuleFormDialog mode="create" onSuccess={() => refetch()} />
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="rules">规则列表</TabsTrigger>
          <TabsTrigger value="events">系统事件</TabsTrigger>
        </TabsList>

        <TabsContent value="rules" className="space-y-4">
          <div className="flex gap-2 flex-wrap">
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-32">
                <SelectValue placeholder="状态" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ALL">全部</SelectItem>
                <SelectItem value="模板">模板</SelectItem>
                <SelectItem value="生效">生效中</SelectItem>
                <SelectItem value="有结果">已触发</SelectItem>
                <SelectItem value="结束">已结束</SelectItem>
              </SelectContent>
            </Select>
            <Button variant="outline" onClick={() => refetch()}>
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>

          {isLoading ? (
            <div className="text-center py-4">加载中...</div>
          ) : filteredRules.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredRules.map(rule => (
                <RuleCard key={rule.id} rule={rule} onUpdate={() => refetch()} />
              ))}
            </div>
          ) : (
            <div className="text-center py-4 text-muted-foreground">暂无规则</div>
          )}
        </TabsContent>

        <TabsContent value="events">
          {events && events.length > 0 ? (
            <Card>
              <CardContent className="p-0">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>时间</TableHead>
                      <TableHead>事件类型</TableHead>
                      <TableHead>描述</TableHead>
                      <TableHead>关联</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {events.map(event => (
                      <TableRow key={event.id}>
                        <TableCell className="text-sm">{formatDate(event.timestamp)}</TableCell>
                        <TableCell><Badge variant="outline">{event.event_type}</Badge></TableCell>
                        <TableCell>{event.description}</TableCell>
                        <TableCell>
                          {event.related_type && event.related_id && (
                            <Badge variant="outline">{event.related_type} #{event.related_id}</Badge>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          ) : (
            <div className="text-center py-4 text-muted-foreground">暂无事件</div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}
