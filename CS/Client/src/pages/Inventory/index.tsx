import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { RefreshCw, Package, Cog } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { inventoryApi, EquipmentInventory, MaterialInventory, OperationalStatus, DeviceStatus, MaterialStatus } from '@/api/endpoints/inventory'
import { formatCurrency, formatDate } from '@/lib/utils'

const OPERATIONAL_STATUS_LABELS: Record<OperationalStatus, string> = {
  IN_STOCK: '库存',
  IN_OPERATION: '运营中',
  DISPOSAL: '已处置',
}

const DEVICE_STATUS_LABELS: Record<DeviceStatus, string> = {
  NORMAL: '正常',
  MAINTENANCE: '维护中',
  DAMAGED: '损坏',
  FAULT: '故障',
  MAINTENANCE_REQUIRED: '需要维护',
  LOCKED: '已锁定',
}

const DEVICE_STATUS_COLORS: Record<string, string> = {
  NORMAL: 'bg-green-100 text-green-800',
  MAINTENANCE: 'bg-yellow-100 text-yellow-800',
  DAMAGED: 'bg-red-100 text-red-800',
  FAULT: 'bg-red-100 text-red-800',
  MAINTENANCE_REQUIRED: 'bg-orange-100 text-orange-800',
  LOCKED: 'bg-gray-100 text-gray-800',
}

const MATERIAL_STATUS_LABELS: Record<string, string> = {
  active: '可用',
  depleted: '已用完',
}

const MATERIAL_STATUS_COLORS: Record<string, string> = {
  active: 'bg-green-100 text-green-800',
  depleted: 'bg-gray-100 text-gray-800',
  // 处理 null/undefined 状态
  default: 'bg-gray-100 text-gray-800',
}

function EquipmentDetailDialog({ equipment }: { equipment: EquipmentInventory }) {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <Label className="text-muted-foreground">序列号</Label>
          <p className="font-mono font-medium">{equipment.sn}</p>
        </div>
        <div>
          <Label className="text-muted-foreground">SKU</Label>
          <p>{equipment.sku_name}</p>
        </div>
        <div>
          <Label className="text-muted-foreground">运营状态</Label>
          <p>{OPERATIONAL_STATUS_LABELS[equipment.operational_status]}</p>
        </div>
        <div>
          <Label className="text-muted-foreground">设备状态</Label>
          <Badge className={DEVICE_STATUS_COLORS[equipment.device_status]}>
            {DEVICE_STATUS_LABELS[equipment.device_status]}
          </Badge>
        </div>
        <div>
          <Label className="text-muted-foreground">押金</Label>
          <p>{formatCurrency(equipment.deposit_amount)}</p>
        </div>
        <div>
          <Label className="text-muted-foreground">点位</Label>
          <p>{equipment.point_name || '-'}</p>
        </div>
        {equipment.vc_id && (
          <div>
            <Label className="text-muted-foreground">关联合同</Label>
            <Badge variant="outline">VC-{equipment.vc_id}</Badge>
          </div>
        )}
        <div>
          <Label className="text-muted-foreground">创建时间</Label>
          <p>{formatDate(equipment.created_at)}</p>
        </div>
      </div>
    </div>
  )
}

