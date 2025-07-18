# GCP Services Assessment 

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![Google Cloud](https://img.shields.io/badge/Google%20Cloud-4285F4?logo=google-cloud&logoColor=white)](https://cloud.google.com/)

A comprehensive Google Cloud Platform assessment toolkit that provides detailed analysis across all major GCP services. Generate complete inventories, security assessments, and cost optimization insights for your entire GCP organization.

## 🎯 Overview

This suite provides **separate specialized scripts** for different GCP services, each generating **detailed CSV outputs** for focused analysis:

- **🖥️ Compute Engine** - Instances, OS details, storage types, utilization metrics
- **🌐 Networking** - VPCs, subnets, firewall rules, load balancers, NAT, VPN, DNS
- **💾 Storage** - GCS buckets, usage analytics, policies, security settings  
- **☸️ Kubernetes (GKE)** - Clusters, node pools, workloads, resource calculations
- **🎛️ Master Orchestrator** - Run all assessments with parallel execution

## 🚀 Quick Start

### Prerequisites
- Python 3.7+
- [Google Cloud SDK](https://cloud.google.com/sdk/docs/install)
- Appropriate GCP IAM permissions (see [Permissions Guide](docs/PERMISSIONS_GUIDE.md))

### Installation
```bash
# Clone the repository
git clone https://github.com/anandynwa/gcp-assessment-suite.git
cd gcp-assessment-suite

# Validate your GCP setup
python3 validate_org_setup.py
```

### Basic Usage
```bash
# Complete organization assessment (all services)
python3 gcp_master_assessment.py --org-id YOUR_ORG_ID

# Individual service assessments
python3 gcp_org_compute_inventory.py --org-id YOUR_ORG_ID
python3 gcp_networking_assessment.py --org-id YOUR_ORG_ID
python3 gcp_storage_assessment.py --org-id YOUR_ORG_ID
python3 gcp_gke_assessment.py --org-id YOUR_ORG_ID
```

## 📊 Output Files

The suite generates **15+ CSV files** with comprehensive data:

| Service | Output Files | Purpose |
|---------|--------------|---------|
| **Compute** | `inventory.csv`, `utilization.csv` | Instance specs, OS details, performance metrics |
| **Networking** | `vpcs.csv`, `subnets.csv`, `firewall_rules.csv`, `load_balancers.csv`, etc. | Network topology and security |
| **Storage** | `buckets.csv`, `usage.csv` | GCS configurations and usage analytics |
| **GKE** | `clusters.csv`, `node_pools.csv`, `workloads.csv` | Kubernetes infrastructure |

## 🔧 Advanced Usage

### Parallel Execution (Recommended for Large Organizations)
```bash
python3 gcp_master_assessment.py --org-id YOUR_ORG_ID --parallel
```

### Specific Services Only
```bash
python3 gcp_master_assessment.py --org-id YOUR_ORG_ID --services compute,networking
```

### Project or Folder Level Assessment
```bash
# Specific projects
python3 gcp_master_assessment.py --project-ids proj1,proj2,proj3

# Specific folder
python3 gcp_master_assessment.py --folder-id folders/123456789
```

## 📋 Key Features

### 🖥️ Enhanced Compute Assessment
- **OS Detection** - Ubuntu, Debian, CentOS, RHEL, Windows Server versions
- **Storage Analysis** - Types (SSD/Standard), sizes, boot disk details
- **Runtime Metrics** - 30-day uptime and utilization tracking
- **Security Config** - Preemptible instances, deletion protection

### 🌐 Comprehensive Networking
- **Network Topology** - Complete VPC, subnet, and routing analysis
- **Security Rules** - Detailed firewall rule analysis with source/destination
- **Load Balancers** - HTTP/S and Network LB configurations
- **Connectivity** - VPN gateways, NAT gateways, DNS zones

### 💾 Storage Analytics
- **Security Policies** - IAM, public access prevention, encryption
- **Usage Analytics** - Size calculations, object counts, cost analysis
- **Lifecycle Management** - Retention policies, storage classes
- **Compliance** - Versioning, CORS, website configurations

### ☸️ Kubernetes Assessment
- **Cluster Security** - Workload Identity, Binary Authorization, Network Policies
- **Resource Calculations** - Total vCPUs, memory, storage per cluster
- **Node Pool Analysis** - Autoscaling, machine types, spot instances
- **Workload Inventory** - Deployments, services, pods across namespaces

## 🔐 Required Permissions

### Organization-Level Assessment (Recommended)
```bash
# Core roles required
roles/compute.viewer
roles/monitoring.viewer  
roles/resourcemanager.organizationViewer
roles/browser
roles/storage.objectViewer
roles/container.viewer
roles/dns.reader
```

### Quick Setup
```bash
ORG_ID="123456789012"
USER_EMAIL="your-email@company.com"

gcloud organizations add-iam-policy-binding $ORG_ID \
    --member="user:$USER_EMAIL" \
    --role="roles/compute.viewer"
# ... (see docs/PERMISSIONS_GUIDE.md for complete setup)
```

## 📚 Documentation

- **[Usage Guide](docs/USAGE_GUIDE.md)** - Comprehensive usage examples and troubleshooting
- **[Permissions Guide](docs/PERMISSIONS_GUIDE.md)** - IAM setup and security best practices  
- **[Output Reference](docs/OUTPUT_REFERENCE.md)** - Complete field reference for all CSV files
- **[Examples](examples/)** - Sample analysis scripts and use cases

## 🎯 Use Cases

### Security & Compliance
- **Security Audits** - Complete infrastructure security posture
- **Compliance Reporting** - Detailed configurations for regulatory requirements
- **Vulnerability Management** - OS versions and patch management tracking

### Cost Optimization  
- **Resource Right-sizing** - Identify over/under-provisioned resources
- **Storage Optimization** - Analyze storage classes and lifecycle policies
- **Utilization Analysis** - Find idle or low-utilization instances

### Capacity Planning
- **Growth Projections** - Historical usage patterns and trends
- **Architecture Review** - Network topology and service dependencies
- **Migration Planning** - Complete inventory for cloud migrations

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

### Development Setup
```bash
git clone https://github.com/anandynwa/gcp-assessment-suite.git
cd gcp-assessment-suite

# Run validation
python3 validate_org_setup.py

# Test with a small scope first
python3 gcp_master_assessment.py --project-ids test-project
```


## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/anandynwa/gcp-assessment-suite/issues)
- **Discussions**: [GitHub Discussions](https://github.com/anandynwa/gcp-assessment-suite/discussions)
- **Documentation**: Check the [docs/](docs/) directory


**Ready to assess your GCP environment?** Start with `python3 validate_org_setup.py` then run your first assessment!
