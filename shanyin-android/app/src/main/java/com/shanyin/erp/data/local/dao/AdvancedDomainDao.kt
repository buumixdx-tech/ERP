package com.shanyin.erp.data.local.dao

import androidx.room.*
import com.shanyin.erp.data.local.entity.*
import kotlinx.coroutines.flow.Flow

// Using a unified DAO for complex Transaction/Cross-table operations in UseCases
@Dao
interface AdvancedDomainDao {

    // Logistics & Express
    @Insert
    suspend fun insertLogistics(logistics: LogisticsEntity): Long
    
    @Update
    suspend fun updateLogistics(logistics: LogisticsEntity)
    
    @Query("SELECT * FROM logistics WHERE virtualContractId = :vcId LIMIT 1")
    suspend fun getLogisticsByVcId(vcId: Long): LogisticsEntity?

    @Query("SELECT * FROM logistics WHERE localId = :id")
    suspend fun getLogisticsById(id: Long): LogisticsEntity?

    @Query("SELECT * FROM express_orders WHERE logisticsId = :logisticsId")
    suspend fun getExpressOrdersByLogisticsId(logisticsId: Long): List<ExpressOrderEntity>

    // CashFlow
    @Insert
    suspend fun insertCashFlow(cashFlow: CashFlowEntity): Long

    @Query("SELECT * FROM cash_flows WHERE virtualContractId = :vcId")
    suspend fun getCashFlowsByVcId(vcId: Long): List<CashFlowEntity>
    
    @Query("SELECT * FROM cash_flows WHERE localId = :id")
    suspend fun getCashFlowById(id: Long): CashFlowEntity?

    // Finance Accounts and Ledgers
    @Insert
    suspend fun insertFinanceAccount(account: FinanceAccountEntity): Long
    
    @Query("SELECT * FROM finance_accounts WHERE level1Name = :lvl1 AND counterpartType = :cpType AND counterpartId = :cpId LIMIT 1")
    suspend fun getFinanceAccount(lvl1: String, cpType: String?, cpId: Long?): FinanceAccountEntity?

    @Insert
    suspend fun insertJournal(journal: FinancialJournalEntity): Long
    
    @Query("SELECT SUM(debit) as d, SUM(credit) as c FROM financial_journals WHERE accountId = :accountId")
    suspend fun getAccountBalanceSums(accountId: Long): AccountSums?

    @Query("SELECT * FROM financial_journals WHERE refVcId = :vcId AND refType = :refType LIMIT 1")
    suspend fun getJournalByRef(vcId: Long, refType: String): FinancialJournalEntity?

    // Inventory
    @Query("SELECT * FROM equipment_inventory WHERE virtualContractId = :vcId AND operationalStatus = :status")
    suspend fun getEquipmentsByVcAndStatus(vcId: Long, status: String): List<EquipmentInventoryEntity>
    
    @Query("SELECT * FROM material_inventory WHERE skuId = :skuId LIMIT 1")
    suspend fun getMaterialInventoryBySkuId(skuId: Long): MaterialInventoryEntity?

    // System Events
    @Insert
    suspend fun insertSystemEvent(event: SystemEventEntity): Long
    
    @Query("SELECT * FROM system_events WHERE eventType = :type AND aggregateId = :aggregateId LIMIT 1")
    suspend fun getSystemEvent(type: String, aggregateId: Long): SystemEventEntity?
}

data class AccountSums(
    val d: Double?,
    val c: Double?
)
