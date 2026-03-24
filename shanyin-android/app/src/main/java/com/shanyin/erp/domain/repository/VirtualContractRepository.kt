package com.shanyin.erp.domain.repository

import com.shanyin.erp.data.local.entity.VirtualContractItemEntity
import com.shanyin.erp.data.local.entity.VirtualContractWithItems
import kotlinx.coroutines.flow.Flow

interface VirtualContractRepository {
    fun getAllContractsFlow(): Flow<List<VirtualContractWithItems>>
    
    /**
     * Creates a new Virtual Contract in DRAFT state locally.
     * Items must not specify contractLocalId as it will be assigned.
     */
    suspend fun createDraftContract(
        customerLocalId: Long,
        contractNo: String,
        items: List<VirtualContractItemEntity>
    ): Long
}
