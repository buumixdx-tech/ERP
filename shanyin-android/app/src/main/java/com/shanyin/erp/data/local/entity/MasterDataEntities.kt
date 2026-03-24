package com.shanyin.erp.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

// Sync status enum
enum class SyncStatus {
    SYNCED,
    PENDING_INSERT,
    PENDING_UPDATE,
    PENDING_DELETE,
    CONFLICT
}

// Base interface for syncable entities
interface SyncableEntity {
    val localId: Long
    val remoteId: Long?
    val syncStatus: SyncStatus
    val lastModifiedLocal: Long
}

@Entity(tableName = "channel_customers")
data class ChannelCustomerEntity(
    @PrimaryKey(autoGenerate = true) override val localId: Long = 0,
    override val remoteId: Long? = null,
    override val syncStatus: SyncStatus = SyncStatus.PENDING_INSERT,
    override val lastModifiedLocal: Long = System.currentTimeMillis(),
    
    val name: String,
    val info: String?
) : SyncableEntity

@Entity(tableName = "suppliers")
data class SupplierEntity(
    @PrimaryKey(autoGenerate = true) override val localId: Long = 0,
    override val remoteId: Long? = null,
    override val syncStatus: SyncStatus = SyncStatus.PENDING_INSERT,
    override val lastModifiedLocal: Long = System.currentTimeMillis(),
    
    val name: String,
    val category: String?,
    val address: String?,
    val qualifications: String?,
    val info: String?
) : SyncableEntity

@Entity(tableName = "skus")
data class SKUEntity(
    @PrimaryKey(autoGenerate = true) override val localId: Long = 0,
    override val remoteId: Long? = null,
    override val syncStatus: SyncStatus = SyncStatus.PENDING_INSERT,
    override val lastModifiedLocal: Long = System.currentTimeMillis(),
    
    val supplierId: Long?,
    val name: String,
    val typeLevel1: String?,
    val typeLevel2: String?,
    val model: String?,
    val description: String?,
    val paramsJson: String?
) : SyncableEntity
