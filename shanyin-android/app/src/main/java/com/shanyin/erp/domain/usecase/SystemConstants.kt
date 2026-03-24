package com.shanyin.erp.domain.usecase

object SystemAggregateType {
    const val LOGISTICS = "logistics"
    const val VIRTUAL_CONTRACT = "virtual_contract"
}

object SystemEventType {
    const val LOGISTICS_STATUS_CHANGED = "logistics_status_changed"
    const val VC_GOODS_CLEARED = "vc_goods_cleared"
    const val VC_DEPOSIT_CLEARED = "vc_deposit_cleared"
}
