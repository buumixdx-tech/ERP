package com.shanyin.erp.presentation.navigation

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.List
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.ShoppingCart
import androidx.compose.ui.graphics.vector.ImageVector

sealed class Screen(val route: String, val title: String, val icon: ImageVector) {
    object Dashboard : Screen("dashboard", "工作台", Icons.Filled.Home)
    object Customers : Screen("customers", "客户", Icons.Filled.Person)
    object Suppliers : Screen("suppliers", "供应商", Icons.Filled.ShoppingCart)
    object SKUs : Screen("skus", "商品SKU", Icons.Filled.List)
}
