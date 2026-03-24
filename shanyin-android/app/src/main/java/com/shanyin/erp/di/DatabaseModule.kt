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
        ).build()
    }

    @Provides
    @Singleton
    fun provideChannelCustomerDao(db: AppDatabase) = db.channelCustomerDao()
}
