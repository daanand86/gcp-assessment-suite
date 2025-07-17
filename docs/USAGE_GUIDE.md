# GCP Assessment Suite - Comprehensive Usage Guide

## 🎯 Assessment Scripts Overview

| Script | Purpose | Output Files | Use Case |
|--------|---------|--------------|----------|
| `gcp_master_assessment.py` | **Run all assessments** | All service outputs + summary | Complete organization analysis |
| `gcp_org_compute_inventory.py` | **Compute Engine** | inventory.csv + utilization.csv | Server inventory & performance |
| `gcp_networking_assessment.py` | **Networking** | 7 separate CSV files | Network architecture review |
| `gcp_storage_assessment.py` | **GCS Storage** | buckets.csv + usage.csv | Storage cost optimization |
| `gcp_gke_assessment.py` | **Kubernetes** | clusters.csv + pools.csv + workloads.csv | Container platform analysis |
| `validate_org_setup.py` | **Setup validation** | Console output | Pre-assessment verification |

## 🚀 Getting Started

### **Step 1: Validate Setup**
```bash
# Always run this first to check permissions and authentication
python3 validate_org_setup.py

# Set environment variables (optional)
export GCP_ORGANIZATION_ID="123456789012"
export GCP_FOLDER_ID="folders/123456789"  # Alternative to org
export GCP_PROJECT_IDS="proj1,proj2,proj3"  # Alternative to org/folder
```

### **Step 2: Choose Assessment Scope**

#### **Complete Organization Assessment**
```bash
# All services, entire organization
python3 gcp_master_assessment.py --org-id 123456789012

# Parallel execution (faster for large orgs)
python3 gcp_master_assessment.py --org-id 123456789012 --parallel
```

#### **Folder-Level Assessment**
```bash
# Assess specific business unit/folder
python3 gcp_master_assessment.py --folder-id folders/123456789
```

#### **Project-Level Assessment**
```bash
# Assess specific projects only
python3 gcp_master_assessment.py --project-ids proj1,proj2,proj3
```

### **Step 3: Individual Service Assessment**
```bash
# Only compute instances
python3 gcp_org_compute_inventory.py --org-id 123456789012

# Only networking resources
python3 gcp_networking_assessment.py --org-id 123456789012

# Only storage buckets
python3 gcp_storage_assessment.py --org-id 123456789012

# Only Kubernetes clusters
python3 gcp_gke_assessment.py --org-id 123456789012
```

## 📊 Output Files Reference

### **Master Assessment Output**
```
gcp_assessment_summary.txt           # Summary report
gcp_compute_inventory_TIMESTAMP.csv  # Compute instances
gcp_compute_utilization_TIMESTAMP.csv # Performance metrics
gcp_networking_vpcs_TIMESTAMP.csv    # VPC networks
gcp_networking_subnets_TIMESTAMP.csv # Subnets
gcp_networking_firewall_rules_TIMESTAMP.csv # Security rules
gcp_networking_load_balancers_TIMESTAMP.csv # Load balancers
gcp_networking_nat_gateways_TIMESTAMP.csv   # NAT gateways
gcp_networking_vpn_gateways_TIMESTAMP.csv   # VPN gateways
gcp_networking_dns_zones_TIMESTAMP.csv      # DNS zones
gcp_storage_buckets_TIMESTAMP.csv    # GCS buckets
gcp_storage_usage_TIMESTAMP.csv      # Storage usage
gcp_gke_clusters_TIMESTAMP.csv       # Kubernetes clusters
gcp_gke_node_pools_TIMESTAMP.csv     # Node pools
gcp_gke_workloads_TIMESTAMP.csv      # K8s workloads
*.log                                # Assessment logs
```

### **Individual Service Outputs**

#### **Compute Engine**
- **Inventory**: Instance specs, OS details, storage types, network config
- **Utilization**: 30-day CPU/memory metrics, runtime hours, uptime percentage

#### **Networking**
- **VPCs**: Network configurations, routing modes, MTU settings
- **Subnets**: IP ranges, regions, private Google access settings
- **Firewall Rules**: Security policies, source/destination rules, protocols
- **Load Balancers**: HTTP/S and Network LB configurations
- **NAT Gateways**: NAT configurations and IP allocation
- **VPN Gateways**: VPN tunnel configurations
- **DNS Zones**: Managed DNS zones and records

