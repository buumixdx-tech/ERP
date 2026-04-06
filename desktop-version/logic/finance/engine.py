from models import (
    get_session, Logistics, CashFlow, VirtualContract, SKU, 
    EquipmentInventory, MaterialInventory, Supplier, ChannelCustomer, ExternalPartner,
    FinanceAccount, FinancialJournal, CashFlowLedger, BankAccount
)
import os
import json
import uuid
from datetime import datetime
from sqlalchemy import func
from logic.constants import (
    VCType, VCStatus, SubjectStatus, CashStatus, ReturnDirection, 
    CashFlowType, AccountLevel1, CounterpartType, AccountOwnerType, 
    LogisticsBearer, BankInfoKey
)

VOUCHER_DIR = 'data/finance/finance-voucher'
REPORT_DIR = 'data/finance/finance-report'

ACCOUNT_CONFIG = {
    AccountLevel1.CASH: {"category": "资产", "direction": "Debit"},
    AccountLevel1.INVENTORY: {"category": "资产", "direction": "Debit"},
    AccountLevel1.FIXED_ASSET: {"category": "资产", "direction": "Debit"},
    AccountLevel1.AR: {"category": "资产", "direction": "Debit"},
    AccountLevel1.PREPAYMENT: {"category": "资产", "direction": "Debit"},
    AccountLevel1.DEPOSIT_RECEIVABLE: {"category": "资产", "direction": "Debit"},
    AccountLevel1.OTHER_RECEIVABLE: {"category": "资产", "direction": "Debit"},
    AccountLevel1.AP: {"category": "负债", "direction": "Credit"},
    AccountLevel1.PRE_COLLECTION: {"category": "负债", "direction": "Credit"},
    AccountLevel1.DEPOSIT_PAYABLE: {"category": "负债", "direction": "Credit"},
    AccountLevel1.OTHER_PAYABLE: {"category": "负债", "direction": "Credit"},
    "应付款": {"category": "负债", "direction": "Credit"},
    AccountLevel1.EQUITY: {"category": "所有者权益", "direction": "Credit"},
    AccountLevel1.REVENUE: {"category": "损益", "direction": "Credit"},
    AccountLevel1.NON_OP_REVENUE_PENALTY: {"category": "损益", "direction": "Credit"},
    AccountLevel1.COST: {"category": "损益", "direction": "Debit"},
    AccountLevel1.EXPENSE: {"category": "损益", "direction": "Debit"},
    AccountLevel1.NON_OP_COST_PENALTY: {"category": "损益", "direction": "Debit"},
}

def finance_module(logistics_id=None, cash_flow_id=None, session=None):
    ext_session = session is not None
    if not ext_session:
        session = get_session()
    try:
        if logistics_id:
            process_logistics_finance(session, logistics_id)
        if cash_flow_id:
            process_cash_flow_finance(session, cash_flow_id)
        if not ext_session:
            session.commit()
    except Exception as e:
        if not ext_session:
            session.rollback()
        raise e
    finally:
        if not ext_session:
            session.close()

def get_or_create_account(session, level1_name, counterpart_type=None, counterpart_id=None):
    config = ACCOUNT_CONFIG.get(level1_name, {"category": "其他", "direction": "Debit"})
    level2_name = None
    if counterpart_type and counterpart_id:
        if counterpart_type == CounterpartType.CUSTOMER:
            obj = session.query(ChannelCustomer).get(counterpart_id)
            if obj: level2_name = f"{level1_name} - {obj.name}"
        elif counterpart_type == CounterpartType.SUPPLIER:
            obj = session.query(Supplier).get(counterpart_id)
            if obj: level2_name = f"{level1_name} - {obj.name}"
        elif counterpart_type == CounterpartType.PARTNER:
            obj = session.query(ExternalPartner).get(counterpart_id)
            if obj: level2_name = f"{level1_name} - {obj.name}"
        elif counterpart_type == CounterpartType.BANK_ACCOUNT:
            obj = session.query(BankAccount).get(counterpart_id)
            if obj:
                info = obj.account_info or {}
                bname = info.get(BankInfoKey.BANK_NAME, '未知银行')
                acc_no = str(info.get(BankInfoKey.ACCOUNT_NO, ''))[-4:]
                level2_name = f"{level1_name} - {bname} ({acc_no})"
            
    q = session.query(FinanceAccount).filter(FinanceAccount.level1_name == level1_name)
    if level2_name:
        q = q.filter(FinanceAccount.level2_name == level2_name)
    else:
        q = q.filter(FinanceAccount.level2_name == None)
        
    account = q.first()
    if not account:
        account = FinanceAccount(
            category=config["category"], level1_name=level1_name,
            level2_name=level2_name, counterpart_type=counterpart_type,
            counterpart_id=counterpart_id, direction=config["direction"]
        )
        session.add(account)
        session.flush()
    return account

