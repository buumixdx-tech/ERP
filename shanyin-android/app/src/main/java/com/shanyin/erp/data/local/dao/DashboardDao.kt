package com.shanyin.erp.data.local.dao

import androidx.room.Dao
import androidx.room.Query
import kotlinx.coroutines.flow.Flow

@Dao
interface DashboardDao {
    @Query("SELECT COUNT(*) FROM channel_customers")
    fun getCustomerCountFlow(): Flow<Int>

    @Query("SELECT COUNT(*) FROM suppliers")
    fun getSupplierCountFlow(): Flow<Int>

    @Query("SELECT COUNT(*) FROM skus")
    fun getSkuCountFlow(): Flow<Int>
}
