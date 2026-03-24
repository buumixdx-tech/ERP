package com.shanyin.erp.presentation.contract

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import com.shanyin.erp.data.local.entity.ChannelCustomerEntity
import com.shanyin.erp.data.local.entity.SKUEntity

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CreateContractDialog(
    viewModel: VirtualContractViewModel,
    onDismiss: () -> Unit
) {
    val customers by viewModel.customers.collectAsState()
    val skus by viewModel.skus.collectAsState()
    val draftItems by viewModel.draftItems.collectAsState()

    var selectedCustomer by remember { mutableStateOf<ChannelCustomerEntity?>(null) }
    var contractNo by remember { mutableStateOf("VC-" + System.currentTimeMillis().toString().takeLast(6)) }
    
    // Add Item Dialog State
    var showAddItem by remember { mutableStateOf(false) }

    Dialog(
        onDismissRequest = onDismiss,
        properties = DialogProperties(usePlatformDefaultWidth = false) // Full screen
    ) {
        Surface(modifier = Modifier.fillMaxSize()) {
            Column(modifier = Modifier.fillMaxSize().padding(16.dp)) {
                Text("拟定新业务合同", style = MaterialTheme.typography.headlineSmall)
                Spacer(modifier = Modifier.height(16.dp))
                
                OutlinedTextField(
                    value = contractNo,
                    onValueChange = { contractNo = it },
                    label = { Text("合同编号") },
                    modifier = Modifier.fillMaxWidth()
                )
                
                Spacer(modifier = Modifier.height(8.dp))
                
                // Simplified Customer Selector
                var customerDropdownExpanded by remember { mutableStateOf(false) }
                ExposedDropdownMenuBox(
                    expanded = customerDropdownExpanded,
                    onExpandedChange = { customerDropdownExpanded = !customerDropdownExpanded }
                ) {
                    OutlinedTextField(
                        value = selectedCustomer?.name ?: "点击选择关联客户",
                        onValueChange = {},
                        readOnly = true,
                        label = { Text("挂靠客户") },
                        trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = customerDropdownExpanded) },
                        modifier = Modifier.menuAnchor().fillMaxWidth()
                    )
                    ExposedDropdownMenu(
                        expanded = customerDropdownExpanded,
                        onDismissRequest = { customerDropdownExpanded = false }
                    ) {
                        customers.forEach { customer ->
                            DropdownMenuItem(
                                text = { Text(customer.name) },
                                onClick = {
                                    selectedCustomer = customer
                                    customerDropdownExpanded = false
                                }
                            )
                        }
                    }
                }
                
                Spacer(modifier = Modifier.height(16.dp))
                
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                    Text("合同明细清单", style = MaterialTheme.typography.titleMedium)
                    Button(onClick = { showAddItem = true }) {
                        Text("添加行")
                    }
                }
                
                Spacer(modifier = Modifier.height(8.dp))
                
                LazyColumn(modifier = Modifier.weight(1f)) {
                    itemsIndexed(draftItems) { index, item ->
                        Row(
                            modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column(modifier = Modifier.weight(1f)) {
                                Text(item.skuName)
                                Text("${item.quantity} x ¥${item.unitPrice} = ¥${item.totalPrice}", style = MaterialTheme.typography.bodySmall)
                            }
                            IconButton(onClick = { viewModel.removeDraftItem(index) }) {
                                Icon(Icons.Default.Delete, contentDescription = "删除该行", tint = MaterialTheme.colorScheme.error)
                            }
                        }
                        Divider()
                    }
                }
                
                Spacer(modifier = Modifier.height(16.dp))
                val sumTotal = draftItems.sumOf { it.totalPrice }
                Text("单据总额: ¥ $sumTotal", style = MaterialTheme.typography.titleMedium)
                
                Spacer(modifier = Modifier.height(16.dp))
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
                    TextButton(onClick = { viewModel.clearDraft(); onDismiss() }) { Text("取消") }
                    Spacer(modifier = Modifier.width(8.dp))
                    Button(onClick = {
                        if (selectedCustomer != null && draftItems.isNotEmpty()) {
                            viewModel.saveDraftContract(selectedCustomer!!.localId, contractNo)
                            onDismiss()
                        }
                    }, enabled = selectedCustomer != null && draftItems.isNotEmpty()) {
                        Text("存为离线草稿")
                    }
                }
            }
        }
        
        if (showAddItem) {
            AddItemDialog(skus, onDismiss = { showAddItem = false }) { sku, q, p ->
                viewModel.addDraftItem(sku, q, p)
                showAddItem = false
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AddItemDialog(
    skus: List<SKUEntity>,
    onDismiss: () -> Unit,
    onConfirm: (SKUEntity, Int, Double) -> Unit
) {
    var selectedSku by remember { mutableStateOf<SKUEntity?>(null) }
    var quantityStr by remember { mutableStateOf("") }
    var priceStr by remember { mutableStateOf("") }
    
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("添加明细行") },
        text = {
            Column {
                var skuDropdownExpanded by remember { mutableStateOf(false) }
                ExposedDropdownMenuBox(
                    expanded = skuDropdownExpanded,
                    onExpandedChange = { skuDropdownExpanded = !skuDropdownExpanded }
                ) {
                    OutlinedTextField(
                        value = selectedSku?.name ?: "点击选择 SKU",
                        onValueChange = {},
                        readOnly = true,
                        label = { Text("商品") },
                        trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = skuDropdownExpanded) },
                        modifier = Modifier.menuAnchor().fillMaxWidth()
                    )
                    ExposedDropdownMenu(
                        expanded = skuDropdownExpanded,
                        onDismissRequest = { skuDropdownExpanded = false }
                    ) {
                        skus.forEach { sku ->
                            DropdownMenuItem(
                                text = { Text(sku.name) },
                                onClick = {
                                    selectedSku = sku
                                    skuDropdownExpanded = false
                                }
                            )
                        }
                    }
                }
                Spacer(modifier = Modifier.height(8.dp))
                OutlinedTextField(value = quantityStr, onValueChange = { quantityStr = it }, label = { Text("数量") })
                Spacer(modifier = Modifier.height(8.dp))
                OutlinedTextField(value = priceStr, onValueChange = { priceStr = it }, label = { Text("单价") })
            }
        },
        confirmButton = {
            Button(onClick = {
                val q = quantityStr.toIntOrNull()
                val p = priceStr.toDoubleOrNull()
                if (selectedSku != null && q != null && p != null) onConfirm(selectedSku!!, q, p)
            }) { Text("添加") }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("取消") } }
    )
}
