import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Users, MapPin, Store, Package, Briefcase, Building, Upload, Plus, Pencil, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { masterApi, Customer, Point, Supplier, SKU } from '@/api/endpoints/master'
import { apiClient } from '@/api/client'

// 可扩展的类型配置 - 新增类型只需添加一项
const ENTRY_TYPES = [
  { value: 'customers', label: '渠道客户', icon: Users },
  { value: 'points', label: '点位', icon: MapPin },
  { value: 'suppliers', label: '供应商', icon: Store },
  { value: 'skus', label: 'SKU', icon: Package },
  { value: 'partners', label: '外部合作方', icon: Briefcase },
  { value: 'bank-accounts', label: '银行账户', icon: Building },
  { value: 'import-export', label: '批量导入导出', icon: Upload },
] as const

type EntryType = typeof ENTRY_TYPES[number]['value']

// Partner types
interface Partner {
  id: number
  name: string
  type: string
  address?: string
  remark?: string
}

interface BankAccount {
  id: number
  owner_type: string
  owner_id?: number
  owner_name?: string
  account_name: string
  bank_name: string
  account_number: string
  is_default: boolean
}

function CustomersTab() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [editingCustomer, setEditingCustomer] = useState<Customer | null>(null)
  const [isDialogOpen, setIsDialogOpen] = useState(false)

  const { data, isLoading } = useQuery({
    queryKey: ['customers', search],
    queryFn: () => masterApi.customers.list({ search, size: 100 }),
  })

  const createMutation = useMutation({
    mutationFn: masterApi.customers.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['customers'] })
      setIsDialogOpen(false)
    },
  })

  const updateMutation = useMutation({
    mutationFn: masterApi.customers.update,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['customers'] })
      setEditingCustomer(null)
      setIsDialogOpen(false)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (ids: number[]) => masterApi.customers.delete(ids),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['customers'] }),
  })

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const formData = new FormData(e.currentTarget)
    const payload = { name: formData.get('name') as string, info: formData.get('info') as string }
    if (editingCustomer) {
      updateMutation.mutate([{ ...editingCustomer, ...payload }])
    } else {
      createMutation.mutate(payload)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Input placeholder="搜索客户..." value={search} onChange={(e) => setSearch(e.target.value)} className="w-64" />
        </div>
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger asChild>
            <Button onClick={() => { setEditingCustomer(null); setIsDialogOpen(true) }}>
              <Plus className="mr-2 h-4 w-4" />新建客户
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>{editingCustomer ? '编辑客户' : '新建客户'}</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name">客户名称</Label>
                <Input id="name" name="name" defaultValue={editingCustomer?.name} required />
              </div>
              <div className="space-y-2">
                <Label htmlFor="info">整体信息描述</Label>
                <Textarea id="info" name="info" defaultValue={typeof editingCustomer?.info === 'string' ? editingCustomer?.info : ''} />
              </div>
              <div className="flex justify-end gap-2">
                <Button type="button" variant="outline" onClick={() => setIsDialogOpen(false)}>取消</Button>
                <Button type="submit" disabled={createMutation.isPending || updateMutation.isPending}>
                  {createMutation.isPending || updateMutation.isPending ? '保存中...' : '保存'}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>名称</TableHead>
                <TableHead>描述</TableHead>
                <TableHead className="w-[100px]">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data?.items?.map((customer) => (
                <TableRow key={customer.id}>
                  <TableCell className="font-medium">{customer.id}</TableCell>
                  <TableCell>{customer.name}</TableCell>
                  <TableCell className="text-muted-foreground">{typeof customer.info === 'string' ? customer.info : '-'}</TableCell>
                  <TableCell>
                    <div className="flex gap-2">
                      <Button variant="ghost" size="icon" onClick={() => { setEditingCustomer(customer); setIsDialogOpen(true) }}>
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="icon" onClick={() => deleteMutation.mutate([customer.id])}>
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
              {!data?.items?.length && (
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
    </div>
  )
}

function PointsTab() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [editingPoint, setEditingPoint] = useState<Point | null>(null)
  const [formData, setFormData] = useState({ name: '', type: '运营点位', address: '', customer_id: '', supplier_id: '' })

  const { data } = useQuery({
    queryKey: ['points', search],
    queryFn: () => masterApi.points.list({ search, size: 100 }),
  })

  const { data: customers } = useQuery({
    queryKey: ['customers'],
    queryFn: () => masterApi.customers.list({ size: 100 }),
  })

  const { data: suppliers } = useQuery({
    queryKey: ['suppliers'],
    queryFn: () => masterApi.suppliers.list({ size: 100 }),
  })

  const createMutation = useMutation({
    mutationFn: masterApi.points.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['points'] })
      setIsDialogOpen(false)
      setFormData({ name: '', type: '运营点位', address: '', customer_id: '', supplier_id: '' })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (ids: number[]) => masterApi.points.delete(ids),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['points'] }),
  })

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const payload: Record<string, unknown> = {
      name: formData.name,
      type: formData.type,
      address: formData.address,
      receiving_address: formData.address,
    }
    if (formData.customer_id) payload.customer_id = parseInt(formData.customer_id)
    if (formData.supplier_id) payload.supplier_id = parseInt(formData.supplier_id)
    createMutation.mutate(payload as unknown as Point)
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <Input placeholder="搜索点位..." value={search} onChange={(e) => setSearch(e.target.value)} className="w-64" />
        <Button onClick={() => { setEditingPoint(null); setIsDialogOpen(true) }}>
          <Plus className="mr-2 h-4 w-4" />新建点位
        </Button>
      </div>

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>名称</TableHead>
                <TableHead>类型</TableHead>
                <TableHead>地址</TableHead>
                <TableHead>货主</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data?.items?.map((point) => (
                <TableRow key={point.id}>
                  <TableCell className="font-medium">{point.id}</TableCell>
                  <TableCell>{point.name}</TableCell>
                  <TableCell><Badge variant="secondary">{point.type}</Badge></TableCell>
                  <TableCell className="text-muted-foreground">{point.address}</TableCell>
                  <TableCell className="text-muted-foreground">{point.owner_label || '-'}</TableCell>
                  <TableCell>
                    <div className="flex gap-2">
                      <Button variant="ghost" size="icon" onClick={() => deleteMutation.mutate([point.id])}>
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
              {!data?.items?.length && (
                <TableRow>
                  <TableCell colSpan={6} className="text-center text-muted-foreground">暂无数据</TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>新建点位</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label>点位名称</Label>
              <Input name="name" value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} required />
            </div>
            <div className="space-y-2">
              <Label>类型</Label>
              <Select value={formData.type} onValueChange={(v) => setFormData({ ...formData, type: v })}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="运营点位">运营点位</SelectItem>
                  <SelectItem value="客户仓">客户仓</SelectItem>
                  <SelectItem value="自有仓">自有仓</SelectItem>
                  <SelectItem value="转运仓">转运仓</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>货主</Label>
              <Select value={formData.customer_id || ''} onValueChange={(v) => setFormData({ ...formData, customer_id: v, supplier_id: '' })}>
                <SelectTrigger>
                  <SelectValue placeholder="无" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">无</SelectItem>
                  <SelectItem value="company">公司</SelectItem>
                  {customers?.items?.map(c => (
                    <SelectItem key={c.id} value={String(c.id)}>{c.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            {!formData.customer_id && (
              <div className="space-y-2">
                <Label>供应商</Label>
                <Select value={formData.supplier_id || ''} onValueChange={(v) => setFormData({ ...formData, supplier_id: v })}>
                  <SelectTrigger>
                    <SelectValue placeholder="无" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">无</SelectItem>
                    {suppliers?.items?.map(s => (
                      <SelectItem key={s.id} value={String(s.id)}>{s.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}
            <div className="space-y-2">
              <Label>地址</Label>
              <Input name="address" value={formData.address} onChange={(e) => setFormData({ ...formData, address: e.target.value })} />
            </div>
            <div className="flex justify-end gap-2">
              <Button type="button" variant="outline" onClick={() => setIsDialogOpen(false)}>取消</Button>
              <Button type="submit">保存</Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}

function SuppliersTab() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [formData, setFormData] = useState({ name: '', category: '', address: '' })

  const { data } = useQuery({
    queryKey: ['suppliers', search],
    queryFn: () => masterApi.suppliers.list({ search, size: 100 }),
  })

  const createMutation = useMutation({
    mutationFn: masterApi.suppliers.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['suppliers'] })
      setIsDialogOpen(false)
      setFormData({ name: '', category: '', address: '' })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (ids: number[]) => masterApi.suppliers.delete(ids),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['suppliers'] }),
  })

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    createMutation.mutate(formData)
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <Input placeholder="搜索供应商..." value={search} onChange={(e) => setSearch(e.target.value)} className="w-64" />
        <Button onClick={() => setIsDialogOpen(true)}><Plus className="mr-2 h-4 w-4" />新建供应商</Button>
      </div>

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>名称</TableHead>
                <TableHead>类别</TableHead>
                <TableHead>地址</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data?.items?.map((supplier) => (
                <TableRow key={supplier.id}>
                  <TableCell>{supplier.id}</TableCell>
                  <TableCell>{supplier.name}</TableCell>
                  <TableCell><Badge variant="secondary">{supplier.category || '-'}</Badge></TableCell>
                  <TableCell className="text-muted-foreground">{supplier.address || '-'}</TableCell>
                  <TableCell>
                    <Button variant="ghost" size="icon" onClick={() => deleteMutation.mutate([supplier.id])}>
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
              {!data?.items?.length && (
                <TableRow>
                  <TableCell colSpan={5} className="text-center text-muted-foreground">暂无数据</TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>新建供应商</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label>供应商名称</Label>
              <Input name="name" value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} required />
            </div>
            <div className="space-y-2">
              <Label>供应类别</Label>
              <Select value={formData.category} onValueChange={(v) => setFormData({ ...formData, category: v })}>
                <SelectTrigger>
                  <SelectValue placeholder="选择类别" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="设备">设备</SelectItem>
                  <SelectItem value="物料">物料</SelectItem>
                  <SelectItem value="设备+物料">设备+物料</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>地址信息</Label>
              <Input name="address" value={formData.address} onChange={(e) => setFormData({ ...formData, address: e.target.value })} />
            </div>
            <div className="flex justify-end gap-2">
              <Button type="button" variant="outline" onClick={() => setIsDialogOpen(false)}>取消</Button>
              <Button type="submit">保存</Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}

function SKUTab() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [formData, setFormData] = useState({ name: '', model: '', type_level1: '', supplier_id: '' })

  const { data } = useQuery({
    queryKey: ['skus', search],
    queryFn: () => masterApi.skus.list({ search, size: 100 }),
  })

  const { data: suppliers } = useQuery({
    queryKey: ['suppliers'],
    queryFn: () => masterApi.suppliers.list({ size: 100 }),
  })

  const createMutation = useMutation({
    mutationFn: masterApi.skus.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['skus'] })
      setIsDialogOpen(false)
      setFormData({ name: '', model: '', type_level1: '', supplier_id: '' })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (ids: number[]) => masterApi.skus.delete(ids),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['skus'] }),
  })

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    createMutation.mutate({
      ...formData,
      supplier_id: formData.supplier_id ? parseInt(formData.supplier_id) : 0,
    })
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <Input placeholder="搜索SKU..." value={search} onChange={(e) => setSearch(e.target.value)} className="w-64" />
        <Button onClick={() => setIsDialogOpen(true)}><Plus className="mr-2 h-4 w-4" />新建SKU</Button>
      </div>

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>名称</TableHead>
                <TableHead>型号</TableHead>
                <TableHead>一级分类</TableHead>
                <TableHead>供应商</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data?.items?.map((sku) => (
                <TableRow key={sku.id}>
                  <TableCell>{sku.id}</TableCell>
                  <TableCell>{sku.name}</TableCell>
                  <TableCell>{sku.model || '-'}</TableCell>
                  <TableCell><Badge variant="secondary">{sku.type_level1 || '-'}</Badge></TableCell>
                  <TableCell className="text-muted-foreground">
                    {suppliers?.items?.find(s => s.id === sku.supplier_id)?.name || '-'}
                  </TableCell>
                  <TableCell>
                    <Button variant="ghost" size="icon" onClick={() => deleteMutation.mutate([sku.id])}>
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
              {!data?.items?.length && (
                <TableRow>
                  <TableCell colSpan={6} className="text-center text-muted-foreground">暂无数据</TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>新建SKU</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label>供应商</Label>
              <Select value={formData.supplier_id} onValueChange={(v) => setFormData({ ...formData, supplier_id: v })}>
                <SelectTrigger>
                  <SelectValue placeholder="选择供应商" />
                </SelectTrigger>
                <SelectContent>
                  {suppliers?.items?.map(s => (
                    <SelectItem key={s.id} value={String(s.id)}>{s.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>SKU名称</Label>
              <Input name="name" value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} required />
            </div>
            <div className="space-y-2">
              <Label>型号</Label>
              <Input name="model" value={formData.model} onChange={(e) => setFormData({ ...formData, model: e.target.value })} />
            </div>
            <div className="space-y-2">
              <Label>一级分类</Label>
              <Select value={formData.type_level1} onValueChange={(v) => setFormData({ ...formData, type_level1: v })}>
                <SelectTrigger>
                  <SelectValue placeholder="选择分类" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="设备">设备</SelectItem>
                  <SelectItem value="物料">物料</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex justify-end gap-2">
              <Button type="button" variant="outline" onClick={() => setIsDialogOpen(false)}>取消</Button>
              <Button type="submit">保存</Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}

function PartnersTab() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [formData, setFormData] = useState({ name: '', type: 'OUTSOURCING', address: '', remark: '' })

  const { data, isLoading } = useQuery({
    queryKey: ['partners', search],
    queryFn: async () => {
      const res = await apiClient.get('/master/partners', { params: { search, size: 100 } }) as { items: Partner[]; total: number }
      return res
    },
  })

  const createMutation = useMutation({
    mutationFn: async (payload: { name: string; type: string; address?: string; remark?: string }) => {
      return apiClient.post('/master/create-partner', payload)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['partners'] })
      setIsDialogOpen(false)
      setFormData({ name: '', type: 'OUTSOURCING', address: '', remark: '' })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: async (ids: number[]) => {
      return apiClient.delete('/master/delete-partners', { data: ids.map(id => ({ id })) })
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['partners'] }),
  })

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    createMutation.mutate(formData)
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <Input placeholder="搜索合作方..." value={search} onChange={(e) => setSearch(e.target.value)} className="w-64" />
        <Button onClick={() => setIsDialogOpen(true)}><Plus className="mr-2 h-4 w-4" />新建合作方</Button>
      </div>

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>名称</TableHead>
                <TableHead>类型</TableHead>
                <TableHead>地址</TableHead>
                <TableHead>备注</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data?.items?.map((partner) => (
                <TableRow key={partner.id}>
                  <TableCell>{partner.id}</TableCell>
                  <TableCell>{partner.name}</TableCell>
                  <TableCell><Badge variant="secondary">{partner.type}</Badge></TableCell>
                  <TableCell className="text-muted-foreground">{partner.address || '-'}</TableCell>
                  <TableCell className="text-muted-foreground">{partner.remark || '-'}</TableCell>
                  <TableCell>
                    <Button variant="ghost" size="icon" onClick={() => deleteMutation.mutate([partner.id])}>
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
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

      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>新建合作方</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label>名称</Label>
              <Input name="name" value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} required />
            </div>
            <div className="space-y-2">
              <Label>类型</Label>
              <Select value={formData.type} onValueChange={(v) => setFormData({ ...formData, type: v })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="OUTSOURCING">外包</SelectItem>
                  <SelectItem value="CUSTOMER_AFFILIATE">客户关联</SelectItem>
                  <SelectItem value="SUPPLIER_AFFILIATE">供应商关联</SelectItem>
                  <SelectItem value="OTHER">其他</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>地址</Label>
              <Input name="address" value={formData.address} onChange={(e) => setFormData({ ...formData, address: e.target.value })} />
            </div>
            <div className="space-y-2">
              <Label>备注</Label>
              <Textarea name="remark" value={formData.remark} onChange={(e) => setFormData({ ...formData, remark: e.target.value })} />
            </div>
            <div className="flex justify-end gap-2">
              <Button type="button" variant="outline" onClick={() => setIsDialogOpen(false)}>取消</Button>
              <Button type="submit">保存</Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}

function BankAccountsTab() {
  const queryClient = useQueryClient()
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [formData, setFormData] = useState({
    owner_type: 'Ourselves',
    account_name: '',
    bank_name: '',
    account_number: '',
    is_default: false,
  })

  const { data, isLoading } = useQuery({
    queryKey: ['bank-accounts-all'],
    queryFn: async () => {
      const res = await apiClient.get('/master/bank-accounts', { params: { size: 100 } }) as BankAccount[]
      return res
    },
  })

  const createMutation = useMutation({
    mutationFn: async (payload: typeof formData) => {
      return apiClient.post('/master/create-bank-account', {
        owner_type: payload.owner_type,
        account_info: {
          account_name: payload.account_name,
          bank_name: payload.bank_name,
          account_no: payload.account_number,
        },
        is_default: payload.is_default,
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['bank-accounts-all'] })
      setIsDialogOpen(false)
      setFormData({ owner_type: 'Ourselves', account_name: '', bank_name: '', account_number: '', is_default: false })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: async (ids: number[]) => {
      return apiClient.delete('/master/delete-bank-accounts', { data: ids.map(id => ({ id })) })
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['bank-accounts-all'] }),
  })

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    createMutation.mutate(formData)
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-medium">银行账户</h3>
        <Button onClick={() => setIsDialogOpen(true)}><Plus className="mr-2 h-4 w-4" />新建账户</Button>
      </div>

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>账户名称</TableHead>
                <TableHead>开户行</TableHead>
                <TableHead>账号</TableHead>
                <TableHead>所有者</TableHead>
                <TableHead>默认</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data?.map((acc) => (
                <TableRow key={acc.id}>
                  <TableCell>{acc.id}</TableCell>
                  <TableCell>{acc.account_name}</TableCell>
                  <TableCell>{acc.bank_name}</TableCell>
                  <TableCell className="font-mono">{acc.account_number}</TableCell>
                  <TableCell><Badge variant="outline">{acc.owner_type}</Badge></TableCell>
                  <TableCell>{acc.is_default ? '是' : '-'}</TableCell>
                  <TableCell>
                    <Button variant="ghost" size="icon" onClick={() => deleteMutation.mutate([acc.id])}>
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
              {!data?.length && (
                <TableRow>
                  <TableCell colSpan={7} className="text-center text-muted-foreground">
                    {isLoading ? '加载中...' : '暂无数据'}
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>新建银行账户</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label>所有者类型</Label>
              <Select value={formData.owner_type} onValueChange={(v) => setFormData({ ...formData, owner_type: v })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="Ourselves">我方</SelectItem>
                  <SelectItem value="Customer">客户</SelectItem>
                  <SelectItem value="Supplier">供应商</SelectItem>
                  <SelectItem value="Partner">合作方</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>账户名称</Label>
              <Input name="account_name" value={formData.account_name} onChange={(e) => setFormData({ ...formData, account_name: e.target.value })} required />
            </div>
            <div className="space-y-2">
              <Label>开户行</Label>
              <Input name="bank_name" value={formData.bank_name} onChange={(e) => setFormData({ ...formData, bank_name: e.target.value })} required />
            </div>
            <div className="space-y-2">
              <Label>账号</Label>
              <Input name="account_number" value={formData.account_number} onChange={(e) => setFormData({ ...formData, account_number: e.target.value })} required />
            </div>
            <div className="flex justify-end gap-2">
              <Button type="button" variant="outline" onClick={() => setIsDialogOpen(false)}>取消</Button>
              <Button type="submit">保存</Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}

function ImportExportTab() {
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState<{ success: number; failed: number; errors: string[] } | null>(null)

  const handleImport = async () => {
    if (!file) return
    setUploading(true)
    setResult(null)

    try {
      const formData = new FormData()
      formData.append('file', file)
      // Note: This would need a real API endpoint
      const res = await apiClient.post('/master/import', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      }) as unknown as { success: number; failed: number; errors: string[] }
      setResult({ success: res?.success || 0, failed: res?.failed || 0, errors: res?.errors || [] })
    } catch (err) {
      setResult({ success: 0, failed: 0, errors: ['导入失败，请检查文件格式'] })
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>批量导入导出</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>上传文件</Label>
            <Input type="file" accept=".xlsx,.xls,.json" onChange={(e) => setFile(e.target.files?.[0] || null)} />
            <p className="text-sm text-muted-foreground">支持 .xlsx, .xls, .json 格式</p>
          </div>
          <Button onClick={handleImport} disabled={!file || uploading}>
            {uploading ? '导入中...' : '开始导入'}
          </Button>

          {result && (
            <div className="mt-4 space-y-2">
              <p className="text-green-600">成功: {result.success} 条</p>
              {result.failed > 0 && <p className="text-red-600">失败: {result.failed} 条</p>}
              {result.errors.map((err, i) => (
                <p key={i} className="text-sm text-muted-foreground">{err}</p>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

export function EntryPage() {
  const [activeType, setActiveType] = useState<EntryType>('customers')

  const renderContent = () => {
    switch (activeType) {
      case 'customers': return <CustomersTab />
      case 'points': return <PointsTab />
      case 'suppliers': return <SuppliersTab />
      case 'skus': return <SKUTab />
      case 'partners': return <PartnersTab />
      case 'bank-accounts': return <BankAccountsTab />
      case 'import-export': return <ImportExportTab />
      default: return <CustomersTab />
    }
  }

  const currentType = ENTRY_TYPES.find(t => t.value === activeType)

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <h2 className="text-2xl font-bold">信息录入与维护</h2>
        <Select value={activeType} onValueChange={(v) => setActiveType(v as EntryType)}>
          <SelectTrigger className="w-40">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {ENTRY_TYPES.map((type) => (
              <SelectItem key={type.value} value={type.value}>
                <div className="flex items-center gap-2">
                  <type.icon className="h-4 w-4" />
                  {type.label}
                </div>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      {renderContent()}
    </div>
  )
}
