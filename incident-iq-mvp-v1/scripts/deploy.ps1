\
param(
  [string]$ResourceGroup,
  [string]$Location,
  [string]$SearchName,
  [string]$AoaiName,
  [string]$WebAppName
)
az group create -n $ResourceGroup -l $Location
az deployment group create -g $ResourceGroup --template-file scripts/provision_resources.bicep --parameters searchName=$SearchName aoaiName=$AoaiName webAppName=$WebAppName
