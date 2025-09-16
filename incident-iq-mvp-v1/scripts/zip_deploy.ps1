\
param(
  [string]$WebAppName,
  [string]$ResourceGroup,
  [string]$ZipPath = "webapp.zip"
)
# Build zip
if (Test-Path $ZipPath) { Remove-Item $ZipPath }
Compress-Archive -Path app, .streamlit, requirements.txt -DestinationPath $ZipPath -Force
# Deploy
az webapp deploy --resource-group $ResourceGroup --name $WebAppName --src-path $ZipPath --type zip
# set startup command
az webapp config set -g $ResourceGroup -n $WebAppName --startup-file "python -m streamlit run app/streamlit_app.py --server.port=8000 --server.address=0.0.0.0"
Write-Host "Deployed. Visit: https://$WebAppName.azurewebsites.net"
