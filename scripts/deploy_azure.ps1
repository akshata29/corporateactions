# Azure Deployment Script for Corporate Actions POC
# This script helps deploy the services to Azure

param(
    [Parameter(Mandatory=$true)]
    [string]$ResourceGroupName,
    
    [Parameter(Mandatory=$true)]
    [string]$Location,
    
    [Parameter(Mandatory=$false)]
    [string]$SubscriptionId
)

Write-Host "🚀 Corporate Actions POC - Azure Deployment" -ForegroundColor Green

# Set subscription if provided
if ($SubscriptionId) {
    Write-Host "Setting Azure subscription to $SubscriptionId..." -ForegroundColor Yellow
    az account set --subscription $SubscriptionId
}

# Check if logged in to Azure
try {
    $account = az account show --query "name" -o tsv
    Write-Host "✅ Logged in to Azure as: $account" -ForegroundColor Green
} catch {
    Write-Host "❌ Not logged in to Azure. Please run 'az login' first." -ForegroundColor Red
    exit 1
}

# Create resource group
Write-Host "Creating resource group '$ResourceGroupName' in '$Location'..." -ForegroundColor Yellow
az group create --name $ResourceGroupName --location $Location

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Resource group created successfully" -ForegroundColor Green
} else {
    Write-Host "❌ Failed to create resource group" -ForegroundColor Red
    exit 1
}

# Generate unique names
$uniqueId = -join ((1..8) | ForEach {Get-Random -input ([char[]]([char]'a'..[char]'z'))})
$cosmosAccountName = "ca-cosmos-$uniqueId"
$searchServiceName = "ca-search-$uniqueId"
$openaiServiceName = "ca-openai-$uniqueId"
$appServicePlanName = "ca-plan-$uniqueId"
$webAppName = "ca-webapp-$uniqueId"

Write-Host "`n📊 Deploying Azure Services..." -ForegroundColor Green

# Deploy Cosmos DB
Write-Host "Creating Cosmos DB account '$cosmosAccountName'..." -ForegroundColor Yellow
az cosmosdb create `
    --resource-group $ResourceGroupName `
    --name $cosmosAccountName `
    --kind GlobalDocumentDB `
    --locations regionName=$Location failoverPriority=0 isZoneRedundant=False `
    --default-consistency-level "Session" `
    --enable-automatic-failover false `
    --enable-multiple-write-locations false

# Create Cosmos DB database and containers
Write-Host "Creating Cosmos DB database and containers..." -ForegroundColor Yellow
az cosmosdb sql database create `
    --account-name $cosmosAccountName `
    --resource-group $ResourceGroupName `
    --name "corporateactions"

az cosmosdb sql container create `
    --account-name $cosmosAccountName `
    --resource-group $ResourceGroupName `
    --database-name "corporateactions" `
    --name "events" `
    --partition-key-path "/event_id" `
    --throughput 400

az cosmosdb sql container create `
    --account-name $cosmosAccountName `
    --resource-group $ResourceGroupName `
    --database-name "corporateactions" `
    --name "comments" `
    --partition-key-path "/comment_id" `
    --throughput 400

# Deploy Azure Cognitive Search
Write-Host "Creating Azure Cognitive Search service '$searchServiceName'..." -ForegroundColor Yellow
az search service create `
    --resource-group $ResourceGroupName `
    --name $searchServiceName `
    --location $Location `
    --sku Standard `
    --replica-count 1 `
    --partition-count 1

# Deploy Azure OpenAI
Write-Host "Creating Azure OpenAI service '$openaiServiceName'..." -ForegroundColor Yellow
az cognitiveservices account create `
    --name $openaiServiceName `
    --resource-group $ResourceGroupName `
    --location $Location `
    --kind OpenAI `
    --sku S0 `
    --yes

# Deploy model to Azure OpenAI
Write-Host "Deploying GPT-4 model..." -ForegroundColor Yellow
az cognitiveservices account deployment create `
    --resource-group $ResourceGroupName `
    --name $openaiServiceName `
    --deployment-name "gpt-4" `
    --model-name "gpt-4" `
    --model-version "1106-Preview" `
    --model-format OpenAI `
    --sku-name "Standard" `
    --sku-capacity 10

