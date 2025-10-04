# ============================================
# NewsRaag Multi-Region Deployment Script
# ============================================

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("dev", "prod")]
    [string]$Environment = "prod",
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("plan", "apply", "destroy", "init", "validate")]
    [string]$Action = "plan",
    
    [Parameter(Mandatory=$false)]
    [switch]$AutoApprove = $false,
    
    [Parameter(Mandatory=$false)]
    [switch]$Help = $false
)

if ($Help) {
    Write-Host @"
NewsRaag Multi-Region Deployment Script

Usage: .\deploy.ps1 -Environment <env> -Action <action> [-AutoApprove]

Parameters:
  -Environment    Environment to deploy (dev|prod) [default: prod]
  -Action         Terraform action (init|plan|apply|destroy|validate) [default: plan]  
  -AutoApprove    Skip confirmation prompts (use with caution)
  -Help          Show this help message

Examples:
  .\deploy.ps1                                  # Plan production deployment
  .\deploy.ps1 -Environment dev -Action apply   # Deploy to development
  .\deploy.ps1 -Action init                     # Initialize Terraform
  .\deploy.ps1 -Action validate                 # Validate configuration
  .\deploy.ps1 -Action apply -AutoApprove       # Deploy without confirmation

Prerequisites:
1. Azure CLI installed and logged in
2. Terraform installed
3. Update terraform/environments/$Environment.tfvars with your values
4. Ensure you have appropriate Azure permissions

"@ -ForegroundColor Green
    exit 0
}

# Color functions
function Write-Success { param($Message) Write-Host $Message -ForegroundColor Green }
function Write-Warning { param($Message) Write-Host $Message -ForegroundColor Yellow }
function Write-Error { param($Message) Write-Host $Message -ForegroundColor Red }
function Write-Info { param($Message) Write-Host $Message -ForegroundColor Blue }

# Check prerequisites
function Test-Prerequisites {
    Write-Info "🔍 Checking prerequisites..."
    
    # Check Azure CLI
    if (!(Get-Command az -ErrorAction SilentlyContinue)) {
        Write-Error "❌ Azure CLI not found. Please install Azure CLI first."
        exit 1
    }
    
    # Check Terraform
    if (!(Get-Command terraform -ErrorAction SilentlyContinue)) {
        Write-Error "❌ Terraform not found. Please install Terraform first."
        exit 1
    }
    
    # Check Azure login
    try {
        $account = az account show --query "name" -o tsv 2>$null
        if (!$account) {
            Write-Error "❌ Not logged into Azure. Please run 'az login' first."
            exit 1
        }
        Write-Success "✅ Logged into Azure as: $account"
    }
    catch {
        Write-Error "❌ Azure CLI error. Please run 'az login' first."
        exit 1
    }
    
    Write-Success "✅ Prerequisites check passed"
}

# Main deployment function
function Start-Deployment {
    $ErrorActionPreference = "Stop"
    
    Write-Info "🚀 Starting NewsRaag Multi-Region Deployment"
    Write-Info "   Environment: $Environment"
    Write-Info "   Action: $Action"
    Write-Info "   Directory: $(Get-Location)"
    
    # Test prerequisites
    Test-Prerequisites
    
    # Navigate to terraform directory
    $TerraformPath = Join-Path $PSScriptRoot "terraform"
    if (!(Test-Path $TerraformPath)) {
        Write-Error "❌ Terraform directory not found: $TerraformPath"
        exit 1
    }
    
    Push-Location $TerraformPath
    
    try {
        # Set environment file
        $TfVarsFile = "environments/$Environment.tfvars"
        if (!(Test-Path $TfVarsFile)) {
            Write-Error "❌ Environment file not found: $TfVarsFile"
            Write-Warning "Please create the file with your configuration."
            exit 1
        }
        
        Write-Info "📋 Using configuration: $TfVarsFile"
        
        # Execute Terraform command
        switch ($Action.ToLower()) {
            "init" {
                Write-Info "🔧 Initializing Terraform..."
                terraform init
            }
            
            "validate" {
                Write-Info "✅ Validating Terraform configuration..."
                terraform validate
                if ($LASTEXITCODE -eq 0) {
                    Write-Success "✅ Configuration is valid!"
                }
            }
            
            "plan" {
                Write-Info "📋 Creating Terraform plan..."
                terraform plan -var-file="$TfVarsFile" -out="tfplan-$Environment"
                if ($LASTEXITCODE -eq 0) {
                    Write-Success "✅ Plan created successfully!"
                    Write-Info "💡 To apply this plan, run: .\deploy.ps1 -Environment $Environment -Action apply"
                }
            }
            
            "apply" {
                if (Test-Path "tfplan-$Environment") {
                    Write-Info "🚀 Applying existing plan..."
                    terraform apply "tfplan-$Environment"
                } else {
                    Write-Info "🚀 Planning and applying..."
                    if ($AutoApprove) {
                        terraform apply -var-file="$TfVarsFile" -auto-approve
                    } else {
                        terraform apply -var-file="$TfVarsFile"
                    }
                }
                
                if ($LASTEXITCODE -eq 0) {
                    Write-Success "🎉 Deployment completed successfully!"
                    Write-Info "🔗 Check the outputs above for your application URLs"
                    
                    # Show next steps
                    Write-Info "📋 Next Steps:"
                    Write-Info "   1. Update your GitHub Actions to deploy to the new App Services"
                    Write-Info "   2. Test the Traffic Manager URL from the outputs"
                    Write-Info "   3. Configure your application settings in Azure portal"
                    Write-Info "   4. Set up monitoring dashboards in Application Insights"
                }
            }
            
            "destroy" {
                Write-Warning "⚠️  This will DESTROY all resources in $Environment environment!"
                if (!$AutoApprove) {
                    $confirmation = Read-Host "Are you sure you want to continue? Type 'yes' to confirm"
                    if ($confirmation -ne "yes") {
                        Write-Info "Deployment cancelled."
                        exit 0
                    }
                }
                
                terraform destroy -var-file="$TfVarsFile" $(if ($AutoApprove) { "-auto-approve" } else { "" })
            }
            
            default {
                Write-Error "❌ Unknown action: $Action"
                exit 1
            }
        }
        
        if ($LASTEXITCODE -ne 0) {
            Write-Error "❌ Terraform command failed with exit code: $LASTEXITCODE"
            exit 1
        }
        
    }
    catch {
        Write-Error "❌ Deployment failed: $($_.Exception.Message)"
        exit 1
    }
    finally {
        Pop-Location
    }
}

# Run deployment
Start-Deployment
