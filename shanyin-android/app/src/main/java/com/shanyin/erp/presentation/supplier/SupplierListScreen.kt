package com.shanyin.erp.presentation.supplier

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.shanyin.erp.data.local.entity.SupplierEntity

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SupplierListScreen(
    viewModel: SupplierViewModel = hiltViewModel()
) {
    val suppliers by viewModel.suppliers.collectAsState()
    var showAddDialog by remember { mutableStateOf(false) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("供应商管理 (本地版)") },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
            )
        },
        floatingActionButton = {
            FloatingActionButton(onClick = { showAddDialog = true }) {
                Icon(Icons.Default.Add, contentDescription = "新增供应商")
            }
        }
    ) { paddingValues ->
        Box(modifier = Modifier.fillMaxSize().padding(paddingValues)) {
            if (suppliers.isEmpty()) {
                Text(
                    text = "暂无供应商数据",
                    modifier = Modifier.align(Alignment.Center)
                )
            } else {
                LazyColumn(
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    items(suppliers) { supplier ->
                        SupplierItem(supplier)
                    }
                }
            }
        }

        if (showAddDialog) {
            AddSupplierDialog(
                onDismiss = { showAddDialog = false },
                onConfirm = { name, cat, addr ->
                    viewModel.addSupplier(name, cat, addr)
                    showAddDialog = false
                }
            )
        }
    }
}

@Composable
fun SupplierItem(supplier: SupplierEntity) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        elevation = CardDefaults.cardElevation(2.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(text = supplier.name, style = MaterialTheme.typography.titleMedium)
            if (!supplier.category.isNullOrBlank()) {
                Text(text = "分类: ${supplier.category}", style = MaterialTheme.typography.bodyMedium)
            }
            if (!supplier.address.isNullOrBlank()) {
                Text(text = "地址: ${supplier.address}", style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AddSupplierDialog(
    onDismiss: () -> Unit,
    onConfirm: (String, String, String) -> Unit
) {
    var name by remember { mutableStateOf("") }
    var category by remember { mutableStateOf("") }
    var address by remember { mutableStateOf("") }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("新增供应商") },
        text = {
            Column {
                OutlinedTextField(value = name, onValueChange = { name = it }, label = { Text("名称") })
                Spacer(modifier = Modifier.height(8.dp))
                OutlinedTextField(value = category, onValueChange = { category = it }, label = { Text("分类") })
                Spacer(modifier = Modifier.height(8.dp))
                OutlinedTextField(value = address, onValueChange = { address = it }, label = { Text("地址") })
            }
        },
        confirmButton = {
            Button(onClick = { if (name.isNotBlank()) onConfirm(name, category, address) }) {
                Text("保存")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("取消") }
        }
    )
}
