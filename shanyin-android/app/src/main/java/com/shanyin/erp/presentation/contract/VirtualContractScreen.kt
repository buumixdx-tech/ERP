package com.shanyin.erp.presentation.contract

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.shanyin.erp.data.local.entity.VirtualContractWithItems
import java.text.SimpleDateFormat
import java.util.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun VirtualContractScreen(
    viewModel: VirtualContractViewModel = hiltViewModel()
) {
    val contracts by viewModel.contracts.collectAsState()
    var showCreateSheet by remember { mutableStateOf(false) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("虚拟合同管理 (DRAFT)") },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
            )
        },
        floatingActionButton = {
            FloatingActionButton(onClick = { showCreateSheet = true }) {
                Icon(Icons.Default.Add, contentDescription = "拟定草稿")
            }
        }
    ) { paddingValues ->
        Box(modifier = Modifier.fillMaxSize().padding(paddingValues)) {
            if (contracts.isEmpty()) {
                Text(
                    text = "暂无业务单据\n点击右下角按钮进行预登记",
                    modifier = Modifier.align(Alignment.Center)
                )
            } else {
                LazyColumn(
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    items(contracts) { contractWithItems ->
                        ContractItem(contractWithItems, onPayClick = { amt ->
                            viewModel.simulatePayment(contractWithItems.contract.localId, amt)
                        })
                    }
                }
            }
        }
    }

    if (showCreateSheet) {
        CreateContractDialog(
            viewModel = viewModel,
            onDismiss = { showCreateSheet = false }
        )
    }
}

@Composable
fun ContractItem(withItems: VirtualContractWithItems, onPayClick: (Double) -> Unit = {}) {
    val contract = withItems.contract
    val items = withItems.items
    val sdf = remember { SimpleDateFormat("yyyy-MM-dd HH:mm", Locale.getDefault()) }
    
    Card(
        modifier = Modifier.fillMaxWidth(),
        elevation = CardDefaults.cardElevation(2.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Text(text = " 单号: ${contract.contractNo}", style = MaterialTheme.typography.titleMedium)
                Badge(containerColor = if (contract.status == "FINISH") MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.error) {
                    Text(contract.status, modifier = Modifier.padding(4.dp))
                }
            }
            Spacer(modifier = Modifier.height(8.dp))
            Text(text = "客户 (Local ID): ${contract.customerLocalId}", style = MaterialTheme.typography.bodyMedium)
            Text(text = "总计额度: ¥ ${contract.totalAmount}", style = MaterialTheme.typography.bodyMedium)
            Text(text = "创建时间: ${sdf.format(Date(contract.createdAt))}", style = MaterialTheme.typography.bodySmall)
            
            if (contract.status != "FINISH") {
                Spacer(modifier = Modifier.height(8.dp))
                Button(
                    onClick = { onPayClick(contract.totalAmount) },
                    modifier = Modifier.fillMaxWidth(),
                    colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.secondary)
                ) {
                    Text("💰 模拟结算 (触发复式记账与本地核销)")
                }
            }
            
            if (items.isNotEmpty()) {
                Spacer(modifier = Modifier.height(8.dp))
                HorizontalDivider()
                Spacer(modifier = Modifier.height(4.dp))
                items.forEach { item ->
                    Text(
                        text = "- SKU[${item.skuLocalId}] : ${item.quantity} 件 @ ¥${item.unitPrice}",
                        style = MaterialTheme.typography.bodySmall
                    )
                }
            }
        }
    }
}
