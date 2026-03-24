package com.shanyin.erp.data.local

import androidx.room.Database
import androidx.room.RoomDatabase
import com.shanyin.erp.data.local.entity.*
import com.shanyin.erp.data.local.dao.*

@Database(
    entities = [
        ChannelCustomerEntity::class,
        SupplierEntity::class,
        SKUEntity::class,
        VirtualContractEntity::class,
        VirtualContractItemEntity::class,
        LogisticsEntity::class,
        ExpressOrderEntity::class,
        CashFlowEntity::class,
        FinanceAccountEntity::class,
        FinancialJournalEntity::class,
        SystemEventEntity::class,
        EquipmentInventoryEntity::class,
        MaterialInventoryEntity::class
    ],
    version = 2,
    exportSchema = false
)
abstract class AppDatabase : RoomDatabase() {
    abstract fun channelCustomerDao(): ChannelCustomerDao
    abstract fun supplierDao(): SupplierDao
    abstract fun skuDao(): SKUDao
    abstract fun dashboardDao(): DashboardDao
    abstract fun virtualContractDao(): VirtualContractDao
    abstract fun advancedDomainDao(): AdvancedDomainDao
}
