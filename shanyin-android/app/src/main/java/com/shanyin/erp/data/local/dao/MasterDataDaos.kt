package com.shanyin.erp.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Update
import com.shanyin.erp.data.local.entity.ChannelCustomerEntity
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
