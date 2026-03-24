package com.shanyin.erp.domain.usecase

import com.shanyin.erp.data.local.dao.AdvancedDomainDao
import com.shanyin.erp.data.local.dao.VirtualContractDao
import com.shanyin.erp.data.local.entity.VirtualContractEntity
import javax.inject.Inject

data class CashflowProgressResult(
    val isReturn: Boolean = false,
    val goodsTotal: Double = 0.0,
    val goodsAppliedOffsets: Double = 0.0,
    val goodsNetPayable: Double = 0.0,
    val goodsPaid: Double = 0.0,
    val goodsBalance: Double = 0.0,
    val goodsPool: Double = 0.0,
    val goodsDue: Double = 0.0,
    val depositShould: Double = 0.0,
    val depositReceived: Double = 0.0,
    val depositRemaining: Double = 0.0
)

class CashflowCalculationUseCase @Inject constructor(
    private val advancedDao: AdvancedDomainDao,
    private val vcDao: VirtualContractDao
) {
    suspend operator fun invoke(vcId: Long): CashflowProgressResult {
        val vcWithItems = vcDao.getContractWithItems(vcId) ?: return CashflowProgressResult()
        val vc = vcWithItems.contract
        val isReturn = vc.status == "RETURN" // Assuming you encode return as a field or status for now

        // 1. Calculate pool balance (Prepayment / PreCollection Ledger lookup)
        // Note: For MVP we hardcode party lookup till full relationship entities mapped
        var poolBalance = 0.0
        val accountLevel1 = if (isReturn) "PRE_COLLECTION" else "PREPAYMENT"
        val partyType = "CUSTOMER" 
        val partyId = vc.customerLocalId

        val account = advancedDao.getFinanceAccount(accountLevel1, partyType, partyId)
        if (account != null) {
            val sums = advancedDao.getAccountBalanceSums(account.localId)
            val dSum = sums?.d ?: 0.0
            val cSum = sums?.c ?: 0.0
            poolBalance = if (accountLevel1 == "PRE_COLLECTION") cSum - dSum else dSum - cSum
        }

        // 2. Aggregate Cash flows
        val cfs = advancedDao.getCashFlowsByVcId(vcId)
        
        if (isReturn) {
            val totalAmt = vc.totalAmount
            val paidTotal = cfs.filter { it.type == "REFUND" }.sumOf { it.amount }
            val depShould = 0.0 // from elements/deposit_info
            val depReceived = cfs.filter { it.type == "RETURN_DEPOSIT" }.sumOf { it.amount }
            
            return CashflowProgressResult(
                isReturn = true,
                goodsTotal = totalAmt,
                goodsPaid = paidTotal,
                goodsBalance = maxOf(0.0, totalAmt - paidTotal),
                goodsPool = poolBalance,
                goodsDue = maxOf(0.0, totalAmt - paidTotal - poolBalance),
                depositShould = depShould,
                depositReceived = depReceived,
                depositRemaining = maxOf(0.0, depShould - depReceived)
            )
        } else {
            val totalAmt = vc.totalAmount
            val appliedOffsets = cfs.filter { it.type == "OFFSET_PAY" }.sumOf { it.amount }
            val cashPaid = cfs.filter { it.type in listOf("PREPAYMENT", "FULFILLMENT") }.sumOf { it.amount }
            val paidTotal = appliedOffsets + cashPaid
            
            val depShould = 0.0 // from deposit_info
            val depReceived = cfs.filter { it.type == "DEPOSIT" }.sumOf { it.amount }

            return CashflowProgressResult(
                isReturn = false,
                goodsTotal = totalAmt,
                goodsAppliedOffsets = appliedOffsets,
                goodsNetPayable = totalAmt - appliedOffsets,
                goodsPaid = paidTotal,
                goodsBalance = maxOf(0.0, totalAmt - paidTotal),
                goodsPool = poolBalance,
                goodsDue = maxOf(0.0, totalAmt - paidTotal - poolBalance),
                depositShould = depShould,
                depositReceived = depReceived,
                depositRemaining = maxOf(0.0, depShould - depReceived)
            )
        }
    }
}