#### **Storage**
- **Buckets**: Configurations, security policies, lifecycle rules
- **Usage**: Storage sizes, object counts, cost analysis data

#### **GKE**
- **Clusters**: Kubernetes versions, security features, network config
- **Node Pools**: Machine types, autoscaling, resource calculations
- **Workloads**: Deployments, services, pods across all clusters

## 🔧 Advanced Usage Examples

### **Enterprise Assessment Scenarios**

#### **Monthly Security Audit**
```bash
#!/bin/bash
# monthly_security_audit.sh
TIMESTAMP=$(date +%Y%m%d)
REPORT_DIR="security_audit_$TIMESTAMP"
mkdir -p "$REPORT_DIR"

python3 gcp_master_assessment.py \
  --org-id $GCP_ORGANIZATION_ID \
  --parallel \
  --summary-report "$REPORT_DIR/security_summary_$TIMESTAMP.txt" \
  --log-level INFO

# Move all generated files to report directory
mv *.csv *.log "$REPORT_DIR/"

echo "Security audit completed: $REPORT_DIR"
```

#### **Cost Optimization Analysis**
```bash
#!/bin/bash
# cost_optimization.sh
# Focus on compute and storage for cost analysis

python3 gcp_master_assessment.py \
  --org-id $GCP_ORGANIZATION_ID \
  --services compute,storage \
  --parallel \
  --summary-report "cost_analysis_$(date +%Y%m%d).txt"

# Analyze results
python3 -c "
import pandas as pd
import glob

# Load compute data
compute = pd.read_csv(glob.glob('gcp_compute_inventory_*.csv')[0])
storage = pd.read_csv(glob.glob('gcp_storage_usage_*.csv')[0])

print('=== COST OPTIMIZATION OPPORTUNITIES ===')
print(f'Instances with expensive SSD storage: {len(compute[compute[\"storage_types\"].str.contains(\"pd-ssd\", na=False)])}')
print(f'Low utilization instances (<20% CPU): {len(compute[compute[\"uptime_percentage_30d\"].str.contains(\"<20\", na=False)])}')
print(f'Total storage cost (TB): {storage[\"total_size_tb\"].sum():.2f}')
"
```

#### **Development Environment Audit**
```bash
# Assess only development projects
python3 gcp_master_assessment.py \
  --project-ids dev-proj1,dev-proj2,dev-staging \
  --services compute,gke \
  --summary-report "dev_environment_audit.txt"
```

#### **Network Architecture Review**
```bash
# Detailed networking assessment
python3 gcp_networking_assessment.py \
  --org-id $GCP_ORGANIZATION_ID \
  --output-prefix network_architecture \
  --log-level DEBUG

# Generate network topology report
echo "Network Architecture Analysis" > network_report.txt
echo "=============================" >> network_report.txt
echo "VPCs: $(wc -l < network_architecture_vpcs_*.csv) networks" >> network_report.txt
echo "Subnets: $(wc -l < network_architecture_subnets_*.csv) subnets" >> network_report.txt
echo "Firewall Rules: $(wc -l < network_architecture_firewall_rules_*.csv) rules" >> network_report.txt
```

### **Team-Specific Assessments**

#### **Platform Team - Infrastructure Focus**
```bash
# Infrastructure components only
python3 gcp_master_assessment.py \
  --folder-id folders/infrastructure \
  --services compute,networking \
  --max-workers 15 \
  --summary-report "platform_infrastructure_$(date +%Y%m%d).txt"
```

#### **Data Team - Storage and Analytics**
```bash
# Storage and GKE for data workloads
python3 gcp_master_assessment.py \
  --folder-id folders/data-analytics \
  --services storage,gke \
  --summary-report "data_platform_assessment.txt"
```

#### **Security Team - Complete Audit**
```bash
# Full assessment with maximum detail
python3 gcp_master_assessment.py \
  --org-id $GCP_ORGANIZATION_ID \
  --parallel \
  --max-workers 20 \
  --timeout 7200 \
  --log-level DEBUG \
  --summary-report "security_compliance_$(date +%Y%m%d).txt"
```

