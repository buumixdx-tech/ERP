package com.shanyin.erp.presentation.dashboard

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.shanyin.erp.domain.repository.DashboardRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class DashboardViewModel @Inject constructor(
    private val repository: DashboardRepository
) : ViewModel() {

    private val _customerCount = MutableStateFlow(0)
    val customerCount: StateFlow<Int> = _customerCount.asStateFlow()

    private val _supplierCount = MutableStateFlow(0)
    val supplierCount: StateFlow<Int> = _supplierCount.asStateFlow()

    private val _skuCount = MutableStateFlow(0)
    val skuCount: StateFlow<Int> = _skuCount.asStateFlow()

    init {
        viewModelScope.launch {
            repository.getCustomerCount().collect { count ->
                _customerCount.value = count
            }
        }
        viewModelScope.launch {
            repository.getSupplierCount().collect { count ->
                _supplierCount.value = count
            }
        }
        viewModelScope.launch {
            repository.getSkuCount().collect { count ->
                _skuCount.value = count
            }
        }
    }
}
