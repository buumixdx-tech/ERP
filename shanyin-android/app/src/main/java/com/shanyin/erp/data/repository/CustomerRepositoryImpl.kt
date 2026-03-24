package com.shanyin.erp.data.repository

import android.util.Log
import com.shanyin.erp.data.local.dao.ChannelCustomerDao
import com.shanyin.erp.data.local.entity.ChannelCustomerEntity
import com.shanyin.erp.data.remote.ApiService
import com.shanyin.erp.data.remote.dto.toEntity
import com.shanyin.erp.domain.repository.CustomerRepository
import kotlinx.coroutines.flow.Flow
import javax.inject.Inject

class CustomerRepositoryImpl @Inject constructor(
    private val dao: ChannelCustomerDao,
    private val api: ApiService
) : CustomerRepository {

    override fun getCustomers(): Flow<List<ChannelCustomerEntity>> {
        // Single Source of Truth: UI always observes the local DB
        return dao.getAllCustomersFlow()
    }

    override suspend fun refreshCustomers() {
        try {
            val response = api.getCustomers()
            if (response.data != null) {
                // Map remote DTOs to local entities
                val remoteEntities = response.data.map { it.toEntity() }
                
                // Note: A robust implementation would handle conflicts here or in the SyncEngine.
                // For simplicity in Phase 2, we just insert/replace everything locally.
                // Room OnConflictStrategy.REPLACE will overwrite. We might need a smarter upsert
                // based on remoteId rather than localId. We will address upsert logic shortly.
                dao.insertAll(remoteEntities)
            }
        } catch (e: Exception) {
            // Offline gracefully: Network failures just mean we don't have fresh data
            // But the UI still shows the cached Flow<List> data via Room.
            Log.e("CustomerRepo", "Network fetch failed, observing local cache", e)
        }
    }

    override suspend fun insertCustomer(name: String, info: String?) {
        val newCustomer = ChannelCustomerEntity(
            name = name,
            info = info
        )
        // Instantly available to UI due to Room Flow, SyncEngine will upload later
        dao.insert(newCustomer)
    }
}
