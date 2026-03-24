package com.shanyin.erp.domain.usecase

import com.shanyin.erp.data.local.dao.AdvancedDomainDao
import com.shanyin.erp.data.local.dao.VirtualContractDao
import com.shanyin.erp.data.local.entity.SystemEventEntity
import javax.inject.Inject

class VirtualContractStateMachineUseCase @Inject constructor(
    private val advancedDao: AdvancedDomainDao,
    private val vcDao: VirtualContractDao
) {
    suspend operator fun invoke(vcId: Long) {
        val vcWithItems = vcDao.getContractWithItems(vcId) ?: return
        val vc = vcWithItems.contract
        var currentSubjectStatus = "EXE"    // 默认执行中
        var currentCashStatus = "PENDING"  // 默认待结算
        var currentVcStatus = vc.status
        var isDirty = false

        // 1. Subject Status (Logistics)
        val logistics = advancedDao.getLogisticsByVcId(vcId)
        if (logistics != null) {
            currentSubjectStatus = when (logistics.status) {
                "FINISH" -> "FINISH"
                "SIGNED" -> "FINISH"
                "TRANSIT" -> "SHIPPED"
                else -> "EXE"
            }
        }

        // 2. Cash Status (Finance)
        val cashFlows = advancedDao.getCashFlowsByVcId(vcId)
        val paidGoods = cashFlows.filter { it.type in listOf("PREPAYMENT", "FULFILLMENT", "REFUND", "OFFSET_PAY") }.sumOf { it.amount }
        
        val totalDue = vc.totalAmount
        val isGoodsCleared = paidGoods >= totalDue - 0.01
        
        if (isGoodsCleared) {
            currentCashStatus = "FINISH"
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
        
        // 3. Overall VC Status Logic
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
