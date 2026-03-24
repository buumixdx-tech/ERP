package com.shanyin.erp.data.repository

import com.shanyin.erp.data.local.dao.DashboardDao
import com.shanyin.erp.domain.repository.DashboardRepository
import kotlinx.coroutines.flow.Flow
import javax.inject.Inject

class DashboardRepositoryImpl @Inject constructor(
    private val dashboardDao: DashboardDao
) : DashboardRepository {

    override fun getCustomerCount(): Flow<Int> {
        return dashboardDao.getCustomerCountFlow()
    }

    override fun getSupplierCount(): Flow<Int> {
        return dashboardDao.getSupplierCountFlow()
    }

    override fun getSkuCount(): Flow<Int> {
        return dashboardDao.getSkuCountFlow()
    }
}
