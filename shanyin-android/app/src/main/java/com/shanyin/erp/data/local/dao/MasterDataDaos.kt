package com.shanyin.erp.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Update
import com.shanyin.erp.data.local.entity.ChannelCustomerEntity
import com.shanyin.erp.data.local.entity.SKUEntity
import com.shanyin.erp.data.local.entity.SupplierEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface ChannelCustomerDao {
    @Query("SELECT * FROM channel_customers")
    fun getAllCustomersFlow(): Flow<List<ChannelCustomerEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(customer: ChannelCustomerEntity): Long

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAll(customers: List<ChannelCustomerEntity>)

    @Update
    suspend fun update(customer: ChannelCustomerEntity)
}

@Dao
interface SupplierDao {
    @Query("SELECT * FROM suppliers")
    fun getAllSuppliersFlow(): Flow<List<SupplierEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(supplier: SupplierEntity): Long

    @Update
    suspend fun update(supplier: SupplierEntity)
}

@Dao
interface SKUDao {
    @Query("SELECT * FROM skus")
    fun getAllSKUsFlow(): Flow<List<SKUEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(sku: SKUEntity): Long

    @Update
    suspend fun update(sku: SKUEntity)
}
