package com.shanyin.erp.data.repository

import com.shanyin.erp.data.local.dao.SKUDao
import com.shanyin.erp.data.local.entity.SKUEntity
import com.shanyin.erp.domain.repository.SKURepository
import kotlinx.coroutines.flow.Flow
import javax.inject.Inject

class SKURepositoryImpl @Inject constructor(
    private val dao: SKUDao
) : SKURepository {

    override fun getSKUs(): Flow<List<SKUEntity>> {
        return dao.getAllSKUsFlow()
    }

    override suspend fun insertSKU(name: String, typeLevel1: String?, model: String?) {
        val entity = SKUEntity(
            name = name,
            typeLevel1 = typeLevel1,
            model = model,
            supplierId = null,
            typeLevel2 = null,
            description = null,
            paramsJson = null
        )
        dao.insert(entity)
    }
}