def record_entries(session, voucher_no, ref_vc_id, ref_type, ref_id, entries, transaction_date=None):
    if not transaction_date:
        transaction_date = datetime.now()
    db_entries = []
    for entry in entries:
        acc = get_or_create_account(session, entry["level1"], entry.get("cp_type"), entry.get("cp_id"))
        journal = FinancialJournal(
            voucher_no=voucher_no, account_id=acc.id,
            debit=entry.get("debit", 0.0), credit=entry.get("credit", 0.0),
            summary=entry.get("summary", ""), ref_type=ref_type,
            ref_id=ref_id, ref_vc_id=ref_vc_id, transaction_date=transaction_date
        )
        session.add(journal)
        db_entries.append(journal)
        if acc.level1_name == AccountLevel1.CASH:
            amount = entry.get("debit", 0.0) or entry.get("credit", 0.0)
            if amount > 0:
                direction = "流入" if entry.get("debit", 0.0) > 0 else "流出"
                cf_ledger = CashFlowLedger(main_category="经营性", direction=direction, amount=amount)
                journal.cash_flow_record = cf_ledger
    session.flush()
    backup_data = {
        "voucher_no": voucher_no, "ref_vc_id": ref_vc_id,
        "ref_type": ref_type, "ref_id": ref_id,
        "timestamp": transaction_date.isoformat(),
        "entries": [
             {
                 "account": f"{e.account.level1_name}{' - ' + e.account.level2_name if e.account.level2_name else ''}",
                 "debit": e.debit, "credit": e.credit, "summary": e.summary
             } for e in db_entries
        ]
    }
    save_voucher(backup_data, f"{ref_type}_{ref_id}")
    update_report(backup_data)