## 📈 Data Analysis and Reporting

### **PowerShell Analysis Scripts**

#### **Compute Analysis**
```powershell
# Load compute inventory
$compute = Import-Csv "gcp_compute_inventory_*.csv"

# OS distribution
Write-Host "=== OS DISTRIBUTION ===" -ForegroundColor Green
$compute | Group-Object os_family | Sort-Object Count -Descending | 
  Format-Table Name, Count -AutoSize

# Machine type analysis
Write-Host "=== MACHINE TYPE USAGE ===" -ForegroundColor Green
$compute | Group-Object machine_type | Sort-Object Count -Descending | 
  Select-Object -First 10 | Format-Table Name, Count -AutoSize

# Storage cost analysis
Write-Host "=== STORAGE ANALYSIS ===" -ForegroundColor Green
$ssdInstances = $compute | Where-Object {$_.storage_types -like "*pd-ssd*"}
$totalSsdStorage = ($ssdInstances | Measure-Object total_storage_gb -Sum).Sum
Write-Host "Instances using SSD storage: $($ssdInstances.Count)"
Write-Host "Total SSD storage: $totalSsdStorage GB"

# Regional distribution
Write-Host "=== REGIONAL DISTRIBUTION ===" -ForegroundColor Green
$compute | Group-Object region | Sort-Object Count -Descending | 
  Format-Table Name, Count -AutoSize
```

#### **Network Analysis**
```powershell
# Load networking data
$vpcs = Import-Csv "gcp_networking_vpcs_*.csv"
$subnets = Import-Csv "gcp_networking_subnets_*.csv"
$firewalls = Import-Csv "gcp_networking_firewall_rules_*.csv"

Write-Host "=== NETWORK SUMMARY ===" -ForegroundColor Green
Write-Host "Total VPCs: $($vpcs.Count)"
Write-Host "Total Subnets: $($subnets.Count)"
Write-Host "Total Firewall Rules: $($firewalls.Count)"

# Subnet analysis by region
Write-Host "=== SUBNETS BY REGION ===" -ForegroundColor Green
$subnets | Group-Object region | Sort-Object Count -Descending | 
  Format-Table Name, Count -AutoSize

# Firewall rule analysis
Write-Host "=== FIREWALL RULES ANALYSIS ===" -ForegroundColor Green
$allowRules = $firewalls | Where-Object {$_.action -eq "ALLOW"}
$denyRules = $firewalls | Where-Object {$_.action -eq "DENY"}
Write-Host "Allow Rules: $($allowRules.Count)"
Write-Host "Deny Rules: $($denyRules.Count)"
```

### **Python Analysis Scripts**

