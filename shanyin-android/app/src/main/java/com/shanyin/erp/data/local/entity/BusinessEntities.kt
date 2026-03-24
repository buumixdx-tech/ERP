package com.shanyin.erp.data.local.entity

import androidx.room.*

@Entity(
    tableName = "virtual_contracts",
    foreignKeys = [
        ForeignKey(
            entity = ChannelCustomerEntity::class,
            parentColumns = ["localId"],
            childColumns = ["customerLocalId"],
            onDelete = ForeignKey.RESTRICT
        )
    ],
    indices = [Index("customerLocalId")]
)
data class VirtualContractEntity(
    @PrimaryKey(autoGenerate = true) override val localId: Long = 0,
    override val remoteId: Long? = null,
    override val syncStatus: SyncStatus = SyncStatus.PENDING_INSERT,
    override val lastModifiedLocal: Long = System.currentTimeMillis(),
    
    val customerLocalId: Long,
    val contractNo: String,
    // DRAFT, PENDING_SYNC, APPROVED, IN_EXECUTION, COMPLETED, CANCELLED
    val status: String, 
    val totalAmount: Double,
    val createdAt: Long = System.currentTimeMillis()
) : SyncableEntity

@Entity(
    tableName = "virtual_contract_items",
    foreignKeys = [
        ForeignKey(
            entity = VirtualContractEntity::class,
            parentColumns = ["localId"],
            childColumns = ["contractLocalId"],
            onDelete = ForeignKey.CASCADE
        ),
        ForeignKey(
            entity = SKUEntity::class,
            parentColumns = ["localId"],
            childColumns = ["skuLocalId"],
            onDelete = ForeignKey.RESTRICT
        )
    ],
    indices = [Index("contractLocalId"), Index("skuLocalId")]
)
data class VirtualContractItemEntity(
    @PrimaryKey(autoGenerate = true) val localItemId: Long = 0,
    val contractLocalId: Long,
    val skuLocalId: Long,
    val quantity: Int,
    val unitPrice: Double,
    val totalPrice: Double
)

data class VirtualContractWithItems(
    @Embedded val contract: VirtualContractEntity,
    @Relation(
        parentColumn = "localId",
        entityColumn = "contractLocalId"
    )
    val items: List<VirtualContractItemEntity>
)
