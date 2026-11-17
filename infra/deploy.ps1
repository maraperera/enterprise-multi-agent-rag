param(
    [Parameter(Mandatory=$true)][string]$ResourceGroup,
    [Parameter(Mandatory=$true)][string]$AcrName,
    [Parameter(Mandatory=$true)][string]$ContainerApp,
    [string]$Tag = "manual"
)
$ErrorActionPreference = "Stop"
az acr build --registry $AcrName --image "enterprise-rag:$Tag" .
if ($LASTEXITCODE -ne 0) { throw "ACR build failed" }
az containerapp update --resource-group $ResourceGroup --name $ContainerApp --image "$AcrName.azurecr.io/enterprise-rag:$Tag"
if ($LASTEXITCODE -ne 0) { throw "Container App update failed" }