def process_logistics_finance(session, logistics_id):
    from logic.services import get_logistics_finance_context
    ctx = get_logistics_finance_context(session, logistics_id)
    if not ctx or not ctx["can_process"]: return
    if ctx.get("is_duplicate"):
        ctx["logistics"].finance_triggered = True
        return
    logistics, vc = ctx["logistics"], ctx["vc"]
    cp_type, cp_id = ctx["cp_type"], ctx["cp_id"]
    total_amount, items_cost = ctx["total_amount"], ctx["items_cost"]
    logistics.finance_triggered = True
    voucher_no = f"LOG-{logistics_id}-{uuid.uuid4().hex[:6].upper()}"
    entries = []
    if vc.type in [VCType.EQUIPMENT_PROCUREMENT, VCType.STOCK_PROCUREMENT]:
        entries.append({"level1": AccountLevel1.FIXED_ASSET, "debit": total_amount, "summary": "采购设备入库"})
        entries.append({"level1": AccountLevel1.AP, "cp_type": cp_type, "cp_id": cp_id, "credit": total_amount, "summary": "入库挂账"})
    elif vc.type == VCType.MATERIAL_PROCUREMENT:
        entries.append({"level1": AccountLevel1.INVENTORY, "debit": total_amount, "summary": "采购物料入库"})
        entries.append({"level1": AccountLevel1.AP, "cp_type": cp_type, "cp_id": cp_id, "credit": total_amount, "summary": "入库挂账"})
    elif vc.type == VCType.MATERIAL_SUPPLY:
        entries.append({"level1": AccountLevel1.REVENUE, "credit": total_amount, "summary": "物料供应确认收入"})
        entries.append({"level1": AccountLevel1.AR, "cp_type": cp_type, "cp_id": cp_id, "debit": total_amount, "summary": "交付挂账"})
        if items_cost > 0:
            entries.append({"level1": AccountLevel1.COST, "debit": items_cost, "summary": f"结转物料销售成本 (VC:{vc.id})"})
            entries.append({"level1": AccountLevel1.INVENTORY, "credit": items_cost, "summary": "物料发出"})
    elif vc.type == VCType.RETURN:
        original_vc = session.query(VirtualContract).get(vc.related_vc_id) if vc.related_vc_id else None
        # 优先读 VC 表字段，兼容旧数据（仍在 elements 中的 return_direction）
        direction = vc.return_direction or (vc.elements.get("return_direction") if vc.elements else None)
        goods_amount = float(vc.elements.get("goods_amount") or 0)
        if direction and ReturnDirection.CUSTOMER_TO_US in direction:
            if items_cost > 0:
                target_acc = AccountLevel1.FIXED_ASSET if (original_vc and original_vc.type in [VCType.EQUIPMENT_PROCUREMENT, VCType.STOCK_PROCUREMENT]) else AccountLevel1.INVENTORY
                entries.append({"level1": target_acc, "debit": items_cost, "summary": f"物样回收物理入库 (VC:{vc.id})"})
                entries.append({"level1": AccountLevel1.COST, "credit": items_cost, "summary": "冲回成本"})
            if goods_amount > 0:
                entries.append({"level1": AccountLevel1.REVENUE, "debit": goods_amount, "summary": f"销售退回-收入冲减 (VC:{vc.id})"})
                entries.append({"level1": AccountLevel1.AR, "cp_type": cp_type, "cp_id": cp_id, "credit": goods_amount, "summary": "退货冲抵应收"})
        elif direction and ReturnDirection.US_TO_SUPPLIER in direction:
            inv_acc = AccountLevel1.INVENTORY
            if original_vc and original_vc.type in [VCType.EQUIPMENT_PROCUREMENT, VCType.STOCK_PROCUREMENT]: inv_acc = AccountLevel1.FIXED_ASSET
            if goods_amount > 0:
                entries.append({"level1": inv_acc, "credit": goods_amount, "summary": f"物样退还供应商 (VC:{vc.id})"})
                entries.append({"level1": AccountLevel1.AP, "cp_type": cp_type, "cp_id": cp_id, "debit": goods_amount, "summary": "退货冲减应付"})
        log_fee = float(vc.elements.get("logistics_cost") or 0)
        bearer = vc.elements.get("logistics_bearer")
        if log_fee > 0:
            if ReturnDirection.CUSTOMER_TO_US in direction:
                if bearer == LogisticsBearer.RECEIVER:
                    entries.append({"level1": AccountLevel1.EXPENSE, "debit": log_fee, "summary": "退货物流费(我方承担)"})
                    entries.append({"level1": AccountLevel1.AR, "cp_type": cp_type, "cp_id": cp_id, "credit": log_fee, "summary": "物流费补偿"})
                elif bearer == LogisticsBearer.SENDER:
                    entries.append({"level1": AccountLevel1.AR, "cp_type": cp_type, "cp_id": cp_id, "debit": log_fee, "summary": "客户自付物流费"})
                    entries.append({"level1": AccountLevel1.EXPENSE, "credit": log_fee, "summary": "收回代垫"})
            else:
                if bearer == LogisticsBearer.SENDER:
                    entries.append({"level1": AccountLevel1.EXPENSE, "debit": log_fee, "summary": "退供应商物流费(我方承担)"})
                    entries.append({"level1": AccountLevel1.AP, "cp_type": cp_type, "cp_id": cp_id, "credit": log_fee, "summary": "物流费自担"})
                elif bearer == LogisticsBearer.RECEIVER:
                    entries.append({"level1": AccountLevel1.AP, "cp_type": cp_type, "cp_id": cp_id, "debit": log_fee, "summary": "代垫物流费"})
                    entries.append({"level1": AccountLevel1.EXPENSE, "credit": log_fee, "summary": "冲销代垫"})
    if entries:
        record_entries(session, voucher_no, vc.id, "Logistics", logistics_id, entries, logistics.timestamp)

