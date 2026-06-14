// Archon — Azure Infrastructure (Bicep)
// Provisions all resources needed for the Azure deployment.
//
// Resources:
//   - Azure Container Registry
//   - Azure Storage Account (Blob Storage)
//   - Azure Database for PostgreSQL Flexible Server
//   - Azure Container Apps Environment
//   - Azure Container Apps Job (extraction)
//   - Azure Container Apps (analysis endpoint + backend)
//   - Azure AI Search (Foundry IQ knowledge index)
//   - Azure OpenAI (GPT-4o deployments)
//
// Deploy:
//   az deployment group create \
//     --resource-group archon-rg \
//     --template-file infra/main.bicep \
//     --parameters @infra/parameters.json

@description('Azure region for all resources')
param location string = resourceGroup().location

@description('Environment tag: dev | staging | prod')
param environment string = 'prod'

@description('PostgreSQL admin password')
@secure()
param postgresAdminPassword string

@description('Container image tag (default: latest)')
param imageTag string = 'latest'

@description('Azure region for Azure OpenAI — GPT-4o Standard available in swedencentral / eastus / northcentralus')
param openaiLocation string = 'swedencentral'

@description('Azure OpenAI API key — resolved by CI before deploy to avoid listKeys() race on account update')
@secure()
param openaiKey string = ''

@description('Allowed CORS origins for the backend API (comma-separated). Empty string falls back to allow-all in local/dev.')
param corsOrigins string = ''

var prefix = 'archon'
var tags = {
  project: 'archon'
  environment: environment
  challenge: 'AgentsLeague2026'
}

// ── Container Registry ────────────────────────────────────────────────────────

resource acr 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' = {
  name: '${prefix}acr${uniqueString(resourceGroup().id)}'
  location: location
  tags: tags
  sku: { name: 'Basic' }
  properties: {
    adminUserEnabled: true
  }
}

// ── Storage Account ───────────────────────────────────────────────────────────

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: '${prefix}sa${uniqueString(resourceGroup().id)}'
  location: location
  tags: tags
  kind: 'StorageV2'
  sku: { name: 'Standard_LRS' }
  properties: {
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: storage
  name: 'default'
}

resource archonContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobService
  name: 'archon'
  properties: { publicAccess: 'None' }
}

// ── PostgreSQL Flexible Server ─────────────────────────────────────────────────

resource pgServer 'Microsoft.DBforPostgreSQL/flexibleServers@2023-12-01-preview' = {
  name: '${prefix}-pg-${uniqueString(resourceGroup().id)}'
  location: location
  tags: tags
  sku: {
    name: 'Standard_B2ms'
    tier: 'Burstable'
  }
  properties: {
    administratorLogin: 'archon_admin'
    administratorLoginPassword: postgresAdminPassword
    version: '16'
    storage: { storageSizeGB: 32 }
    backup: { backupRetentionDays: 7, geoRedundantBackup: 'Disabled' }
    highAvailability: { mode: 'Disabled' }
    network: { publicNetworkAccess: 'Enabled' }
  }
}

resource pgDatabase 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2023-12-01-preview' = {
  parent: pgServer
  name: 'archon'
}

// ── Azure AI Search (Foundry IQ knowledge index) ──────────────────────────────

resource aiSearch 'Microsoft.Search/searchServices@2024-03-01-preview' = {
  name: '${prefix}-search-${uniqueString(resourceGroup().id)}'
  location: location
  tags: tags
  sku: { name: 'basic' }
  properties: {
    replicaCount: 1
    partitionCount: 1
    publicNetworkAccess: 'enabled'
    semanticSearch: 'free'
  }
}

// ── Azure AI Foundry (Machine Learning workspace — hosts the agent project) ───
// The Foundry project provides the agent runtime, connection registry (AI Search),
// and evaluation tooling used by the NarratorAgent (azure-ai-projects SDK).
//
// IMPORTANT: foundryWorkspace.properties.storageAccount is immutable after Hub creation.
// ARM PUT on subsequent deploys fails with "property cannot be modified".
// Using 'existing' references prevents ARM from attempting to update these resources.
// The Hub and Project were created on the initial deploy and must not be re-provisioned.