Write-Host "Deploying text-embedding-ada-002 model..." -ForegroundColor Yellow
az cognitiveservices account deployment create `
    --resource-group $ResourceGroupName `
    --name $openaiServiceName `
    --deployment-name "text-embedding-ada-002" `
    --model-name "text-embedding-ada-002" `
    --model-version "2" `
    --model-format OpenAI `
    --sku-name "Standard" `
    --sku-capacity 10

# Create App Service Plan for web apps
Write-Host "Creating App Service Plan '$appServicePlanName'..." -ForegroundColor Yellow
az appservice plan create `
    --resource-group $ResourceGroupName `
    --name $appServicePlanName `
    --location $Location `
    --sku B1 `
    --is-linux

# Create Web App for Streamlit UI
Write-Host "Creating Web App '$webAppName'..." -ForegroundColor Yellow
az webapp create `
    --resource-group $ResourceGroupName `
    --plan $appServicePlanName `
    --name $webAppName `
    --runtime "PYTHON|3.9"

# Get connection strings and keys
Write-Host "`n🔑 Retrieving connection strings and keys..." -ForegroundColor Green

$cosmosEndpoint = az cosmosdb show --resource-group $ResourceGroupName --name $cosmosAccountName --query "documentEndpoint" -o tsv
$cosmosKey = az cosmosdb keys list --resource-group $ResourceGroupName --name $cosmosAccountName --query "primaryMasterKey" -o tsv

$searchEndpoint = "https://$searchServiceName.search.windows.net"
$searchKey = az search admin-key show --resource-group $ResourceGroupName --service-name $searchServiceName --query "primaryKey" -o tsv

$openaiEndpoint = az cognitiveservices account show --resource-group $ResourceGroupName --name $openaiServiceName --query "properties.endpoint" -o tsv
$openaiKey = az cognitiveservices account keys list --resource-group $ResourceGroupName --name $openaiServiceName --query "key1" -o tsv

# Generate .env file for production
$envContent = @"
# Azure Configuration - Production Environment
AZURE_COSMOS_ENDPOINT=$cosmosEndpoint
AZURE_COSMOS_KEY=$cosmosKey
AZURE_COSMOS_DATABASE_NAME=corporateactions

AZURE_SEARCH_ENDPOINT=$searchEndpoint
AZURE_SEARCH_KEY=$searchKey
AZURE_SEARCH_INDEX_NAME=corporateactions

AZURE_OPENAI_ENDPOINT=$openaiEndpoint
AZURE_OPENAI_KEY=$openaiKey
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4
AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME=text-embedding-ada-002

# Application Configuration
LOG_LEVEL=INFO
CORS_ORIGINS=*
"@

$envContent | Out-File -FilePath ".env.production" -Encoding UTF8

Write-Host "`n✅ Azure deployment completed successfully!" -ForegroundColor Green
Write-Host "`n📋 Deployment Summary:" -ForegroundColor White
Write-Host "Resource Group: $ResourceGroupName" -ForegroundColor Cyan
Write-Host "Location: $Location" -ForegroundColor Cyan
Write-Host "`nServices Created:" -ForegroundColor White
Write-Host "  📊 Cosmos DB: $cosmosAccountName" -ForegroundColor Cyan
Write-Host "  🔍 Search Service: $searchServiceName" -ForegroundColor Cyan
Write-Host "  🤖 OpenAI Service: $openaiServiceName" -ForegroundColor Cyan
Write-Host "  🌐 Web App: $webAppName" -ForegroundColor Cyan

Write-Host "`n📄 Configuration file created: .env.production" -ForegroundColor Yellow
Write-Host "You can now run the data ingestion script to populate the services with sample data." -ForegroundColor Gray

Write-Host "`n🚀 Next Steps:" -ForegroundColor White
Write-Host "1. Copy .env.production to .env" -ForegroundColor Gray
Write-Host "2. Run data ingestion: python scripts/data_ingestion.py" -ForegroundColor Gray
Write-Host "3. Deploy your applications to the created Web App" -ForegroundColor Gray
Write-Host "4. Configure Teams Bot with Azure Bot Service" -ForegroundColor Gray

Write-Host "`n💰 Estimated Monthly Cost: ~$200-300 USD (varies by usage)" -ForegroundColor Yellow
Write-Host "Consider using Azure Calculator for precise cost estimation." -ForegroundColor Gray
