package com.shanyin.erp.domain.usecase

import com.shanyin.erp.data.local.dao.AdvancedDomainDao
import org.json.JSONObject
import javax.inject.Inject

data class InventoryRequestItem(
    val skuId: Long,
    val skuName: String,
    val warehouseName: String,
    val requestedQty: Int
)

class InventoryValidationUseCase @Inject constructor(
    private val advancedDao: AdvancedDomainDao
) {
    suspend operator fun invoke(items: List<InventoryRequestItem>): Pair<Boolean, List<String>> {
        val totals = mutableMapOf<Pair<Long, String>, Int>()
        val overStockErrors = mutableListOf<String>()

        // Aggregate identical requests
        for (item in items) {
            if (item.requestedQty <= 0) continue
            val key = Pair(item.skuId, item.warehouseName)
            totals[key] = totals.getOrDefault(key, 0) + item.requestedQty
        }

        // Validate against Material Inventory Table using parsed JSON stock maps natively
        for ((key, totalReq) in totals) {
            val (skuId, whName) = key
            val matInv = advancedDao.getMaterialInventoryBySkuId(skuId)
            
            var available = 0.0
            if (matInv != null && matInv.stockDistributionJson != null) {
                try {
                    val jsonObj = JSONObject(matInv.stockDistributionJson)
                    available = jsonObj.optDouble(whName, 0.0)
                } catch (e: Exception) {
                    // JSON parsing failed, consider available as 0.0
                }
            }
            
            if (totalReq > available) {
                // To fetch exact SKU name, we usually map it or get from requested items
                val skuName = items.first { it.skuId == skuId }.skuName
                overStockErrors.add("【$whName】的 $skuName: 申请 $totalReq, 当前存量 $available")
            }
        }

        return Pair(overStockErrors.isEmpty(), overStockErrors)
    }
}