def process_cash_flow_finance(session, cash_flow_id):
    from logic.services import get_cashflow_finance_context
    ctx = get_cashflow_finance_context(session, cash_flow_id)
    if not ctx or not ctx["can_process"]: return
    cf, vc = ctx["cf"], ctx["vc"]
    cp_type, cp_id = ctx["cp_type"], ctx["cp_id"]
    is_income, ar_ap_amt, pre_amt, our_bank_id = ctx["is_income"], ctx["ar_ap_amt"], ctx["pre_amt"], ctx["our_bank_id"]
    voucher_no = f"CSH-{cash_flow_id}-{uuid.uuid4().hex[:6].upper()}"
    entries = []
    def get_money_entry(amount, is_income=True, summary="资金收付"):
        debit, credit = (amount, 0) if is_income else (0, amount)
        entry = {"level1": AccountLevel1.CASH, "debit": debit, "credit": credit, "summary": summary}
        if our_bank_id: entry["cp_type"] = CounterpartType.BANK_ACCOUNT; entry["cp_id"] = our_bank_id
        return entry
    if cf.type in [CashFlowType.PREPAYMENT, CashFlowType.FULFILLMENT]:
        if is_income:
            entries.append(get_money_entry(cf.amount, is_income=True, summary=f"收到资金 ({cf.type})"))
            if ar_ap_amt > 0: entries.append({"level1": AccountLevel1.AR, "cp_type": cp_type, "cp_id": cp_id, "credit": ar_ap_amt, "summary": "核销应收"})
            if pre_amt > 0: entries.append({"level1": AccountLevel1.PRE_COLLECTION, "cp_type": cp_type, "cp_id": cp_id, "credit": pre_amt, "summary": "计入预收"})
        else:
            if ar_ap_amt > 0: entries.append({"level1": AccountLevel1.AP, "cp_type": cp_type, "cp_id": cp_id, "debit": ar_ap_amt, "summary": "核销应付"})
            if pre_amt > 0: entries.append({"level1": AccountLevel1.PREPAYMENT, "cp_type": cp_type, "cp_id": cp_id, "debit": pre_amt, "summary": "计入预付"})
            entries.append(get_money_entry(cf.amount, is_income=False, summary=f"支付资金 ({cf.type})"))
    elif cf.type == CashFlowType.DEPOSIT:
        if is_income:
            entries.append(get_money_entry(cf.amount, is_income=True, summary="收到押金"))
            entries.append({"level1": AccountLevel1.DEPOSIT_PAYABLE, "cp_type": cp_type, "cp_id": cp_id, "credit": cf.amount, "summary": "押金入账"})
        else:
            entries.append({"level1": AccountLevel1.DEPOSIT_RECEIVABLE, "cp_type": cp_type, "cp_id": cp_id, "debit": cf.amount, "summary": "支付押金"})
            entries.append(get_money_entry(cf.amount, is_income=False, summary="支付押金"))
    elif cf.type == CashFlowType.RETURN_DEPOSIT:
        if is_income:
            entries.append(get_money_entry(cf.amount, is_income=True, summary="收回押金"))
            entries.append({"level1": AccountLevel1.DEPOSIT_RECEIVABLE, "cp_type": cp_type, "cp_id": cp_id, "credit": cf.amount, "summary": "收回押金冲减"})
        else:
            entries.append({"level1": AccountLevel1.DEPOSIT_PAYABLE, "cp_type": cp_type, "cp_id": cp_id, "debit": cf.amount, "summary": "退还押金"})
            entries.append(get_money_entry(cf.amount, is_income=False, summary="转账退押金"))
    elif cf.type == CashFlowType.PENALTY:
        if is_income:
            entries.append(get_money_entry(cf.amount, is_income=True, summary="收到罚金"))
            entries.append({"level1": AccountLevel1.NON_OP_REVENUE_PENALTY, "credit": cf.amount, "summary": "罚金收入"})
        else:
            entries.append({"level1": AccountLevel1.NON_OP_COST_PENALTY, "debit": cf.amount, "summary": "罚金支出"})
            entries.append(get_money_entry(cf.amount, is_income=False, summary="交纳罚金"))
    elif cf.type == CashFlowType.REFUND:
        if is_income:
            entries.append(get_money_entry(cf.amount, is_income=True, summary="收到退款"))
            entries.append({"level1": AccountLevel1.AP, "cp_type": cp_type, "cp_id": cp_id, "credit": cf.amount, "summary": "核销应付余额"})
        else:
            entries.append({"level1": AccountLevel1.AR, "cp_type": cp_type, "cp_id": cp_id, "debit": cf.amount, "summary": "支付货款使应收归零"})
            entries.append(get_money_entry(cf.amount, is_income=False, summary="转账退还货款"))
    elif cf.type == CashFlowType.OFFSET_IN:
        if is_income:
            entries.append(get_money_entry(cf.amount, is_income=True, summary="溢收录入"))
            entries.append({"level1": AccountLevel1.PRE_COLLECTION, "cp_type": cp_type, "cp_id": cp_id, "credit": cf.amount, "summary": "手动录入预收"})
        else:
            entries.append({"level1": AccountLevel1.PREPAYMENT, "cp_type": cp_type, "cp_id": cp_id, "debit": cf.amount, "summary": "手动录入预付"})
            entries.append(get_money_entry(cf.amount, is_income=False, summary="支付资金转入预付"))
    elif cf.type == CashFlowType.OFFSET_PAY:
        if is_income:
            entries.append({"level1": AccountLevel1.PRE_COLLECTION, "cp_type": cp_type, "cp_id": cp_id, "debit": cf.amount, "summary": "提取预收冲抵"})
            entries.append({"level1": AccountLevel1.AR, "cp_type": cp_type, "cp_id": cp_id, "credit": cf.amount, "summary": "冲抵核销应收"})
        else:
            entries.append({"level1": AccountLevel1.AP, "cp_type": cp_type, "cp_id": cp_id, "debit": cf.amount, "summary": "冲抵核销应付"})
            entries.append({"level1": AccountLevel1.PREPAYMENT, "cp_type": cp_type, "cp_id": cp_id, "credit": cf.amount, "summary": "扣减预付冲抵"})
    if entries:
        record_entries(session, voucher_no, vc.id if vc else None, "CashFlow", cash_flow_id, entries, cf.transaction_date)
        cf.finance_triggered = True

