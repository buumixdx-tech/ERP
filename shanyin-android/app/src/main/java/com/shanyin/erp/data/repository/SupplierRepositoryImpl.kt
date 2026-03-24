package com.shanyin.erp.data.repository

import com.shanyin.erp.data.local.dao.SupplierDao
import com.shanyin.erp.data.local.entity.SupplierEntity
import com.shanyin.erp.domain.repository.SupplierRepository
import kotlinx.coroutines.flow.Flow
import javax.inject.Inject

class SupplierRepositoryImpl @Inject constructor(
    private val dao: SupplierDao
) : SupplierRepository {

    override fun getSuppliers(): Flow<List<SupplierEntity>> {
        return dao.getAllSuppliersFlow()
    }

    override suspend fun insertSupplier(name: String, category: String?, address: String?) {
        val entity = SupplierEntity(
            name = name,
            category = category,
            address = address,
            qualifications = null,
            info = null
        )
        dao.insert(entity)
    }
}
