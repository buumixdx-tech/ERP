# CLAUDE.md

本文档为 Claude Code (claude.ai/code) 提供代码库操作指引。
所有读取markdown和db的操作都要基于UTF8编码


## 项目简介

**闪饮 ERP** — 面向饮品设备运营企业的 ERP 系统，管理设备/物料的采购、供应、退货全链路，配套物流跟踪、复式记账资金流、时间规则引擎和实时库存。

- **桌面端**（Python）：Streamlit + SQLAlchemy + SQLite，Action 模式，详见 `Docs/desktop_docs/README.md`
- **Android 端**（Kotlin）：Jetpack Compose + Room + Hilt，离线优先，详见 `Docs/Android_docs/README.md`

详细文档索引：
- 桌面端完整文档 → `Docs/desktop_docs/README.md`
- Android 端完整文档 → `Docs/Android_docs/README.md`
- Action API 手册 → `Docs/desktop_docs/API/api_manual.md`

## 仓库结构

```
ERP/
├── Docs/
│   ├── desktop_docs/           # 桌面端完整文档（含 README、database、workflow、API、models/）
│   └── Android_docs/          # Android 端完整文档（含 README、database、workflow、models/）
├── desktop-version/           # 桌面端主代码库（Python）
└── shanyin-android-v2/        # Android 应用（Kotlin）
```

---

## 桌面端 Python ERP（`desktop-version/`）

### 运行与测试
```bash
cd desktop-version
pip install -r requirements.txt
streamlit run main.py --server.port 8501    # 启动应用
python run_api.py                            # 启动 API
pytest tests/ -v                             # 所有测试
pytest tests/actions/test_vc_actions.py -v   # 单文件
pytest tests/ -k "finance" -v                # 按关键词过滤
```

### 架构

```
models.py                        # SQLAlchemy ORM（主数据/协议/VC/物流/财务/库存/规则）
logic/
├── vc/                         # VC 创建/修改/删除/查询（5种 VC 类型）
├── business/                    # 业务阶段推进 + 自动生成时间规则和合同
├── supply_chain/               # 供应链协议及定价绑定
├── logistics/                   # 物流创建 + 入库确认（含库存联动和财务凭证）
├── finance/
│   ├── engine.py               # 复式记账引擎（process_cash_flow_finance / process_logistics_finance）
│   ├── actions.py              # 资金流录入、内转划拨、外部出金
│   └── queries.py              # UI 查询（科目余额、凭证历史、资金划拨历史）
├── deposit.py                  # 押金重算：按 SKU × 运营设备数重算 should_receive
├── offset_manager.py           # 预收/预付池核销到 VC
├── state_machine.py            # VC 三状态机（status / subject / cash）
├── services.py                 # 跨模块辅助（收款进度/退货可退量/对手方信息/财务上下文）
├── time_rules/                 # 规则引擎：rule_manager + 三层继承链 + 告警等级
├── events/                     # 事件派发（emit → dispatch → listener 链）
├── inventory.py                 # 设备 SN + 物料库存变动
└── file_mgmt.py               # Excel 导入导出 / 合同附件
ui/                             # Streamlit 页面
api/routers/                    # FastAPI 路由
```

### 核心设计模式

**Action 模式：** 所有写操作通过 `logic/<domain>/actions.py` 函数完成，包裹在事务中，自动触发状态机和事件。

**VC elements（v5.0）：** `elements` JSON 字段含 `shipping_point_id`、`receiving_point_id`、`sku_id`、`qty`、`price`、`deposit`、`subtotal`。

**复式记账：** `process_cash_flow_finance()` 和 `process_logistics_finance()` 生成 `FinancialJournal` 双录，押金按 SKU 运营设备数重算 `should_receive`。

### Action API 参考

**主数据**（`logic/master/`）：
`create_customer_action` / `update_customers_action` / `delete_customers_action` / `create_supplier_action` / `update_suppliers_action` / `delete_suppliers_action` / `create_point_action` / `update_points_action` / `delete_points_action` / `create_sku_action` / `update_skus_action` / `delete_skus_action` / `create_partner_action` / `update_partners_action` / `delete_partners_action` / `create_bank_account_action` / `update_bank_accounts_action` / `delete_bank_accounts_action` / `get_system_constants`

**业务流**（`logic/business/`）：
`create_business_action` / `update_business_status_action` / `delete_business_action` / `advance_business_stage_action` / `get_business_list` / `get_business_detail` / `get_businesses_for_execution`

**供应链**（`logic/supply_chain/`）：
`create_supply_chain_action` / `delete_supply_chain_action` / `get_supply_chains` / `get_supply_chain_detail`