#### **Comprehensive Analysis**
```python
#!/usr/bin/env python3
# comprehensive_analysis.py

import pandas as pd
import glob
import json
from datetime import datetime

def load_assessment_data():
    """Load all assessment data files."""
    data = {}
    
    # Load compute data
    compute_files = glob.glob('gcp_compute_inventory_*.csv')
    if compute_files:
        data['compute'] = pd.read_csv(compute_files[0])
    
    # Load storage data
    storage_files = glob.glob('gcp_storage_usage_*.csv')
    if storage_files:
        data['storage'] = pd.read_csv(storage_files[0])
    
    # Load GKE data
    gke_files = glob.glob('gcp_gke_clusters_*.csv')
    if gke_files:
        data['gke'] = pd.read_csv(gke_files[0])
    
    # Load networking data
    vpc_files = glob.glob('gcp_networking_vpcs_*.csv')
    if vpc_files:
        data['vpcs'] = pd.read_csv(vpc_files[0])
    
    return data

def generate_executive_summary(data):
    """Generate executive summary report."""
    print("=" * 60)
    print("GCP ENVIRONMENT EXECUTIVE SUMMARY")
    print("=" * 60)
    print(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Compute summary
    if 'compute' in data:
        compute_df = data['compute']
        print("COMPUTE INFRASTRUCTURE")
        print("-" * 30)
        print(f"Total Instances: {len(compute_df):,}")
        print(f"Running Instances: {len(compute_df[compute_df['status'] == 'RUNNING']):,}")
        print(f"Total vCPUs: {compute_df['vcpus'].sum():,}")
        print(f"Total Memory: {compute_df['memory_gb'].sum():,.1f} GB")
        print(f"Total Storage: {compute_df['total_storage_gb'].sum():,.1f} GB")
        print()
        
        # OS distribution
        print("Operating System Distribution:")
        os_dist = compute_df['os_family'].value_counts()
        for os_name, count in os_dist.head().items():
            print(f"  {os_name}: {count:,} instances")
        print()
    
    # Storage summary
    if 'storage' in data:
        storage_df = data['storage']
        print("STORAGE INFRASTRUCTURE")
        print("-" * 30)
        print(f"Total Buckets: {len(storage_df):,}")
        print(f"Total Storage: {storage_df['total_size_tb'].sum():.2f} TB")
        print(f"Total Objects: {storage_df['object_count'].sum():,}")
        print()
        
        # Storage by class
        print("Storage by Class:")
        storage_by_class = storage_df.groupby('storage_class')['total_size_gb'].sum()
        for storage_class, size_gb in storage_by_class.items():
            print(f"  {storage_class}: {size_gb:,.1f} GB")
        print()
    
    # GKE summary
    if 'gke' in data:
        gke_df = data['gke']
        print("KUBERNETES INFRASTRUCTURE")
        print("-" * 30)
        print(f"Total Clusters: {len(gke_df):,}")
        print(f"Total Nodes: {gke_df['node_count'].sum():,}")
        print(f"Total K8s vCPUs: {gke_df['total_vcpus'].sum():,}")
        print(f"Total K8s Memory: {gke_df['total_memory_gb'].sum():,.1f} GB")
        print()
    
    # Network summary
    if 'vpcs' in data:
        vpcs_df = data['vpcs']
        print("NETWORK INFRASTRUCTURE")
        print("-" * 30)
        print(f"Total VPCs: {len(vpcs_df):,}")
        print()

def identify_optimization_opportunities(data):
    """Identify cost and performance optimization opportunities."""
    print("OPTIMIZATION OPPORTUNITIES")
    print("=" * 40)
    
    if 'compute' in data:
        compute_df = data['compute']
        
        # High-cost storage
        ssd_instances = compute_df[compute_df['storage_types'].str.contains('pd-ssd', na=False)]
        print(f"• {len(ssd_instances)} instances using expensive SSD storage")
        
        # Preemptible opportunities
        non_preemptible_dev = compute_df[
            (compute_df['labels'].str.contains('development', na=False)) & 
            (compute_df['preemptible'] == 'False')
        ]
        print(f"• {len(non_preemptible_dev)} development instances could be preemptible")
        
        # Deletion protection
        unprotected_prod = compute_df[
            (compute_df['labels'].str.contains('production', na=False)) & 
            (compute_df['deletion_protection'] == 'False')
        ]
        print(f"• {len(unprotected_prod)} production instances lack deletion protection")
    
    if 'storage' in data:
        storage_df = data['storage']
        
        # Large buckets
        large_buckets = storage_df[storage_df['total_size_gb'] > 1000]
        print(f"• {len(large_buckets)} buckets over 1TB may benefit from lifecycle policies")
    
    print()

if __name__ == "__main__":
    data = load_assessment_data()
    generate_executive_summary(data)
    identify_optimization_opportunities(data)
```

## 🔍 Troubleshooting Guide

### **Common Issues and Solutions**

#### **1. Permission Denied Errors**
```bash
# Problem: "Permission denied" when accessing organization/projects
# Solution: Check and grant required IAM roles

# Check current permissions
gcloud organizations get-iam-policy $ORG_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:$USER_EMAIL"

# Grant required roles
gcloud organizations add-iam-policy-binding $ORG_ID \
  --member="user:$USER_EMAIL" \
  --role="roles/compute.viewer"
```

