package com.shanyin.erp.data.local.dao

import androidx.room.*
import com.shanyin.erp.data.local.entity.VirtualContractEntity
import com.shanyin.erp.data.local.entity.VirtualContractItemEntity
import com.shanyin.erp.data.local.entity.VirtualContractWithItems
import kotlinx.coroutines.flow.Flow

@Dao
interface VirtualContractDao {

    @Transaction
    @Query("SELECT * FROM virtual_contracts ORDER BY createdAt DESC")
    fun getAllContractsWithItemsFlow(): Flow<List<VirtualContractWithItems>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertContract(contract: VirtualContractEntity): Long

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertContractItems(items: List<VirtualContractItemEntity>)

    @Update
    suspend fun updateContract(contract: VirtualContractEntity)

    // Helper to insert a contract and its items atomically
    @Transaction
    suspend fun insertContractWithItems(contract: VirtualContractEntity, items: List<VirtualContractItemEntity>): Long {
        val contractId = insertContract(contract)
        val itemsWithContractId = items.map { it.copy(contractLocalId = contractId) }
        insertContractItems(itemsWithContractId)
        return contractId
    }
}
