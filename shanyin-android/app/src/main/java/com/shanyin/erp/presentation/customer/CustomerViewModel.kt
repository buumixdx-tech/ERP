package com.shanyin.erp.presentation.customer

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.shanyin.erp.data.local.entity.ChannelCustomerEntity
import com.shanyin.erp.domain.repository.CustomerRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class CustomerViewModel @Inject constructor(
    private val repository: CustomerRepository
) : ViewModel() {

    private val _customers = MutableStateFlow<List<ChannelCustomerEntity>>(emptyList())
    val customers: StateFlow<List<ChannelCustomerEntity>> = _customers.asStateFlow()

    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()

    init {
        // Automatically observe local DB changes the moment ViewModel is created
        observeLocalCustomers()
        // Try fetching new data from API in background (Offline-first strategy)
        refreshFromRemote()
    }

    private fun observeLocalCustomers() {
        viewModelScope.launch {
            repository.getCustomers()
                .catch { /* Handle error */ }
                .collect { customerList ->
                    _customers.value = customerList
                }
        }
    }

    fun refreshFromRemote() {
        viewModelScope.launch {
            _isLoading.value = true
            repository.refreshCustomers()
            _isLoading.value = false
        }
    }

    fun addCustomer(name: String, info: String?) {
        viewModelScope.launch {
            // Instantly saved locally, UI will update automatically via Flow observation
            repository.insertCustomer(name, info)
        }
    }
}