#### **2. API Not Enabled**
```bash
# Problem: "API has not been used in project" errors
# Solution: Enable required APIs

gcloud services enable compute.googleapis.com --project=$PROJECT_ID
gcloud services enable container.googleapis.com --project=$PROJECT_ID
gcloud services enable storage.googleapis.com --project=$PROJECT_ID
gcloud services enable dns.googleapis.com --project=$PROJECT_ID
gcloud services enable monitoring.googleapis.com --project=$PROJECT_ID
```

#### **3. Rate Limiting / Quota Exceeded**
```bash
# Problem: "Quota exceeded" or "Rate limit exceeded"
# Solution: Reduce parallel workers and add delays

python3 gcp_master_assessment.py \
  --org-id $ORG_ID \
  --max-workers 5 \
  --timeout 7200
```

#### **4. Large Organization Timeouts**
```bash
# Problem: Assessment times out for large organizations
# Solution: Use folder-level assessment or increase timeout

# Assess by folders
python3 gcp_master_assessment.py --folder-id folders/production
python3 gcp_master_assessment.py --folder-id folders/development

# Or increase timeout
python3 gcp_master_assessment.py \
  --org-id $ORG_ID \
  --timeout 10800 \
  --max-workers 3
```

#### **5. Memory Issues**
```bash
# Problem: Out of memory errors during large assessments
# Solution: Run services individually or reduce scope

# Run one service at a time
python3 gcp_org_compute_inventory.py --org-id $ORG_ID
python3 gcp_networking_assessment.py --org-id $ORG_ID
python3 gcp_storage_assessment.py --org-id $ORG_ID
python3 gcp_gke_assessment.py --org-id $ORG_ID
```

### **Performance Optimization**

#### **For Large Organizations (1000+ projects)**
```bash
# Use folder-based approach
FOLDERS=("folders/prod" "folders/dev" "folders/staging")

for folder in "${FOLDERS[@]}"; do
    echo "Processing $folder"
    python3 gcp_master_assessment.py \
      --folder-id "$folder" \
      --parallel \
      --max-workers 10 \
      --summary-report "${folder//\//_}_assessment.txt"
done
```

#### **Memory-Optimized Execution**
```bash
# Sequential execution with reduced workers
python3 gcp_master_assessment.py \
  --org-id $ORG_ID \
  --max-workers 5 \
  --timeout 14400  # 4 hours
```

## 📊 Integration Examples

### **CI/CD Pipeline Integration**
```yaml
# .github/workflows/gcp-assessment.yml
name: Monthly GCP Assessment
on:
  schedule:
    - cron: '0 2 1 * *'  # First day of month at 2 AM

jobs:
  assess:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - name: Install gcloud
        uses: google-github-actions/setup-gcloud@v1
      - name: Authenticate
        uses: google-github-actions/auth@v1
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}
      - name: Run Assessment
        run: |
          python3 gcp_master_assessment.py \
            --org-id ${{ secrets.ORG_ID }} \
            --parallel \
            --summary-report monthly_assessment_$(date +%Y%m%d).txt
      - name: Upload Results
        uses: actions/upload-artifact@v3
        with:
          name: gcp-assessment-results
          path: |
            *.csv
            *.txt
            *.log
```

### **Automated Reporting Script**
```bash
#!/bin/bash
# automated_reporting.sh

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_DIR="gcp_assessment_$TIMESTAMP"
mkdir -p "$REPORT_DIR"

echo "Starting GCP Assessment at $(date)"

# Run assessment
python3 gcp_master_assessment.py \
  --org-id $GCP_ORGANIZATION_ID \
  --parallel \
  --summary-report "$REPORT_DIR/summary_$TIMESTAMP.txt"

# Move files to report directory
mv *.csv *.log "$REPORT_DIR/"

# Generate additional analysis
python3 comprehensive_analysis.py > "$REPORT_DIR/detailed_analysis_$TIMESTAMP.txt"

# Create archive
tar -czf "gcp_assessment_$TIMESTAMP.tar.gz" "$REPORT_DIR"

echo "Assessment completed: gcp_assessment_$TIMESTAMP.tar.gz"

# Optional: Upload to GCS bucket
# gsutil cp "gcp_assessment_$TIMESTAMP.tar.gz" gs://your-reports-bucket/
```

This comprehensive usage guide provides everything needed to effectively use the GCP assessment suite for any organization size or use case!
