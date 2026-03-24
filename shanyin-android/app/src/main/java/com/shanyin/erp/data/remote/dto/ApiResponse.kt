package com.shanyin.erp.data.remote.dto

data class ApiResponse<T>(
    val data: T?,
    val message: String?,
    val success: Boolean = true // Depending on your FastAPI wrapper structure
)
