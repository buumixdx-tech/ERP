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
                        p_id = o.address_info.get("pointId")
                        if not p_id and "pointName" in o.address_info:
                            p_obj = session.query(models.Point).filter(models.Point.name == o.address_info["pointName"]).first()
                            if p_obj: p_id = p_obj.id
                    
                    if not p_id:
                        p_id = vc.elements.get("point_id")

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
                                operational_status=OperationalStatus.OPERATING,
                                device_status=DeviceStatus.NORMAL,
                                virtual_contract_id=vc.id,
                                point_id=p_id,
                                deposit_amount=item.get("deposit", 0.0),
                                deposit_timestamp=datetime.now()
                            )
                            session.add(inv)
                            sn_index += 1
            session.flush() # Added session.flush() here
            from logic.deposit import deposit_module
            deposit_module(vc_id=vc.id, session=session)

        elif vc.type in [VCType.MATERIAL_PROCUREMENT, VCType.MATERIAL_SUPPLY]:
            orders = session.query(models.ExpressOrder).filter(models.ExpressOrder.logistics_id == logistics_id).all()
            for o in orders:
                if not o.items: continue
                for item in o.items:
                    norm = normalize_item_data(item)
                    sid, qty = norm["sku_id"], norm["qty"]
                    if not sid or qty <= 0: continue
                    
                    mat = session.query(models.MaterialInventory).filter(models.MaterialInventory.sku_id == sid).first()
                    if not mat:
                        mat = models.MaterialInventory(sku_id=sid, total_balance=0.0, average_price=0.0)
                        session.add(mat)
                        session.flush()
                    
                    if vc.type == VCType.MATERIAL_PROCUREMENT:
                        unit_price = 0.0
                        if "skus" in vc.elements:
                            for sk in vc.elements["skus"]:
                                snormal = normalize_item_data(sk)
                                if str(snormal["sku_id"]) == str(sid):
                                    unit_price = snormal["price"]
                                    break
                        elif "points" in vc.elements:
                            for p in vc.elements["points"]:
                                for sk in p.get("items", []):
                                    if str(sk.get("skuId") or sk.get("sku_id") or sk.get("id")) == str(sid):
                                        unit_price = float(sk.get("unitPrice") or sk.get("price") or 0)
                                        break
                                if unit_price > 0: break
                        
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
                        warehouse = norm["point_name"]
                        if warehouse == SystemConstants.UNKNOWN and o.address_info:
                            warehouse = o.address_info.get("pointName", SystemConstants.DEFAULT_WAREHOUSE)
                        if warehouse == SystemConstants.UNKNOWN: 
                            warehouse = SystemConstants.DEFAULT_WAREHOUSE
                            
                        dist[warehouse] = dist.get(warehouse, 0) + float(qty)
                        mat.stock_distribution = dist
                        flag_modified(mat, "stock_distribution")
                    else:
                        mat.total_balance = (mat.total_balance or 0.0) - float(qty)
                        dist = dict(mat.stock_distribution or {})
                        warehouse = item.get("source_warehouse") or item.get("sourceWarehouse") or norm.get("source_warehouse")
                        if (not warehouse or warehouse == SystemConstants.UNKNOWN or warehouse == SystemConstants.DEFAULT_WAREHOUSE) and o.address_info:
                            warehouse = o.address_info.get("sourceWarehouse") or o.address_info.get("pointName")
                        if not warehouse or warehouse == SystemConstants.UNKNOWN: 
                            warehouse = SystemConstants.DEFAULT_WAREHOUSE
                        
                        dist[warehouse] = dist.get(warehouse, 0) - float(qty)
                        mat.stock_distribution = dist
                        flag_modified(mat, "stock_distribution")

        elif vc.type == VCType.RETURN:
            orders = session.query(models.ExpressOrder).filter(models.ExpressOrder.logistics_id == logistics_id).all()
            direction = vc.elements.get("return_direction", SystemConstants.UNKNOWN)
            for o in orders:
                if not o.items: continue
                dest_p_id = None
                if o.address_info:
                    dest_p_id = o.address_info.get("pointId")
                    if not dest_p_id and "pointName" in o.address_info:
                        p_obj = session.query(models.Point).filter(models.Point.name == o.address_info["pointName"]).first()
                        if p_obj: dest_p_id = p_obj.id

                for item in o.items:
                    norm = normalize_item_data(item)
                    sid, sn = norm["sku_id"], norm["sn"]
                    qty, price = norm["qty"], norm["price"]
                    
                    if sn and sn != "-":
                        equip = session.query(models.EquipmentInventory).filter(models.EquipmentInventory.sn == sn).first()
                        if equip:
                            if dest_p_id: equip.point_id = dest_p_id
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
                            warehouse_name = norm["point_name"]
                            if (not warehouse_name or warehouse_name == SystemConstants.UNKNOWN) and o.address_info:
                                warehouse_name = o.address_info.get("pointName", SystemConstants.DEFAULT_WAREHOUSE)
                            
                            sku_obj = session.query(models.SKU).get(sid)
                            cost_price = float(sku_obj.params.get("unit_price") or 0.0) if (sku_obj and sku_obj.params) else price
                            new_total_val = (mat.total_balance * mat.average_price) + (qty * cost_price)
                            mat.total_balance += qty
                            if mat.total_balance > 0:
                                mat.average_price = new_total_val / mat.total_balance
                            dist[warehouse_name] = dist.get(warehouse_name, 0) + qty
                        elif ReturnDirection.US_TO_SUPPLIER in direction:
                            source_wh = item.get("point_name") or item.get("warehouse") or norm["point_name"]
                            if (not source_wh or source_wh == SystemConstants.UNKNOWN) and o.address_info:
                                source_wh = o.address_info.get("sourceWarehouse") or o.address_info.get("pointName")
                            if not source_wh or source_wh == SystemConstants.UNKNOWN: 
                                source_wh = SystemConstants.DEFAULT_WAREHOUSE
                            
                            mat.total_balance -= qty
                            dist[source_wh] = dist.get(source_wh, 0) - qty
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
        
        if not ext_session:
            session.commit()
    except Exception as e:
        print(f"DEBUG: Inventory Module Error: {str(e)}")
        if not ext_session:
            session.rollback()
    finally:
        if not ext_session:
            session.close()
