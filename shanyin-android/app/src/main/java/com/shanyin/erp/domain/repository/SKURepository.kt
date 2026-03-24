package com.shanyin.erp.domain.repository

import com.shanyin.erp.data.local.entity.SKUEntity
import kotlinx.coroutines.flow.Flow

interface SKURepository {
    fun getSKUs(): Flow<List<SKUEntity>>
    suspend fun insertSKU(name: String, typeLevel1: String?, model: String?)
}
