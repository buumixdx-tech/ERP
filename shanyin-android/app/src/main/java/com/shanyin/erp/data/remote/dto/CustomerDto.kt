package com.shanyin.erp.data.remote.dto

import com.google.gson.annotations.SerializedName
import com.shanyin.erp.data.local.entity.ChannelCustomerEntity
import com.shanyin.erp.data.local.entity.SyncStatus

data class CustomerDto(
    @SerializedName("id") val id: Long,
    @SerializedName("name") val name: String,
    @SerializedName("info") val info: String?
)

// Extension function to map DTO to Local Entity
fun CustomerDto.toEntity(): ChannelCustomerEntity {
    return ChannelCustomerEntity(
        // localId is 0 to let Room auto-generate, but we should match by remoteId if it exists
        remoteId = this.id,
        name = this.name,
        info = this.info,
        syncStatus = SyncStatus.SYNCED,
        lastModifiedLocal = System.currentTimeMillis()
    )
}