def save_voucher(data, filename):
    if not os.path.exists(VOUCHER_DIR): os.makedirs(VOUCHER_DIR)
    path = os.path.join(VOUCHER_DIR, f"{filename}.json")
    with open(path, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=2)

def update_report(voucher):
    report_path = os.path.join(REPORT_DIR, "report.json")
    report = {}
    if os.path.exists(report_path):
        try:
            with open(report_path, 'r', encoding='utf-8') as f: report = json.load(f)
        except: pass
    ts_str = voucher.get("timestamp")
    dt = datetime.fromisoformat(ts_str) if ts_str else datetime.now()
    month = dt.strftime("%Y-%m")
    if month not in report:
        report[month] = {
            "summary": {
                AccountLevel1.REVENUE: 0.0, AccountLevel1.COST: 0.0, AccountLevel1.EXPENSE: 0.0,
                "营业外净损益": 0.0, "现金净流量": 0.0, "经营性流入": 0.0, "借贷/注资流入": 0.0,
                "所有支出": 0.0, "月度净利润": 0.0
            },
            "vouchers": []
        }
    report[month]["vouchers"].append(voucher)
    s = report[month]["summary"]
    for entry in voucher.get("entries", []):
        acc_full = entry.get("account", ""); acc_l1 = acc_full.split(" - ")[0]
        debit, credit = float(entry.get("debit", 0.0)), float(entry.get("credit", 0.0))
        if acc_l1 in ACCOUNT_CONFIG:
            conf = ACCOUNT_CONFIG[acc_l1]
            if conf["category"] == "损益":
                if acc_l1 == AccountLevel1.REVENUE: s[AccountLevel1.REVENUE] += credit - debit
                if acc_l1 == AccountLevel1.COST: s[AccountLevel1.COST] += debit - credit
                if acc_l1 == AccountLevel1.EXPENSE: s[AccountLevel1.EXPENSE] += debit - credit
            if acc_l1 == AccountLevel1.CASH:
                s["现金净流量"] += debit - credit
                if debit > 0:
                    if voucher.get("ref_type") == "ExternalTransfer": s["借贷/注资流入"] += debit
                    else: s["经营性流入"] += debit
                elif credit > 0: s["所有支出"] += credit
            if acc_l1 in [AccountLevel1.NON_OP_REVENUE_PENALTY, AccountLevel1.NON_OP_COST_PENALTY]:
                val = credit if acc_l1 == AccountLevel1.NON_OP_REVENUE_PENALTY else -debit
                s["营业外净损益"] += val
    s["月度净利润"] = s[AccountLevel1.REVENUE] - s[AccountLevel1.COST] - s[AccountLevel1.EXPENSE] + s["营业外净损益"]
    if not os.path.exists(REPORT_DIR): os.makedirs(REPORT_DIR)
    with open(report_path, 'w', encoding='utf-8') as f: json.dump(report, f, ensure_ascii=False, indent=2)

