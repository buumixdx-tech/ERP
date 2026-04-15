import models
from datetime import datetime
from sqlalchemy.orm.attributes import flag_modified
import json
from logic.constants import VCType, VCStatus, SubjectStatus, CashStatus, ReturnDirection, CashFlowType, LogisticsStatus, OperationalStatus, DeviceStatus, SystemConstants
from logic.services import normalize_item_data

def inventory_module(logistics_id, equipment_sn_json=None, session=None):
    """
    库存模块：处理物流完成后的库存变动
    
    Args:
        logistics_id: 物流记录ID
        equipment_sn_json: 设备SN列表（可选）
        session: 数据库会话（可选，主要用于测试）
    """
    ext_session = session is not None
    if not ext_session:
        session = models.get_session()
    try:
        logistics = session.query(models.Logistics).filter(models.Logistics.id == logistics_id).first()
        if not logistics:
            return
        
        vc = session.query(models.VirtualContract).filter(models.VirtualContract.id == logistics.virtual_contract_id).first()
        if not vc:
            return
        
        if vc.type in [VCType.EQUIPMENT_PROCUREMENT, VCType.STOCK_PROCUREMENT]:
            sns = equipment_sn_json if equipment_sn_json else []
            orders = session.query(models.ExpressOrder).filter(models.ExpressOrder.logistics_id == logistics_id).all()
            
            sn_index = 0
            for o in orders:
                if not o.items: continue
                for item in o.items:
                    norm = normalize_item_data(item)
                    sid = norm["sku_id"]
                    qty = int(norm["qty"])
                    p_id = None
                    if o.address_info:
                        p_id = o.address_info.get("收货点位Id")
                        if not p_id and "收货点位名称" in o.address_info:
                            p_obj = session.query(models.Point).filter(models.Point.name == o.address_info["收货点位名称"]).first()
                            if p_obj: p_id = p_obj.id
                    
                    if not p_id:
                        vc_elems = (vc.elements or {}).get("elements", [])
                        if vc_elems:
                            p_id = vc_elems[0].get("receiving_point_id")

                    for _ in range(qty):
                        if sn_index < len(sns):
                            current_sn = sns[sn_index]
                            # 检查 SN 是否已存在
                            existing = session.query(models.EquipmentInventory).filter(
                                models.EquipmentInventory.sn == current_sn
                            ).first()
                            if existing:
                                print(f"DEBUG: SN {current_sn} 已存在，跳过")
                                sn_index += 1
                                continue
                            
                            inv = models.EquipmentInventory(
                                sku_id=sid,
                                sn=current_sn,
                                operational_status=OperationalStatus.STOCK if vc.type == VCType.STOCK_PROCUREMENT else OperationalStatus.OPERATING,
                                device_status=DeviceStatus.NORMAL,
                                virtual_contract_id=vc.id if vc.type == VCType.EQUIPMENT_PROCUREMENT else None,  # 库存采购不关联业务VC
                                point_id=p_id,
                                deposit_amount=item.get("deposit", 0.0),
                                deposit_timestamp=datetime.now()
                            )
                            session.add(inv)
                            sn_index += 1
            session.flush() # Added session.flush() here
            # 仅设备采购触发押金核算，库存采购不涉及押金
            if vc.type == VCType.EQUIPMENT_PROCUREMENT:
                from logic.deposit import deposit_module
                deposit_module(vc_id=vc.id, session=session)

        elif vc.type in [VCType.MATERIAL_PROCUREMENT, VCType.MATERIAL_SUPPLY]:
            orders = session.query(models.ExpressOrder).filter(models.ExpressOrder.logistics_id == logistics_id).all()
            for o in orders:
                if not o.items: continue
                # 从 address_info 获取仓库信息（items 只含 sku_id, sku_name, qty）
                addr_info = o.address_info or {}
                recv_point_id = addr_info.get("收货点位Id")
                recv_point_name = addr_info.get("收货点位名称", SystemConstants.DEFAULT_POINT)
                send_point_id = addr_info.get("发货点位Id")
                send_point_name = addr_info.get("发货点位名称", "")

                for item in o.items:
                    sid = item.get("sku_id")
                    qty = int(item.get("qty", 0))
                    if not sid or qty <= 0: continue

                    mat = session.query(models.MaterialInventory).filter(models.MaterialInventory.sku_id == sid).first()
                    if not mat:
                        mat = models.MaterialInventory(sku_id=sid, total_balance=0.0, average_price=0.0)
                        session.add(mat)
                        session.flush()

                    if vc.type == VCType.MATERIAL_PROCUREMENT:
                        unit_price = 0.0
                        vc_elems = (vc.elements or {}).get("elements", [])
                        for sk in vc_elems:
                            if str(sk.get("sku_id")) == str(sid):
                                unit_price = float(sk.get("price") or 0)
                                break

                        if unit_price > 0:
                            current_bal = mat.total_balance or 0.0
                            current_avg = mat.average_price or 0.0
                            old_total_val = current_bal * current_avg
                            new_total_val = old_total_val + (float(qty) * unit_price)
                            mat.total_balance = current_bal + float(qty)
                            if mat.total_balance > 0:
                                mat.average_price = new_total_val / mat.total_balance
                        else:
                            mat.total_balance = (mat.total_balance or 0.0) + float(qty)

                        dist = dict(mat.stock_distribution or {})
                        # 物料采购入库：收货点位ID作为库存分布键
                        point_key = str(recv_point_id) if recv_point_id else SystemConstants.DEFAULT_POINT

                        dist[point_key] = dist.get(point_key, 0) + float(qty)
                        mat.stock_distribution = dist
                        flag_modified(mat, "stock_distribution")
                    else:
                        mat.total_balance = (mat.total_balance or 0.0) - float(qty)
                        dist = dict(mat.stock_distribution or {})
                        # 物料供应出库：发货点位ID作为库存分布键
                        point_key = str(send_point_id) if send_point_id else SystemConstants.DEFAULT_POINT

                        dist[point_key] = dist.get(point_key, 0) - float(qty)
                        mat.stock_distribution = dist
                        flag_modified(mat, "stock_distribution")

        elif vc.type == VCType.RETURN:
            orders = session.query(models.ExpressOrder).filter(models.ExpressOrder.logistics_id == logistics_id).all()
            direction = getattr(vc, 'return_direction', None) or (vc.elements.get("return_direction") if vc.elements else SystemConstants.UNKNOWN)
            # 从 vc.elements 获取物品信息
            return_items_map = {}
            ret_elems = (vc.elements or {}).get("elements", [])
            for ri in ret_elems:
                # sn 可能在 sn_list 数组中（VCElementSchema），也可能在 sn 字段（旧结构）
                sn_val = ri.get("sn")
                if not sn_val or sn_val == "-":
                    sn_list = ri.get("sn_list") or []
                    sn_val = sn_list[0] if sn_list else "-"
                key = (ri.get("sku_id"), sn_val)
                return_items_map[key] = ri

            # equipment_sn_json 包含退货设备的 SN 列表（由 confirm_inbound 传入）
            # 用于直接定位设备记录进行位置/状态更新
            sns = equipment_sn_json if equipment_sn_json else []

            for o in orders:
                addr_info = o.address_info or {}
                # 收货点位信息
                recv_point_id = addr_info.get("收货点位Id")
                recv_point_name = addr_info.get("收货点位名称", SystemConstants.DEFAULT_POINT)
                # 发货点位信息
                send_point_id = addr_info.get("发货点位Id")
                send_point_name = addr_info.get("发货点位名称", "")

                if not o.items: continue
                for item in o.items:
                    sid = item.get("sku_id")
                    qty = int(item.get("qty", 0))
                    sn = item.get("sn", "-")
                    if not sid or qty <= 0: continue

                    # 优先使用 equipment_sn_json 中的 SN（来自 confirm_inbound）
                    # 其次使用 order item 中的 sn 字段
                    lookup_sn = None
                    if sns:
                        # 从 ret_elems 中查找匹配 sku_id 的 SN
                        for ri in ret_elems:
                            if int(ri.get("sku_id")) == int(sid):
                                ri_sn = ri.get("sn")
                                if not ri_sn or ri_sn == "-":
                                    sn_list = ri.get("sn_list") or []
                                    ri_sn = sn_list[0] if sn_list else "-"
                                if ri_sn and ri_sn != "-" and ri_sn in sns:
                                    lookup_sn = ri_sn
                                    break
                    if not lookup_sn:
                        lookup_sn = sn

                    # 从 vc.elements.return_items 查找完整信息
                    key = (sid, lookup_sn)
                    full_item = return_items_map.get(key) or {}
                    price = full_item.get("price", 0.0)

                    if lookup_sn and lookup_sn != "-":
                        equip = session.query(models.EquipmentInventory).filter(models.EquipmentInventory.sn == lookup_sn).first()
                        if equip:
                            if recv_point_id: equip.point_id = recv_point_id
                            if ReturnDirection.CUSTOMER_TO_US in direction:
                                equip.operational_status = OperationalStatus.STOCK
                            elif ReturnDirection.US_TO_SUPPLIER in direction:
                                equip.operational_status = OperationalStatus.DISPOSED
                            equip.deposit_amount = 0.0
                            equip.deposit_timestamp = datetime.now()
                    elif sid and qty > 0:
                        mat = session.query(models.MaterialInventory).filter(models.MaterialInventory.sku_id == sid).first()
                        if not mat:
                            mat = models.MaterialInventory(sku_id=sid, total_balance=0.0, average_price=0.0)
                            session.add(mat)
                            session.flush()
                        dist = dict(mat.stock_distribution or {})
                        if ReturnDirection.CUSTOMER_TO_US in direction:
                            # 退货到我方：收货点位ID作为库存分布键
                            point_key = str(recv_point_id) if recv_point_id else SystemConstants.DEFAULT_POINT

                            sku_obj = session.query(models.SKU).get(sid)
                            cost_price = float(sku_obj.params.get("unit_price") or 0.0) if (sku_obj and sku_obj.params) else price
                            new_total_val = (mat.total_balance * mat.average_price) + (qty * cost_price)
                            mat.total_balance += qty
                            if mat.total_balance > 0:
                                mat.average_price = new_total_val / mat.total_balance
                            dist[point_key] = dist.get(point_key, 0) + qty
                        elif ReturnDirection.US_TO_SUPPLIER in direction:
                            # 退货到供应商：发货点位ID作为库存分布键（减库存）
                            point_key = str(send_point_id) if send_point_id else SystemConstants.DEFAULT_POINT

                            mat.total_balance -= qty
                            dist[point_key] = dist.get(point_key, 0) - qty
                        mat.stock_distribution = dist
                        flag_modified(mat, "stock_distribution")

            # 尝试触发原采购VC的押金重算
            print(f"DEBUG: related_vc_id={vc.related_vc_id}")
            if vc.related_vc_id:
                # 先刷新数据库，确保设备状态变更已写入
                session.flush()
                # 触发原采购VC的押金重算
                print(f"DEBUG: Triggering deposit_module for original VC {vc.related_vc_id}")
                from logic.deposit import deposit_module
                deposit_module(vc_id=vc.related_vc_id, session=session)

        elif vc.type == VCType.INVENTORY_ALLOCATION:
            """
            库存拨付：把我们库存的设备发到客户指定的点位
            设备本来就是我们的，不新建库存记录，只修改 point_id 和状态变为 OPERATING
            """
            orders = session.query(models.ExpressOrder).filter(
                models.ExpressOrder.logistics_id == logistics_id
            ).all()

            for o in orders:
                if not o.items: continue
                addr_info = o.address_info or {}
                recv_point_id = addr_info.get("收货点位Id")  # 目标点位
                send_point_id = addr_info.get("发货点位Id")   # 源点位（必须）

                # 校验发货点位是否存在
                if not send_point_id:
                    from logic.base import ActionResult
                    return ActionResult(success=False, error="库存拨付缺少发货点位信息")

                for item in o.items:
                    sn = item.get("sn", "-")
                    if not sn or sn == "-": continue

                    equip = session.query(models.EquipmentInventory).filter(
                        models.EquipmentInventory.sn == sn
                    ).first()

                    # 找不到设备记录，报错
                    if not equip:
                        from logic.base import ActionResult
                        return ActionResult(success=False, error=f"设备 SN={sn} 不在库存中，无法进行库存拨付")

                    # 校验设备当前点位与发货点位一致，防止错误操作
                    if equip.point_id != send_point_id:
                        from logic.base import ActionResult
                        return ActionResult(success=False, error=f"设备 SN={sn} 当前不在发货点位，无法进行库存拨付")

                    if recv_point_id:
                        equip.point_id = recv_point_id
                    equip.operational_status = OperationalStatus.OPERATING
                    equip.virtual_contract_id = vc.id

        # === 库存流转（待 INVENTORY_TRANSFER 类型创建后实现）===
        # elif vc.type == VCType.INVENTORY_TRANSFER:
        #     """
        #     库存流转：设备/物料暂存供应商仓，发货到我们自己仓库
        #     所有权不变更，只修改 point_id
        #     - 设备：根据 sn 找到设备记录，更新 point_id
        #     - 物料：根据 sku_id 和仓库，更新 stock_distribution
        #     """

        if not ext_session:
            session.commit()
    except Exception as e:
        print(f"DEBUG: Inventory Module Error: {str(e)}")
        if not ext_session:
            session.rollback()
    finally:
        if not ext_session:
            session.close()
