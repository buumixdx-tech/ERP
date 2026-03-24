import streamlit as st
from models import get_session, ChannelCustomer, Point, Supplier, SKU, ExternalPartner, BankAccount
import pandas as pd
import streamlit_antd_components as sac
from logic.constants import PointType, SupplierCategory, SKUType, ExternalPartnerType, AccountOwnerType, BankInfoKey
from logic.master import (
    create_customer_action, update_customers_action,
    create_point_action, update_points_action,
    create_supplier_action, update_suppliers_action,
    create_sku_action, update_skus_action,
    create_partner_action, update_partners_action,
    CustomerSchema, PointSchema, SupplierSchema, SKUSchema, PartnerSchema
)
from logic.finance import (
    create_bank_account_action, update_bank_accounts_action,
    CreateBankAccountSchema, UpdateBankAccountSchema
)
from logic.master.queries import (
    get_customers_for_ui, get_suppliers_for_ui, get_points_for_ui,
    get_skus_for_ui, get_partners_for_ui, get_bank_accounts_for_ui
)
from logic.file_mgmt import generate_master_data_excel, process_master_data_excel
from datetime import datetime

def show_entry_page():
    st.markdown("<h1 style='font-size: 24px;'><i class='bi bi-clipboard-data'></i> 信息录入与维护</h1>", unsafe_allow_html=True)
    st.info("提示：下方表格支持直接双击修改导出数据。修改后请点击下方的‘保存修改’按钮。")
    sel_tab = sac.tabs([
        sac.TabsItem('渠道客户', icon='people'),
        sac.TabsItem('点位', icon='geo-alt'),
        sac.TabsItem('供应商', icon='shop'),
        sac.TabsItem('SKU', icon='box-seam'),
        sac.TabsItem('外部合作方', icon='briefcase'),
        sac.TabsItem('银行账户', icon='bank'),
        sac.TabsItem('批量导入导出', icon='cloud-arrow-up'),
    ], align='center', variant='outline', key='entry_tabs')
    
    session = get_session()
    
    if sel_tab == '渠道客户':
        st.markdown("### <i class='bi bi-people'></i> 渠道客户维护", unsafe_allow_html=True)
        with st.expander("新增客户"):
            with st.form("customer_form"):
                name = st.text_input("客户名称")
                info = st.text_area("整体信息描述")
                submit = st.form_submit_button("提交保存")
                if submit and name:
                    result = create_customer_action(session, CustomerSchema(name=name, info=info))
                    if result.success:
                        st.success(result.message)
                        st.rerun()
                    else:
                        st.error(result.error)

        data = get_customers_for_ui()
        if data:
            df = pd.DataFrame([{"ID": c["id"], "名称": c["name"], "信息": c["info"]} for c in data])
            edited_df = st.data_editor(df, use_container_width=True, disabled=["ID"], key="edit_cust", hide_index=True)
            if st.button("保存客户信息修改"):
                payloads = [CustomerSchema(id=int(row["ID"]), name=row["名称"], info=row["信息"]) for _, row in edited_df.iterrows()]
                result = update_customers_action(session, payloads)
                if result.success:
                    st.success(result.message)
                    st.rerun()
                else:
                    st.error(result.error)

    elif sel_tab == '点位':
        st.markdown("### <i class='bi bi-geo-alt'></i> 点位维护", unsafe_allow_html=True)
        customers = get_customers_for_ui()
        suppliers = get_suppliers_for_ui()
        
        owner_options = {"[公司] 闪饮自身": (AccountOwnerType.OURSELVES, None)}
        for c in customers: owner_options[f"[客户] {c['name']}"] = (AccountOwnerType.CUSTOMER, c['id'])
        for s in suppliers: owner_options[f"[供应商] {s['name']}"] = (AccountOwnerType.SUPPLIER, s['id'])

        with st.expander("新增点位"):
            with st.form("point_form"):
                selection = st.selectbox("归属主体", list(owner_options.keys()))
                name = st.text_input("点位名称")
                addr = st.text_input("详细地址")
                p_type = st.selectbox("类型", PointType.ALL_TYPES)
                recv_addr = st.text_input("收货地址(通常同详细地址)", value=addr)
                
                if st.form_submit_button("保存点位"):
                    otype, oid = owner_options[selection]
                    payload = PointSchema(
                        name=name, type=p_type, address=addr, receiving_address=recv_addr or addr,
                        customer_id=oid if otype == AccountOwnerType.CUSTOMER else None,
                        supplier_id=oid if otype == AccountOwnerType.SUPPLIER else None
                    )
                    result = create_point_action(session, payload)
                    if result.success:
                        st.success(result.message)
                        st.rerun()
                    else:
                        st.error(result.error)

        data = get_points_for_ui()
        if data:
            df = pd.DataFrame([
                {"ID": p["id"], "名称": p["name"], "归属主体": p["owner_label"], "类型": p["type"], "地址": p["address"], "收货地址": p["receiving_address"]} 
                for p in data
            ])
            edited_df = st.data_editor(df, use_container_width=True, disabled=["ID"], key="edit_point", hide_index=True, column_config={
                "类型": st.column_config.SelectboxColumn("类型", options=PointType.ALL_TYPES),
                "归属主体": st.column_config.SelectboxColumn("归属主体", options=list(owner_options.keys()))
            })
            if st.button("保存点位修改"):
                payloads = []
                for _, row in edited_df.iterrows():
                    otype, oid = owner_options[row["归属主体"]]
                    payloads.append(PointSchema(
                        id=int(row["ID"]), name=row["名称"], type=row["类型"], address=row["地址"], receiving_address=row["收货地址"],
                        customer_id=oid if otype == AccountOwnerType.CUSTOMER else None,
                        supplier_id=oid if otype == AccountOwnerType.SUPPLIER else None
                    ))
                result = update_points_action(session, payloads)
                if result.success:
                    st.success(result.message)
                    st.rerun()
                else: st.error(result.error)

    elif sel_tab == '供应商':
        st.markdown("### <i class='bi bi-shop'></i> 供应商维护", unsafe_allow_html=True)
        with st.expander("新增供应商"):
            with st.form("supplier_form"):
                name = st.text_input("供应商名称")
                cat = st.selectbox("供应类别", SupplierCategory.ALL_TYPES)
                addr = st.text_input("地址信息")
                if st.form_submit_button("保存供应商"):
                    result = create_supplier_action(session, SupplierSchema(name=name, category=cat, address=addr))
                    if result.success: st.rerun()
                    else: st.error(result.error)

        data = get_suppliers_for_ui()
        if data:
            df = pd.DataFrame([{"ID": s["id"], "名称": s["name"], "类别": s["category"], "地址": s["address"]} for s in data])
            edited_df = st.data_editor(df, use_container_width=True, disabled=["ID"], key="edit_supp", hide_index=True, column_config={
                "类别": st.column_config.SelectboxColumn("类别", options=SupplierCategory.ALL_TYPES)
            })
            if st.button("保存供应商修改"):
                payloads = [SupplierSchema(id=int(row["ID"]), name=row["名称"], category=row["类别"], address=row["地址"]) for _, row in edited_df.iterrows()]
                result = update_suppliers_action(session, payloads)
                if result.success: st.rerun()
                else: st.error(result.error)

    elif sel_tab == 'SKU':
        st.markdown("### <i class='bi bi-box-seam'></i> SKU维护", unsafe_allow_html=True)
        suppliers = get_suppliers_for_ui()
        supp_options = {s["name"]: s["id"] for s in suppliers}
        with st.expander("新增SKU"):
            with st.form("sku_form"):
                s_name = st.selectbox("所属供应商", list(supp_options.keys()))
                name = st.text_input("SKU名称")
                t1 = st.selectbox("一级分类", SKUType.ALL_TYPES)
                model = st.text_input("型号")
                if st.form_submit_button("保存SKU"):
                    result = create_sku_action(session, SKUSchema(supplier_id=supp_options[s_name], name=name, type_level1=t1, model=model))
                    if result.success: st.rerun()
                    else: st.error(result.error)

        data = get_skus_for_ui()
        if data:
            df = pd.DataFrame([{"ID": k["id"], "名称": k["name"], "供应商": k["supplier_name"], "一级分类": k["type_level1"], "型号": k["model"]} for k in data])
            edited_df = st.data_editor(df, use_container_width=True, disabled=["ID"], key="edit_sku", hide_index=True, column_config={
                "供应商": st.column_config.SelectboxColumn("供应商", options=list(supp_options.keys())),
                "一级分类": st.column_config.SelectboxColumn("一级分类", options=SKUType.ALL_TYPES)
            })
            if st.button("保存SKU修改"):
                payloads = [SKUSchema(id=int(row["ID"]), name=row["名称"], supplier_id=supp_options.get(row["供应商"]), type_level1=row["一级分类"], model=row["型号"]) for _, row in edited_df.iterrows()]
                result = update_skus_action(session, payloads)
                if result.success: st.rerun()
                else: st.error(result.error)

    elif sel_tab == '外部合作方':
        st.markdown("### <i class='bi bi-briefcase'></i> 外部合作方维护", unsafe_allow_html=True)
        with st.expander("新增合作方"):
            with st.form("ext_p_form"):
                name = st.text_input("名称")
                p_type = st.selectbox("类型", ExternalPartnerType.ALL_TYPES)
                if st.form_submit_button("保存合作方"):
                    result = create_partner_action(session, PartnerSchema(name=name, type=p_type))
                    if result.success: st.rerun()
                    else: st.error(result.error)

        data = get_partners_for_ui()
        if data:
            df = pd.DataFrame([{"ID": p["id"], "名称": p["name"], "类型": p["type"]} for p in data])
            edited_df = st.data_editor(df, use_container_width=True, disabled=["ID"], key="edit_ext", hide_index=True, column_config={"类型": st.column_config.SelectboxColumn("类型", options=ExternalPartnerType.ALL_TYPES)})
            if st.button("保存修改", key="save_ext"):
                payloads = [PartnerSchema(id=int(row["ID"]), name=row["名称"], type=row["类型"]) for _, row in edited_df.iterrows()]
                result = update_partners_action(session, payloads)
                if result.success: st.rerun()
                else: st.error(result.error)
                
    elif sel_tab == '银行账户':
        st.markdown("### <i class='bi bi-bank'></i> 银行账户维护", unsafe_allow_html=True)
        customers = get_customers_for_ui()
        suppliers = get_suppliers_for_ui()
        partners = get_partners_for_ui()
        
        # Build owner options dict similarly to points
        owner_options = {"[公司] 闪饮自身": (AccountOwnerType.OURSELVES, None)}
        for c in customers: owner_options[f"[客户] {c['name']}"] = (AccountOwnerType.CUSTOMER, c["id"])
        for s in suppliers: owner_options[f"[供应商] {s['name']}"] = (AccountOwnerType.SUPPLIER, s["id"])
        for p in partners: owner_options[f"[合作方] {p['name']}"] = (AccountOwnerType.OTHER, p["id"])
        
        with st.expander("新增银行账户"):
            with st.form("bank_acc_form"):
                selection = st.selectbox("归属方", list(owner_options.keys()))
                acc_name = st.text_input("开户名称", placeholder="例如：闪饮科技有限公司")
                bank_name = st.text_input("银行名称", placeholder="例如：招商银行北京分行")
                acc_num = st.text_input("银行账号", placeholder="例如：622202...")
                is_default = st.checkbox("设为默认账户", value=True)
                
                if st.form_submit_button("保存账户"):
                    otype, oid = owner_options[selection]
                    
                    payload = CreateBankAccountSchema(
                        owner_type=otype,
                        owner_id=oid,
                        account_info={BankInfoKey.HOLDER_NAME: acc_name, BankInfoKey.BANK_NAME: bank_name, BankInfoKey.ACCOUNT_NO: acc_num},
                        is_default=is_default
                    )
                    
                    result = create_bank_account_action(session, payload)
                    if result.success:
                        st.success(result.message)
                        st.rerun()
                    else:
                        st.error(result.error)

        data = get_bank_accounts_for_ui()
        if data:
            df = pd.DataFrame([
                {
                    "ID": acc["id"], 
                    "归属方": acc["owner_label"], 
                    "开户名称": acc["holder_name"],
                    "银行名称": acc["bank_name"],
                    "银行账号": acc["account_no"],
                    "默认": acc["is_default"]
                } for acc in data
            ])
            edited_df = st.data_editor(
                df, use_container_width=True, disabled=["ID", "归属方"], key="edit_bank", hide_index=True
            )
            
            if st.button("保存账户修改", key="save_bank"):
                payloads = []
                for _, row in edited_df.iterrows():
                    acc_id = int(row["ID"])
                    account_info = {
                        BankInfoKey.HOLDER_NAME: row["开户名称"],
                        BankInfoKey.BANK_NAME: row["银行名称"],
                        BankInfoKey.ACCOUNT_NO: row["银行账号"]
                    }
                    # Find the account to get owner info
                    acc_data = next((a for a in data if a["id"] == acc_id), None)
                    if acc_data:
                        payloads.append(UpdateBankAccountSchema(
                            id=acc_id,
                            owner_type=acc_data["owner_type"],
                            owner_id=acc_data["owner_id"],
                            account_info=account_info,
                            is_default=bool(row["默认"])
                        ))
                result = update_bank_accounts_action(session, payloads)
                if result.success: st.rerun()
                else: st.error(result.error)

    elif sel_tab == '批量导入导出':
        st.markdown("### <i class='bi bi-cloud-arrow-up'></i> 基础数据批量导入与导出", unsafe_allow_html=True)
        st.info("💡 强烈建议在导入前，先下载最新模板提取云端最新数据和关系。")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("#### 第一步：导出数据模板")
            st.markdown("模板内包含了最新的下拉框验证数据。你可以直接在模板上修改或新增数据。")
            
            with st.spinner("正在生成最新导出文件..."):
                excel_bytes = generate_master_data_excel(session)
                
            current_time_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_filename = f"master_data_{current_time_str}.xlsx"
            
            st.download_button(
                label="📥 下载最新主数据Excel",
                data=excel_bytes,
                file_name=export_filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                help="下载包含数据库内部ID与下拉联动的安全模板"
            )
            
        with col2:
            st.markdown("#### 第二步：上传更新文件")
            st.markdown("强烈建议谨慎使用最后一列的 `[操作指令]` 标记删除。")
            uploaded_file = st.file_uploader("只接受生成的模板格式Excel", type=["xlsx", "xls"])
            
            if uploaded_file is not None:
                if st.button("🚀 确认上传并覆盖入库", type="primary"):
                    with st.spinner("系统正在进行数据关系预检与入库，请稍候..."):
                        # Read bytes from streamlit UploadedFile object
                        file_bytes = uploaded_file.getvalue()
                        report = process_master_data_excel(session, file_bytes)
                        
                        st.divider()
                        st.markdown("### 📊 导入处理报告")
                        if report["success"]:
                            st.success("✅ 数据校验通过，写入执行成功！")
                        else:
                            st.error("❌ 处理过程中遇到阻断性错误。部分或全部数据未保存。")
                            
                        # Display Stats
                        s = report["stats"]
                        st.info(f"**处理统计**: 新增 **{s['新增']}** 条 | 更新 **{s['更新']}** 条 | 成功删除 **{s['删除']}** 条")
                        
                        # Display specific row/relation errors if any
                        if report["logs"]:
                            for log in report["logs"]:
                                if log.startswith("❌"): st.error(log)
                                elif log.startswith("⚠️"): st.warning(log)
                                else: st.text(log)
                                
                        if report["success"] and sum(s.values()) > 0:
                            # Re-generate the state if something successfully changed
                            if st.button("刷新页面加载最新数据"):
                                st.rerun()

    session.close()
