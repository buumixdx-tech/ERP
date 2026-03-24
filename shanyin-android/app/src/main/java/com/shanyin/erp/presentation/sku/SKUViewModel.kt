package com.shanyin.erp.presentation.sku

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.shanyin.erp.data.local.entity.SKUEntity
import com.shanyin.erp.domain.repository.SKURepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class SKUViewModel @Inject constructor(
    private val repository: SKURepository
) : ViewModel() {

    private val _skus = MutableStateFlow<List<SKUEntity>>(emptyList())
    val skus: StateFlow<List<SKUEntity>> = _skus.asStateFlow()

    init {
        observeLocalSKUs()
    }

    private fun observeLocalSKUs() {
        viewModelScope.launch {
            repository.getSKUs()
                .catch { /* error handling */ }
                .collect { list ->
                    _skus.value = list
                }
        }
    }

    fun addSKU(name: String, type: String?, model: String?) {
        viewModelScope.launch {
            repository.insertSKU(name, type, model)
        }
    }
}