resource foundryWorkspace 'Microsoft.MachineLearningServices/workspaces@2024-04-01' existing = {
  name: '${prefix}-foundry-${uniqueString(resourceGroup().id)}'
}

resource foundryProject 'Microsoft.MachineLearningServices/workspaces@2024-04-01' existing = {
  name: '${prefix}-project'
}

// AI Search connection inside Foundry project — referenced as existing.
// The connection (archon-search) was created on initial deploy and is immutable;
// the credentials.key field cannot be updated via ARM PUT without risks of conflict.
resource searchConnection 'Microsoft.MachineLearningServices/workspaces/connections@2024-04-01' existing = {
  parent: foundryProject
  name: 'archon-search'
}

// ── Azure OpenAI ──────────────────────────────────────────────────────────────

resource openai 'Microsoft.CognitiveServices/accounts@2024-04-01-preview' = {
  name: '${prefix}-openai-${uniqueString(resourceGroup().id)}'
  location: openaiLocation
  tags: tags
  kind: 'OpenAI'
  sku: { name: 'S0' }
  properties: {
    publicNetworkAccess: 'Enabled'
    customSubDomainName: '${prefix}-openai-${uniqueString(resourceGroup().id)}'
  }
}

resource gpt4oVision 'Microsoft.CognitiveServices/accounts/deployments@2024-04-01-preview' = {
  parent: openai
  name: 'gpt-4o'
  sku: { name: 'Standard', capacity: 10 }
  properties: {
    model: { format: 'OpenAI', name: 'gpt-4o', version: '2024-11-20' }
  }
}

// ── Container Apps Environment ────────────────────────────────────────────────

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${prefix}-logs-${uniqueString(resourceGroup().id)}'
  location: location
  tags: tags
  properties: { sku: { name: 'PerGB2018' }, retentionInDays: 30 }
}

resource acaEnv 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${prefix}-env'
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

// ── Container Apps Job (extraction) ──────────────────────────────────────────

resource extractionJob 'Microsoft.App/jobs@2024-03-01' = {
  name: '${prefix}-extraction-job'
  location: location
  tags: tags
  properties: {
    environmentId: acaEnv.id
    configuration: {
      triggerType: 'Manual'
      replicaTimeout: 7200
      replicaRetryLimit: 1
      manualTriggerConfig: { replicaCompletionCount: 1, parallelism: 1 }
      registries: [{
        server: acr.properties.loginServer
        username: acr.listCredentials().username
        passwordSecretRef: 'acr-password'
      }]
      secrets: [
        {
          name: 'acr-password'
          value: acr.listCredentials().passwords[0].value
        }
        {
          name: 'storage-conn'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storage.name};AccountKey=${storage.listKeys().keys[0].value};EndpointSuffix=core.windows.net'
        }
        {
          name: 'openai-key'
          value: openaiKey
        }
      ]
    }
    template: {
      containers: [{
        name: 'archon-extraction'
        // Placeholder — pipeline updates to real ACR image after push
        image: 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
        resources: { cpu: json('2.0'), memory: '4Gi' }
        env: [
          { name: 'AZURE_STORAGE_CONTAINER', value: 'archon' }
          { name: 'AZURE_OPENAI_API_VERSION', value: '2024-05-01-preview' }
          { name: 'AZURE_OPENAI_VISION_DEPLOYMENT', value: 'gpt-4o' }
          { name: 'AZURE_STORAGE_CONNECTION_STRING', secretRef: 'storage-conn' }
          { name: 'AZURE_OPENAI_ENDPOINT', value: openai.properties.endpoint }
          { name: 'AZURE_OPENAI_API_KEY', secretRef: 'openai-key' }
        ]
      }]
    }
  }
  dependsOn: [acaEnv]
}

// ── Container App (analysis endpoint — always-on) ─────────────────────────────