def rebuild_report():
    session = get_session()
    try:
        journals = session.query(FinancialJournal).order_by(FinancialJournal.transaction_date.desc()).all()
        report = {}
        for j in journals:
            dt = j.transaction_date; month = dt.strftime("%Y-%m")
            if month not in report:
                report[month] = {
                    "summary": {
                        AccountLevel1.REVENUE: 0.0, AccountLevel1.COST: 0.0, AccountLevel1.EXPENSE: 0.0,
                        "营业外净损益": 0.0, "现金净流量": 0.0, "经营性流入": 0.0, "借贷/注资流入": 0.0, "所有支出": 0.0
                    },
                    "vouchers": {}
                }
            acc_name, cat = j.account.level1_name, j.account.category
            if cat == "损益":
                if acc_name == AccountLevel1.REVENUE: report[month]["summary"][AccountLevel1.REVENUE] += (j.credit - j.debit)
                elif acc_name == AccountLevel1.COST: report[month]["summary"][AccountLevel1.COST] += (j.debit - j.credit)
                elif acc_name == AccountLevel1.EXPENSE: report[month]["summary"][AccountLevel1.EXPENSE] += (j.debit - j.credit)
                elif acc_name in [AccountLevel1.NON_OP_REVENUE_PENALTY, AccountLevel1.NON_OP_COST_PENALTY]:
                    val = j.credit if acc_name == AccountLevel1.NON_OP_REVENUE_PENALTY else -j.debit
                    report[month]["summary"]["营业外净损益"] += val
            if acc_name == AccountLevel1.CASH:
                report[month]["summary"]["现金净流量"] += (j.debit - j.credit)
                if j.debit > 0:
                    if j.ref_type == "ExternalTransfer": report[month]["summary"]["借贷/注资流入"] += j.debit
                    else: report[month]["summary"]["经营性流入"] += j.debit
                elif j.credit > 0: report[month]["summary"]["所有支出"] += j.credit
            v_no = j.voucher_no
            if v_no not in report[month]["vouchers"]:
                report[month]["vouchers"][v_no] = {"voucher_no": v_no, "ref_type": j.ref_type, "timestamp": dt.isoformat(), "entries": []}
            report[month]["vouchers"][v_no]["entries"].append({
                "account": f"{acc_name}{' - ' + j.account.level2_name if j.account.level2_name else ''}",
                "debit": j.debit, "credit": j.credit, "summary": j.summary
            })
        for month in report:
            s = report[month]["summary"]
            s["月度净利润"] = s[AccountLevel1.REVENUE] - s[AccountLevel1.COST] - s[AccountLevel1.EXPENSE] + s["营业外净损益"]
            report[month]["vouchers"] = list(report[month]["vouchers"].values())
        if not os.path.exists(REPORT_DIR): os.makedirs(REPORT_DIR)
        with open(os.path.join(REPORT_DIR, "report.json"), 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
    finally: session.close()