export function InventoryPage() {
  const [selectedEquipment, setSelectedEquipment] = useState<EquipmentInventory | null>(null)

  const { data: equipment, isLoading: eqLoading, refetch: eqRefetch } = useQuery({
    queryKey: ['equipment-list'],
    queryFn: () => inventoryApi.getEquipment({ size: 100 }),
  })

  const { data: material, isLoading: matLoading, refetch: matRefetch, error: matError } = useQuery({
    queryKey: ['material-list'],
    queryFn: () => inventoryApi.getMaterial({ size: 100 }),
  })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">库存看板</h2>
      </div>

      <Tabs defaultValue="equipment">
        <TabsList>
          <TabsTrigger value="equipment">
            <Cog className="mr-2 h-4 w-4" />设备库存
          </TabsTrigger>
          <TabsTrigger value="material">
            <Package className="mr-2 h-4 w-4" />物料库存
          </TabsTrigger>
        </TabsList>

        <TabsContent value="equipment" className="space-y-4">
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => eqRefetch()}>
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>

          {/* Summary */}
          <div className="grid grid-cols-4 gap-4">
            <Card>
              <CardContent className="pt-4">
                <div className="text-2xl font-bold">{equipment?.total || 0}</div>
                <p className="text-sm text-muted-foreground">设备总数</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-4">
                <div className="text-2xl font-bold text-green-600">
                  {equipment?.items?.filter(e => e.operational_status === 'IN_OPERATION').length || 0}
                </div>
                <p className="text-sm text-muted-foreground">运营中</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-4">
                <div className="text-2xl font-bold text-blue-600">
                  {equipment?.items?.filter(e => e.operational_status === 'IN_STOCK').length || 0}
                </div>
                <p className="text-sm text-muted-foreground">库存</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-4">
                <div className="text-2xl font-bold text-red-600">
                  {equipment?.items?.filter(e => e.device_status === 'FAULT' || e.device_status === 'DAMAGED').length || 0}
                </div>
                <p className="text-sm text-muted-foreground">异常</p>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>序列号</TableHead>
                    <TableHead>SKU</TableHead>
                    <TableHead>运营状态</TableHead>
                    <TableHead>设备状态</TableHead>
                    <TableHead>押金</TableHead>
                    <TableHead>点位</TableHead>
                    <TableHead>关联合同</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {equipment?.items?.map(eq => (
                    <TableRow key={eq.sn} className="cursor-pointer" onClick={() => setSelectedEquipment(eq)}>
                      <TableCell className="font-mono font-medium">{eq.sn}</TableCell>
                      <TableCell>{eq.sku_name}</TableCell>
                      <TableCell>{OPERATIONAL_STATUS_LABELS[eq.operational_status]}</TableCell>
                      <TableCell>
                        <Badge className={DEVICE_STATUS_COLORS[eq.device_status]}>
                          {DEVICE_STATUS_LABELS[eq.device_status]}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">{formatCurrency(eq.deposit_amount)}</TableCell>
                      <TableCell>{eq.point_name || '-'}</TableCell>
                      <TableCell>
                        {eq.vc_id && <Badge variant="outline">VC-{eq.vc_id}</Badge>}
                      </TableCell>
                    </TableRow>
                  ))}
                  {!equipment?.items?.length && (
                    <TableRow>
                      <TableCell colSpan={7} className="text-center text-muted-foreground">
                        {eqLoading ? '加载中...' : '暂无数据'}
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="material" className="space-y-4">
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => matRefetch()}>
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>

          {/* Summary */}
          <div className="grid grid-cols-3 gap-4">
            <Card>
              <CardContent className="pt-4">
                <div className="text-2xl font-bold">{material?.total || 0}</div>
                <p className="text-sm text-muted-foreground">批次总数</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-4">
                <div className="text-2xl font-bold">
                  {material?.items?.reduce((sum, m) => sum + m.quantity, 0) || 0}
                </div>
                <p className="text-sm text-muted-foreground">物料总量</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-4">
                <div className="text-2xl font-bold text-green-600">
                  {material?.items?.filter(m => m.status === 'active' || m.status == null).length || 0}
                </div>
                <p className="text-sm text-muted-foreground">可用批次</p>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>SKU</TableHead>
                    <TableHead>批次号</TableHead>
                    <TableHead>仓库</TableHead>
                    <TableHead className="text-right">数量</TableHead>
                    <TableHead className="text-right">单价</TableHead>
                    <TableHead>生产日期</TableHead>
                    <TableHead>有效期</TableHead>
                    <TableHead>状态</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {material?.items?.map(m => (
                    <TableRow key={m.id}>
                      <TableCell className="font-medium">{m.sku_name}</TableCell>
                      <TableCell className="font-mono text-sm">{m.batch_no}</TableCell>
                      <TableCell>{m.warehouse_point_name}</TableCell>
                      <TableCell className="text-right">{m.quantity.toFixed(2)}</TableCell>
                      <TableCell className="text-right">{formatCurrency(m.average_price)}</TableCell>
                      <TableCell className="text-sm">{m.production_date ? formatDate(m.production_date) : '-'}</TableCell>
                      <TableCell className="text-sm">{m.expiration_date ? formatDate(m.expiration_date) : '-'}</TableCell>
                      <TableCell>
                        <Badge className={MATERIAL_STATUS_COLORS[m.status] || MATERIAL_STATUS_COLORS.default}>
                          {MATERIAL_STATUS_LABELS[m.status] || m.status || '未知'}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                  {!material?.items?.length && (
                    <TableRow>
                      <TableCell colSpan={8} className="text-center text-muted-foreground">
                        {matLoading ? '加载中...' : matError ? `错误: ${matError.message}` : '暂无数据'}
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {selectedEquipment && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <Card className="w-full max-w-lg mx-4">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>设备详情</CardTitle>
              <Button variant="ghost" size="sm" onClick={() => setSelectedEquipment(null)}>关闭</Button>
            </CardHeader>
            <CardContent>
              <EquipmentDetailDialog equipment={selectedEquipment} />
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