resource analysisApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${prefix}-analysis'
  location: location
  tags: tags
  identity: { type: 'SystemAssigned' }    // managed identity for Foundry IQ DefaultAzureCredential
  properties: {
    environmentId: acaEnv.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8001
        transport: 'http'
      }
      registries: [{
        server: acr.properties.loginServer
        username: acr.listCredentials().username
        passwordSecretRef: 'acr-password'
      }]
      secrets: [
        { name: 'acr-password', value: acr.listCredentials().passwords[0].value }
        { name: 'storage-conn', value: 'DefaultEndpointsProtocol=https;AccountName=${storage.name};AccountKey=${storage.listKeys().keys[0].value};EndpointSuffix=core.windows.net' }
        { name: 'openai-key', value: openaiKey }
        { name: 'search-key', value: aiSearch.listAdminKeys().primaryKey }
        { name: 'pg-url', value: 'postgresql://archon_admin:${postgresAdminPassword}@${pgServer.properties.fullyQualifiedDomainName}:5432/archon' }
        // Foundry project connection string: <endpoint>;<sub>;<rg>;<project>
        // discoveryUrl resolves to a generic regional URL; the azure-ai-projects SDK requires
        // the workspace-specific API endpoint: https://<region>.api.azureml.ms
        { name: 'foundry-conn', value: 'https://${location}.api.azureml.ms;${subscription().subscriptionId};${resourceGroup().name};${foundryProject.name}' }
      ]
    }
    template: {
      containers: [{
        name: 'archon-analysis'
        // Placeholder — pipeline updates to real ACR image after push
        image: 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
        resources: { cpu: json('1.0'), memory: '2Gi' }
        env: [
          { name: 'AZURE_STORAGE_CONTAINER', value: 'archon' }
          { name: 'AZURE_OPENAI_API_VERSION', value: '2024-05-01-preview' }
          { name: 'AZURE_OPENAI_ANALYSIS_DEPLOYMENT', value: 'gpt-4o' }
          { name: 'AZURE_AI_SEARCH_INDEX', value: 'archon-knowledge' }
          { name: 'AZURE_OPENAI_ENDPOINT', value: openai.properties.endpoint }
          { name: 'AZURE_STORAGE_CONNECTION_STRING', secretRef: 'storage-conn' }
          { name: 'AZURE_OPENAI_API_KEY', secretRef: 'openai-key' }
          { name: 'AZURE_AI_SEARCH_ENDPOINT', value: 'https://${aiSearch.name}.search.windows.net' }
          { name: 'AZURE_AI_SEARCH_KEY', secretRef: 'search-key' }
          { name: 'DATABASE_URL', secretRef: 'pg-url' }
          // Foundry agent runtime — enables azure-ai-projects SDK in NarratorAgent
          { name: 'AZURE_AI_PROJECT_CONNECTION_STRING', secretRef: 'foundry-conn' }
          { name: 'AZURE_AI_SEARCH_CONNECTION_NAME', value: 'archon-search' }
        ]
        probes: [
          {
            type: 'Liveness'
            httpGet: { path: '/health', port: 8001, scheme: 'HTTP' }
            periodSeconds: 30
            failureThreshold: 3
          }
          {
            type: 'Readiness'
            httpGet: { path: '/health', port: 8001, scheme: 'HTTP' }
            initialDelaySeconds: 10
            periodSeconds: 10
            failureThreshold: 3
          }
        ]
      }]
      scale: {
        minReplicas: 1
        maxReplicas: 3
        rules: [
          {
            name: 'http-scale'
            http: { metadata: { concurrentRequests: '10' } }
          }
        ]
      }
    }
  }
  dependsOn: [acaEnv]
}

// ── Container App (backend — always-on) ───────────────────────────────────────

