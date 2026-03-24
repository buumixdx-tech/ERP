package com.shanyin.erp.presentation.supplier

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.shanyin.erp.data.local.entity.SupplierEntity
import com.shanyin.erp.domain.repository.SupplierRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class SupplierViewModel @Inject constructor(
    private val repository: SupplierRepository
) : ViewModel() {

    private val _suppliers = MutableStateFlow<List<SupplierEntity>>(emptyList())
    val suppliers: StateFlow<List<SupplierEntity>> = _suppliers.asStateFlow()

    init {
        observeLocalSuppliers()
    }

    private fun observeLocalSuppliers() {
        viewModelScope.launch {
            repository.getSuppliers()
                .catch { /* error handling */ }
                .collect { list ->
                    _suppliers.value = list
                }
        }
    }

    fun addSupplier(name: String, category: String?, address: String?) {
        viewModelScope.launch {
            repository.insertSupplier(name, category, address)
        }
    }
}
