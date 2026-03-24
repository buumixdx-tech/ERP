package com.shanyin.erp.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "logistics")
data class LogisticsEntity(
    @PrimaryKey(autoGenerate = true) val localId: Long = 0,
    val virtualContractId: Long,
    val status: String,
    val createdAt: Long = System.currentTimeMillis()
)

@Entity(tableName = "express_orders")
data class ExpressOrderEntity(
    @PrimaryKey(autoGenerate = true) val localId: Long = 0,
    val logisticsId: Long,
    val trackingNo: String,
    val status: String
)

@Entity(tableName = "cash_flows")
data class CashFlowEntity(
    @PrimaryKey(autoGenerate = true) val localId: Long = 0,
    val virtualContractId: Long?,
    val type: String, // PREPAYMENT, FULFILLMENT, REFUND, RETURN_DEPOSIT, DEPOSIT, OFFSET_PAY
    val amount: Double,
    val payerAccountId: Long?,
    val payeeAccountId: Long?,
    val financeTriggered: Boolean = false,
    val createdAt: Long = System.currentTimeMillis()
)

@Entity(tableName = "finance_accounts")
data class FinanceAccountEntity(
    @PrimaryKey(autoGenerate = true) val localId: Long = 0,
    val level1Name: String, // AR, AP, PREPAYMENT, PRE_COLLECTION, etc.
    val counterpartType: String?, // CUSTOMER, SUPPLIER, OURSELVES
    val counterpartId: Long?
)

@Entity(tableName = "financial_journals")
data class FinancialJournalEntity(
    @PrimaryKey(autoGenerate = true) val localId: Long = 0,
    val accountId: Long,
    val debit: Double,
    val credit: Double,
    val refVcId: Long?,
    val refType: String?, // Logistics, CashFlow
    val createdAt: Long = System.currentTimeMillis()
)

@Entity(tableName = "system_events")
data class SystemEventEntity(
    @PrimaryKey(autoGenerate = true) val localId: Long = 0,
    val eventType: String,
    val aggregateType: String,
    val aggregateId: Long,
    val payloadJson: String?,
    val createdAt: Long = System.currentTimeMillis()
)

@Entity(tableName = "equipment_inventory")
data class EquipmentInventoryEntity(
    @PrimaryKey(autoGenerate = true) val localId: Long = 0,
    val skuId: Long,
    val sn: String,
    val pointId: Long?,
    val operationalStatus: String, // STOCK, OPERATING, SCRAP
    val depositAmount: Double,
    val virtualContractId: Long?
)

@Entity(tableName = "material_inventory")
data class MaterialInventoryEntity(
    @PrimaryKey(autoGenerate = true) val localId: Long = 0,
    val skuId: Long,
    val stockDistributionJson: String?, // Map<String, Double> as JSON
    val averagePrice: Double
)

object SystemAggregateType {
    const val LOGISTICS = "logistics"
    const val VIRTUAL_CONTRACT = "virtual_contract"
}

object SystemEventType {
    const val LOGISTICS_STATUS_CHANGED = "logistics_status_changed"
    const val VC_GOODS_CLEARED = "vc_goods_cleared"
    const val VC_DEPOSIT_CLEARED = "vc_deposit_cleared"
}
