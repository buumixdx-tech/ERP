package com.shanyin.erp.domain.usecase

import com.shanyin.erp.data.local.dao.AdvancedDomainDao
import com.shanyin.erp.data.local.dao.VirtualContractDao
import com.shanyin.erp.data.local.entity.SystemEventEntity
import javax.inject.Inject

object SystemAggregateType {
    const val LOGISTICS = "logistics"
    const val VIRTUAL_CONTRACT = "virtual_contract"
}

object SystemEventType {
    const val LOGISTICS_STATUS_CHANGED = "logistics_status_changed"
    const val VC_GOODS_CLEARED = "vc_goods_cleared"
    const val VC_DEPOSIT_CLEARED = "vc_deposit_cleared"
}

class LogisticsStateMachineUseCase @Inject constructor(
    private val advancedDao: AdvancedDomainDao,
    private val vcStateMachineUseCase: VirtualContractStateMachineUseCase
) {
    suspend operator fun invoke(logisticsId: Long) {
        val logistics = advancedDao.getLogisticsById(logisticsId) ?: return
        
        val oldStatus = logistics.status
        if (oldStatus != "FINISH") {
            val expressOrders = advancedDao.getExpressOrdersByLogisticsId(logisticsId)
            var newStatus = "PENDING"
            if (expressOrders.isNotEmpty()) {
                if (expressOrders.all { it.status == "SIGNED" }) {
                    newStatus = "SIGNED"
                } else if (expressOrders.all { it.status == "TRANSIT" || it.status == "SIGNED" }) {
                    newStatus = "TRANSIT"
                }
            }
            if (newStatus != oldStatus) {
                // Update linguistics
                advancedDao.updateLogistics(logistics.copy(status = newStatus))
                
                // Emit system event
                advancedDao.insertSystemEvent(
                    SystemEventEntity(
                        eventType = SystemEventType.LOGISTICS_STATUS_CHANGED,
                        aggregateType = SystemAggregateType.LOGISTICS,
                        aggregateId = logisticsId,
                        payloadJson = "{\"from\":\"$oldStatus\", \"to\":\"$newStatus\"}"
                    )
                )
            }
        }
        
        // Trigger VC State machine
        vcStateMachineUseCase(logistics.virtualContractId, "logistics", logisticsId)
    }
}
