package com.shanyin.erp.presentation.sku

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
import com.shanyin.erp.data.local.entity.SKUEntity

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SKUListScreen(
    viewModel: SKUViewModel = hiltViewModel()
) {
    val skus by viewModel.skus.collectAsState()
    var showAddDialog by remember { mutableStateOf(false) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("商品库 (SKU)") },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
            )
        },
        floatingActionButton = {
            FloatingActionButton(onClick = { showAddDialog = true }) {
                Icon(Icons.Default.Add, contentDescription = "新增商品")
            }
        }
    ) { paddingValues ->
        Box(modifier = Modifier.fillMaxSize().padding(paddingValues)) {
            if (skus.isEmpty()) {
                Text(
                    text = "商品库为空",
                    modifier = Modifier.align(Alignment.Center)
                )
            } else {
                LazyColumn(
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    items(skus) { sku ->
                        SKUItem(sku)
                    }
                }
            }
        }

        if (showAddDialog) {
            AddSKUDialog(
                onDismiss = { showAddDialog = false },
                onConfirm = { name, type, model ->
                    viewModel.addSKU(name, type, model)
                    showAddDialog = false
                }
            )
        }
    }
}

@Composable
fun SKUItem(sku: SKUEntity) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        elevation = CardDefaults.cardElevation(2.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(text = sku.name, style = MaterialTheme.typography.titleMedium)
            if (!sku.typeLevel1.isNullOrBlank()) {
                Text(text = "类别: ${sku.typeLevel1}", style = MaterialTheme.typography.bodyMedium)
            }
            if (!sku.model.isNullOrBlank()) {
                Text(text = "型号: ${sku.model}", style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AddSKUDialog(
    onDismiss: () -> Unit,
    onConfirm: (String, String, String) -> Unit
) {
    var name by remember { mutableStateOf("") }
    var type by remember { mutableStateOf("") }
    var model by remember { mutableStateOf("") }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("新增商品 SKU") },
        text = {
            Column {
                OutlinedTextField(value = name, onValueChange = { name = it }, label = { Text("商品名称") })
                Spacer(modifier = Modifier.height(8.dp))
                OutlinedTextField(value = type, onValueChange = { type = it }, label = { Text("一级分类") })
                Spacer(modifier = Modifier.height(8.dp))
                OutlinedTextField(value = model, onValueChange = { model = it }, label = { Text("规格型号") })
            }
        },
        confirmButton = {
            Button(onClick = { if (name.isNotBlank()) onConfirm(name, type, model) }) {
                Text("保存")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("取消") }
        }
    )
}
