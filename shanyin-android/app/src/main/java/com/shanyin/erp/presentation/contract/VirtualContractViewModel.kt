package com.shanyin.erp.presentation.contract

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.shanyin.erp.data.local.entity.ChannelCustomerEntity
import com.shanyin.erp.data.local.entity.SKUEntity
import com.shanyin.erp.data.local.entity.VirtualContractItemEntity
import com.shanyin.erp.domain.repository.CustomerRepository
import com.shanyin.erp.domain.repository.SKURepository
import com.shanyin.erp.domain.repository.VirtualContractRepository
import com.shanyin.erp.domain.usecase.DualEntryLedgerUseCase
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import javax.inject.Inject

data class DraftItemState(
    val skuLocalId: Long,
    val skuName: String,
    val quantity: Int,
    val unitPrice: Double
) {
    val totalPrice get() = quantity * unitPrice
}

@HiltViewModel
class VirtualContractViewModel @Inject constructor(
    private val contractRepository: VirtualContractRepository,
    private val customerRepository: CustomerRepository,
    private val skuRepository: SKURepository,
    private val dualEntryLedgerUseCase: DualEntryLedgerUseCase
) : ViewModel() {

    val contracts = contractRepository.getAllContractsFlow()
        .stateIn(viewModelScope, SharingStarted.Lazily, emptyList())
        
    val customers = customerRepository.getCustomers()
        .stateIn(viewModelScope, SharingStarted.Lazily, emptyList())
        
    val skus = skuRepository.getSKUs()
        .stateIn(viewModelScope, SharingStarted.Lazily, emptyList())

    private val _draftItems = MutableStateFlow<List<DraftItemState>>(emptyList())
    val draftItems: StateFlow<List<DraftItemState>> = _draftItems.asStateFlow()

    fun addDraftItem(sku: SKUEntity, quantity: Int, unitPrice: Double) {
        val current = _draftItems.value.toMutableList()
        current.add(DraftItemState(sku.localId, sku.name, quantity, unitPrice))
        _draftItems.value = current
    }

    fun removeDraftItem(index: Int) {
        val current = _draftItems.value.toMutableList()
        if (index in current.indices) {
            current.removeAt(index)
            _draftItems.value = current
        }
    }

    fun clearDraft() {
        _draftItems.value = emptyList()
    }

    fun saveDraftContract(customerLocalId: Long, contractNo: String) {
        val currentItems = _draftItems.value
        if (currentItems.isEmpty()) return
        
        val itemEntities = currentItems.map { 
            VirtualContractItemEntity(
                contractLocalId = 0, // Assigned correctly in repository transcation
                skuLocalId = it.skuLocalId,
                quantity = it.quantity,
                unitPrice = it.unitPrice,
                totalPrice = it.totalPrice
            )
        }
        
        viewModelScope.launch {
            contractRepository.createDraftContract(customerLocalId, contractNo, itemEntities)
            clearDraft()
        }
    }

    fun simulatePayment(vcId: Long, amount: Double) {
        viewModelScope.launch {
            // Using placeholder Account IDs (1L for Bank, 2L for Client AR)
            dualEntryLedgerUseCase.recordCashFlowAndGenerateLedgers(
                vcId = vcId,
                amount = amount,
                cfType = "FULFILLMENT",
                debitAccountId = 1L,
                creditAccountId = 2L
            )
        }
    }
}
