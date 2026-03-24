package com.shanyin.erp.sync

import android.content.Context
import android.util.Log
import androidx.hilt.work.HiltWorker
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import dagger.assisted.Assisted
import dagger.assisted.AssistedInject
import com.shanyin.erp.domain.repository.CustomerRepository
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/**
 * SyncWorker runs in the background to synchronize local changes 
 * with the remote FastAPI server.
 */
@HiltWorker
class SyncWorker @AssistedInject constructor(
    @Assisted appContext: Context,
    @Assisted workerParams: WorkerParameters,
    private val customerRepository: CustomerRepository
) : CoroutineWorker(appContext, workerParams) {

    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        try {
            Log.d("SyncWorker", "Starting datastore synchronization...")
            
            // Step 1: Push local pending changes to backend
            // In a real implementation: query local DB for syncStatus != SYNCED
            // loop them and use generic ApiService to upload.
            
            // Step 2: Pull the latest data from the remote API into the local Room DB
            customerRepository.refreshCustomers()
            
            // Other models logic... (Supplier, SKU, VirtualContract, etc.)
            
            Log.d("SyncWorker", "Synchronization finished successfully.")
            Result.success()
        } catch (e: Exception) {
            Log.e("SyncWorker", "Error during sync.", e)
            Result.retry()
        }
    }
}