resource backendApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${prefix}-backend'
  location: location
  tags: tags
  identity: { type: 'SystemAssigned' }    // managed identity for SDK job submission
  properties: {
    environmentId: acaEnv.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
        transport: 'http'
      }
      registries: [{
        server: acr.properties.loginServer
        username: acr.listCredentials().username
        passwordSecretRef: 'acr-password'
      }]
      secrets: [
        { name: 'acr-password', value: acr.listCredentials().passwords[0].value }
        { name: 'storage-conn', value: 'DefaultEndpointsProtocol=https;AccountName=${storage.name};AccountKey=${storage.listKeys().keys[0].value};EndpointSuffix=core.windows.net' }
        { name: 'pg-url', value: 'postgresql://archon_admin:${postgresAdminPassword}@${pgServer.properties.fullyQualifiedDomainName}:5432/archon' }
        { name: 'openai-key', value: openaiKey }
      ]
    }
    template: {
      containers: [{
        name: 'archon-backend'
        // Placeholder — pipeline updates to real ACR image after push
        image: 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
        resources: { cpu: json('0.5'), memory: '1Gi' }
        env: [
          { name: 'AZURE_STORAGE_CONTAINER', value: 'archon' }
          { name: 'AZURE_OPENAI_API_VERSION', value: '2024-05-01-preview' }
          { name: 'AZURE_OPENAI_ENDPOINT', value: openai.properties.endpoint }
          { name: 'AZURE_OPENAI_API_KEY', secretRef: 'openai-key' }
          { name: 'AZURE_OPENAI_VISION_DEPLOYMENT', value: 'gpt-4o' }
          { name: 'EXTRACTION_IMAGE', value: '${acr.properties.loginServer}/archon-extraction:latest' }
          { name: 'ANALYSIS_ENDPOINT_URL', value: 'https://${analysisApp.properties.configuration.ingress.fqdn}' }
          { name: 'JOB_RUNNER_BACKEND', value: 'azure' }
          { name: 'AZURE_STORAGE_CONNECTION_STRING', secretRef: 'storage-conn' }
          { name: 'DATABASE_URL', secretRef: 'pg-url' }
          { name: 'ACA_JOB_NAME', value: '${prefix}-extraction-job' }
          { name: 'AZURE_RESOURCE_GROUP', value: resourceGroup().name }
          { name: 'AZURE_SUBSCRIPTION_ID', value: subscription().subscriptionId }
          { name: 'CORS_ORIGINS', value: corsOrigins }
        ]
        probes: [
          {
            type: 'Liveness'
            httpGet: { path: '/health', port: 8000, scheme: 'HTTP' }
            periodSeconds: 30
            failureThreshold: 3
          }
          {
            type: 'Readiness'
            httpGet: { path: '/health', port: 8000, scheme: 'HTTP' }
            initialDelaySeconds: 10
            periodSeconds: 10
            failureThreshold: 3
          }
        ]
      }]
      scale: {
        minReplicas: 1
        maxReplicas: 3
        rules: [
          {
            name: 'http-scale'
            http: { metadata: { concurrentRequests: '10' } }
          }
        ]
      }
    }
  }
  dependsOn: [acaEnv, analysisApp]
}

// Note: Role assignments for managed identities are applied once manually (az role
// assignment create) — not in Bicep to avoid Microsoft.Authorization/roleAssignments/write.
// backendApp: Contributor on archon-extraction-job (already applied)
// analysisApp: Azure AI Developer on foundryProject (apply after first deploy with managed identity)

// ── Outputs ───────────────────────────────────────────────────────────────────

output acrLoginServer string = acr.properties.loginServer
output analysisEndpointUrl string = 'https://${analysisApp.properties.configuration.ingress.fqdn}'
output backendUrl string = 'https://${backendApp.properties.configuration.ingress.fqdn}'
output storageAccountName string = storage.name
output openAIEndpoint string = openai.properties.endpoint
output searchEndpoint string = 'https://${aiSearch.name}.search.windows.net'
output postgresHost string = pgServer.properties.fullyQualifiedDomainName
output foundryProjectName string = foundryProject.name
output foundryConnectionString string = 'https://${location}.api.azureml.ms;${subscription().subscriptionId};${resourceGroup().name};${foundryProject.name}'
