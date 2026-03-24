package com.shanyin.erp.domain.repository

import kotlinx.coroutines.flow.Flow

interface DashboardRepository {
    fun getCustomerCount(): Flow<Int>
    fun getSupplierCount(): Flow<Int>
    fun getSkuCount(): Flow<Int>
}
