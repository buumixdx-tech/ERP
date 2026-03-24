package com.shanyin.erp.data.local

import androidx.room.Database
import androidx.room.RoomDatabase
import com.shanyin.erp.data.local.entity.*
import com.shanyin.erp.data.local.dao.*

@Database(
    entities = [
        ChannelCustomerEntity::class,
        SupplierEntity::class,
        SKUEntity::class
    ],
    version = 1,
    exportSchema = false
)
abstract class AppDatabase : RoomDatabase() {
    abstract fun channelCustomerDao(): ChannelCustomerDao
}