**虚拟合同**（`logic/vc/`）：
`create_procurement_vc_action` / `create_material_supply_vc_action` / `create_stock_procurement_vc_action` / `create_mat_procurement_vc_action` / `create_return_vc_action` / `update_vc_action` / `delete_vc_action` / `create_inventory_allocation_action` / `get_vc_list` / `get_vc_detail` / `get_time_rules_for_vc` / `get_returnable_vcs` / `get_vc_status_logs` / `get_vc_cash_flows`

**物流**（`logic/logistics/`）：
`create_logistics_plan_action` / `confirm_inbound_action` / `update_express_order_action` / `update_express_order_status_action` / `bulk_progress_express_orders_action` / `get_logistics_list` / `get_logistics_detail` / `get_logistics_dashboard_summary`

**财务**（`logic/finance/`）：
`create_cash_flow_action` / `internal_transfer_action` / `external_fund_action` / `create_bank_account_action` / `update_bank_accounts_action` / `get_cash_flow_list` / `get_bank_accounts` / `get_dashboard_stats` / `get_account_list_for_ui` / `get_journal_entries_for_ui` / `get_fund_operation_history_for_ui` / `finance_module` / `record_entries`

**押金与核销**：`deposit_module` / `process_cf_deposit` / `process_vc_deposit` / `apply_offset_to_vc`

**时间规则**（`logic/time_rules/`）：
`save_rule_action` / `delete_rule_action` / `persist_draft_rules_action` / `get_time_rule_list`

**辅助**（`logic/services.py`）：
`calculate_cashflow_progress` / `get_returnable_items` / `format_vc_items_for_display` / `get_counterpart_info` / `get_suggested_cashflow_parties` / `get_account_balance` / `get_logistics_finance_context` / `get_cashflow_finance_context`

**文件与库存**：`generate_master_data_excel` / `process_master_data_excel` / `save_contract_files` / `get_contract_files` / `get_equipment_inventory` / `get_material_inventory` / `get_inventory_stats` / `validate_inventory_availability`

---

## Android 应用（`shanyin-android-v2/`）

### 构建
```bash
cd shanyin-android-v2
./gradlew assembleDebug   # 构建
./gradlew test            # 测试
```

### 架构（整洁架构）

```
app/src/main/java/com/shanyin/erp/
├── domain/               # 纯业务逻辑（无 Android 依赖）
│   ├── model/           # 领域模型（不含 android.*）
│   ├── repository/      # Repository 接口
│   └── usecase/         # UseCase（13+ 个）
│       ├── VirtualContractStateMachineUseCase.kt   # 对标 state_machine.py + deposit.py
│       ├── ProcessCashFlowFinanceUseCase.kt       # 对标 process_cash_flow_finance
│       ├── ProcessLogisticsFinanceUseCase.kt       # 对标 process_logistics_finance
│       ├── OffsetPoolUseCase.kt + ApplyOffsetToVcUseCase.kt
│       ├── AccountsPayableReceivableUseCases.kt
│       └── finance/（InternalTransfer / ExternalFund / Statements 等）
├── data/
│   ├── local/           # Room DB（23 Entity + 23 DAO）
│   └── repository/      # Repository 实现
└── ui/                  # Compose UI（11 个屏幕 + ViewModel）
```

### 资金流对齐说明

Android 已实现桌面端约 85-90% 的资金流逻辑。已知差异：
1. Dashboard 月度收入用 CashFlow 金额求和，未从 Journal 贷方发生额计算
2. 缺少 `get_fund_operation_history` 等效查询
3. 状态机中 `OFFSET_PAY` vs `OFFSET_OUTFLOW` 类型名不匹配

---

## 开发工作流

- **桌面端优先**：先在 `desktop-version/` 实现和测试业务逻辑，再移植 Android
- **移植到 Android**：逐行对比 `logic/` 文件与 `usecase/` 目录，确保状态机/押金/核销逻辑一致
- **数据库**：桌面端 SQLite 在 `desktop-version/data/*.db`，严禁提交 `*.db`、`*-wal`、`*-shm`
- **编码**：所有数据库操作（SQLAlchemy/SQLite）和 Excel 导入导出均须使用 UTF-8 编码，中文数据才能正确存储和读取
- **财务凭证**：`data/finance/finance-voucher/*.json` 已在 `.gitignore` 中忽略

---

## 关键文档路径

| 文档 | 路径 |
|------|------|
| 桌面端完整索引 | `Docs/desktop_docs/README.md` |
| Android 完整索引 | `Docs/Android_docs/README.md` |
| Action API 手册 | `Docs/desktop_docs/API/api_manual.md` |
| 数据库结构 | `Docs/desktop_docs/database.md` / `Docs/Android_docs/database.md` |
| 业务流程 | `Docs/desktop_docs/workflow.md` |
