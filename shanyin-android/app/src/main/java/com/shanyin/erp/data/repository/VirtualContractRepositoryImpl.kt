package com.shanyin.erp.data.repository

import com.shanyin.erp.data.local.dao.VirtualContractDao
import com.shanyin.erp.data.local.entity.SyncStatus
import com.shanyin.erp.data.local.entity.VirtualContractEntity
import com.shanyin.erp.data.local.entity.VirtualContractItemEntity
import com.shanyin.erp.data.local.entity.VirtualContractWithItems
import com.shanyin.erp.domain.repository.VirtualContractRepository
import kotlinx.coroutines.flow.Flow
import javax.inject.Inject

class VirtualContractRepositoryImpl @Inject constructor(
    private val dao: VirtualContractDao
) : VirtualContractRepository {

    override fun getAllContractsFlow(): Flow<List<VirtualContractWithItems>> {
        return dao.getAllContractsWithItemsFlow()
    }

    override suspend fun createDraftContract(
        customerLocalId: Long,
        contractNo: String,
        items: List<VirtualContractItemEntity>
    ): Long {
        val totalAmount = items.sumOf { it.totalPrice }
        
        val newContract = VirtualContractEntity(
            customerLocalId = customerLocalId,
            contractNo = contractNo,
            status = "DRAFT",
            totalAmount = totalAmount,
            syncStatus = SyncStatus.PENDING_INSERT // Flags to SyncEngine to upload later
        )
        
        return dao.insertContractWithItems(newContract, items)
    }
}
