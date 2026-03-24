package com.shanyin.erp

import android.app.Application
import dagger.hilt.android.HiltAndroidApp

@HiltAndroidApp
class ShanYinApp : Application() {
    override fun onCreate() {
        super.onCreate()
    }
}
