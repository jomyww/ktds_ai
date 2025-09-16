param location string = resourceGroup().location
param searchName string
param aoaiName string
param webAppName string
param planName string = '${webAppName}-plan'

resource search 'Microsoft.Search/searchServices@2023-11-01' = {
  name: searchName
  location: location
  sku: {
    name: 'standard'
  }
  properties:{
    hostingMode: 'default'
    partitionCount: 1
    replicaCount: 1
    semanticSearch: 'free'
    disableLocalAuth: false
    authOptions: {
      apiKeyOnly: {}
    }
  }
}

resource aoai 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: aoaiName
  location: location
  kind: 'OpenAI'
  sku: {
    name: 'S0'
  }
  properties: {
    publicNetworkAccess: 'Enabled'
  }
}

resource plan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: planName
  location: location
  sku: {
    name: 'B1'
    tier: 'Basic'
    size: 'B1'
    capacity: 1
  }
}

resource web 'Microsoft.Web/sites@2023-12-01' = {
  name: webAppName
  location: location
  properties: {
    serverFarmId: plan.id
    siteConfig: {
      linuxFxVersion: 'PYTHON|3.11'
      appSettings: [
        { name: 'SCM_DO_BUILD_DURING_DEPLOYMENT', value: '1' }
        { name: 'WEBSITES_PORT', value: '8000' }
      ]
    }
    httpsOnly: true
  }
  kind: 'app,linux'
}
