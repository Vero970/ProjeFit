resource storage 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: 'calorifitstorage'
  location: resourceGroup().location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
}
