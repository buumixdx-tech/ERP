package com.shanyin.erp.domain.repository

import com.shanyin.erp.data.local.entity.ChannelCustomerEntity
import kotlinx.coroutines.flow.Flow

interface CustomerRepository {
    /**
     * Returns a reactive stream of local data.
     */
    fun getCustomers(): Flow<List<ChannelCustomerEntity>>

    /**
     * Triggers a remote fetch to update the local database.
     */
    suspend fun refreshCustomers()
    
    /**
     * Saves a new customer offline. SyncEngine will pick it up later.
     */
    suspend fun insertCustomer(name: String, info: String?)
}
