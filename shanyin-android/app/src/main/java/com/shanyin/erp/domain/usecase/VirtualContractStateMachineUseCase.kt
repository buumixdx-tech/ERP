package com.shanyin.erp.domain.usecase

import com.shanyin.erp.data.local.dao.AdvancedDomainDao
import com.shanyin.erp.data.local.dao.VirtualContractDao
import com.shanyin.erp.data.local.entity.SystemEventEntity
import javax.inject.Inject

class VirtualContractStateMachineUseCase @Inject constructor(
    private val advancedDao: AdvancedDomainDao,
    private val vcDao: VirtualContractDao
) {
    suspend operator fun invoke(vcId: Long, refType: String? = null, refId: Long? = null) {
        val vcWithItems = vcDao.getContractWithItems(vcId) ?: return
        val vc = vcWithItems.contract
        var currentSubjectStatus = vc.status // Simplified representing subject status
        var currentCashStatus = vc.status    // Using main status temporarily if field missing
        var currentVcStatus = vc.status
        var isDirty = false

        // 1. Subject Status
        if (refType == "logistics" || refId == null) {
            val logistics = advancedDao.getLogisticsByVcId(vcId)
            if (logistics != null) {
                val newSubStatus = when (logistics.status) {
                    "FINISH" -> "FINISH"
                    "SIGNED" -> "SIGNED"
                    "TRANSIT" -> "SHIPPED"
                    else -> "EXE"
                }
                
                // Note: Real Desktop implementation has SubjectStatus column in VC.
                // Assuming status column handles it or we add subjectStatus to VC Entity later.
                // For MVP thickness: we directly cascade finish if conditions met.
            }
        }

        // 2. Cash Status
        if (refType == "cash_flow") {
            val cashFlows = advancedDao.getCashFlowsByVcId(vcId)
            val paidGoods = cashFlows.filter { it.type in listOf("PREPAYMENT", "FULFILLMENT", "REFUND", "OFFSET_PAY") }.sumOf { it.amount }
            val paidDeposit = cashFlows.filter { it.type == "DEPOSIT" }.sumOf { it.amount }
            val paidReturnDeposit = cashFlows.filter { it.type == "RETURN_DEPOSIT" }.sumOf { it.amount }
            
            val totalDue = vc.totalAmount // Using top level total
            val isGoodsCleared = paidGoods >= totalDue - 0.01
            
            if (isGoodsCleared) {
                val exists = advancedDao.getSystemEvent(SystemEventType.VC_GOODS_CLEARED, vcId)
                if (exists == null) {
                    advancedDao.insertSystemEvent(
                        SystemEventEntity(
                            eventType = SystemEventType.VC_GOODS_CLEARED,
                            aggregateType = SystemAggregateType.VIRTUAL_CONTRACT,
                            aggregateId = vcId,
                            payloadJson = "{\"amount\": $paidGoods}"
                        )
                    )
                }
            }
            // For MVP: Mark cash as FINISH if goods cleared (omitting deposit logic complexity for now based on minimal schema mapping)
            if (isGoodsCleared) {
                currentCashStatus = "FINISH"
            }
        }
        
        // 3. Overall VC Status
        // Example check to finish the contract natively!
        if (currentSubjectStatus == "FINISH" && currentCashStatus == "FINISH") {
            if (currentVcStatus != "FINISH") {
                currentVcStatus = "FINISH"
                isDirty = true
            }
        }
        
        if (isDirty) {
            vcDao.updateContract(vc.copy(status = currentVcStatus))
        }
    }
}
