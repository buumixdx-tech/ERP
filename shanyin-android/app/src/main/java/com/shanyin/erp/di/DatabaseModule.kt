package com.shanyin.erp.di

import android.content.Context
import androidx.room.Room
import com.shanyin.erp.data.local.AppDatabase
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object DatabaseModule {

    @Provides
    @Singleton
    fun provideAppDatabase(@ApplicationContext context: Context): AppDatabase {
        return Room.databaseBuilder(
            context,
            AppDatabase::class.java,
            "shanyin_erp_local.db"
        )
        .fallbackToDestructiveMigration()
        .build()
    }

    @Provides
    @Singleton
    fun provideChannelCustomerDao(db: AppDatabase) = db.channelCustomerDao()

    @Provides
    @Singleton
    fun provideSupplierDao(db: AppDatabase) = db.supplierDao()

    @Provides
    @Singleton
    fun provideSKUDao(db: AppDatabase) = db.skuDao()

    @Provides
    @Singleton
    fun provideDashboardDao(db: AppDatabase) = db.dashboardDao()

    @Provides
    @Singleton
    fun provideVirtualContractDao(db: AppDatabase) = db.virtualContractDao()
}
