package com.shanyin.erp.di

import com.shanyin.erp.data.repository.CustomerRepositoryImpl
import com.shanyin.erp.data.repository.SKURepositoryImpl
import com.shanyin.erp.data.repository.SupplierRepositoryImpl
import com.shanyin.erp.data.repository.DashboardRepositoryImpl
import com.shanyin.erp.data.repository.VirtualContractRepositoryImpl
import com.shanyin.erp.domain.repository.CustomerRepository
import com.shanyin.erp.domain.repository.DashboardRepository
import com.shanyin.erp.domain.repository.SKURepository
import com.shanyin.erp.domain.repository.SupplierRepository
import com.shanyin.erp.domain.repository.VirtualContractRepository
import dagger.Binds
import dagger.Module
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
abstract class RepositoryModule {

    @Binds
    @Singleton
    abstract fun bindCustomerRepository(
        customerRepositoryImpl: CustomerRepositoryImpl
    ): CustomerRepository

    @Binds
    @Singleton
    abstract fun bindSupplierRepository(
        supplierRepositoryImpl: SupplierRepositoryImpl
    ): SupplierRepository

    @Binds
    @Singleton
    abstract fun bindSKURepository(
        skuRepositoryImpl: SKURepositoryImpl
    ): SKURepository

    @Binds
    @Singleton
    abstract fun bindDashboardRepository(
        dashboardRepositoryImpl: DashboardRepositoryImpl
    ): DashboardRepository

    @Binds
    @Singleton
    abstract fun bindVirtualContractRepository(impl: VirtualContractRepositoryImpl): VirtualContractRepository
}
