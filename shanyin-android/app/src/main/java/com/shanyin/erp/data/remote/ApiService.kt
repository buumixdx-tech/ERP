package com.shanyin.erp.data.remote

import com.shanyin.erp.data.remote.dto.ApiResponse
import com.shanyin.erp.data.remote.dto.CustomerDto
import retrofit2.http.GET

interface ApiService {
    @GET("api/v1/master/customers")
    suspend fun getCustomers(): ApiResponse<List<CustomerDto>>
}
