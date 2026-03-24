package com.shanyin.erp.data.remote

import retrofit2.http.GET

interface ApiService {
    // Defines standard endpoints corresponding to your FastAPI routes
    
    @GET("api/v1/master/customers")
    suspend fun getCustomers(): Any // Adjust Return type when defining Network schemas
}
