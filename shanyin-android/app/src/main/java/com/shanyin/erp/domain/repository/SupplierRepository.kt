package com.shanyin.erp.domain.repository

import com.shanyin.erp.data.local.entity.SupplierEntity
import kotlinx.coroutines.flow.Flow

interface SupplierRepository {
    fun getSuppliers(): Flow<List<SupplierEntity>>
    suspend fun insertSupplier(name: String, category: String?, address: String?)
}
