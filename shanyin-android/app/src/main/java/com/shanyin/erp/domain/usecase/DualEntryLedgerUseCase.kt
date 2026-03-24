package com.shanyin.erp.domain.usecase

import androidx.room.withTransaction
import com.shanyin.erp.data.local.AppDatabase
import com.shanyin.erp.data.local.dao.AdvancedDomainDao
import com.shanyin.erp.data.local.entity.CashFlowEntity
import com.shanyin.erp.data.local.entity.FinancialJournalEntity
import javax.inject.Inject

class DualEntryLedgerUseCase @Inject constructor(
    private val db: AppDatabase,
    private val advancedDao: AdvancedDomainDao,
    private val cashflowCalculationUseCase: CashflowCalculationUseCase,
    private val stateMachineUseCase: VirtualContractStateMachineUseCase
) {
    /**
     * Records a cash flow and automatically generates balanced double-entry accounting journals
     * entirely on the Android device using a local SQLite Transaction.
     */
    suspend fun recordCashFlowAndGenerateLedgers(
        vcId: Long,
        amount: Double,
        cfType: String,
        debitAccountId: Long,
        creditAccountId: Long
    ) {
        db.withTransaction {
            // 1. Atomic Insert of CashFlow
            val cfId = advancedDao.insertCashFlow(
                CashFlowEntity(
                    virtualContractId = vcId,
                    type = cfType,
                    amount = amount,
                    payerAccountId = creditAccountId, // Simplified payer/payee linking
                    payeeAccountId = debitAccountId
                )
            )

            // 2. Dual-Entry Accounting (T-Account generation)
            // Debit Entry (Usually Asset/Cash increase or Liability decrease)
            advancedDao.insertJournal(
                FinancialJournalEntity(
                    accountId = debitAccountId,
                    debit = amount,
                    credit = 0.0,
                    refVcId = vcId,
                    refType = "CashFlow_$cfId"
                )
            )

            // Credit Entry (Usually Revenue, Liability increase, or Asset decrease)
            advancedDao.insertJournal(
                FinancialJournalEntity(
                    accountId = creditAccountId,
                    debit = 0.0,
                    credit = amount,
                    refVcId = vcId,
                    refType = "CashFlow_$cfId"
                )
            )

            // 3. Trigger State Machine cascading updates locally!
            stateMachineUseCase.invoke(vcId, refType = "cash_flow", refId = cfId)
        }
    }
}
