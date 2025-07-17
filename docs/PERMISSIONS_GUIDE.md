# GCP Assessment Suite - Permissions Guide

## 🔐 Required IAM Roles Summary

| Assessment Scope | Required Roles | Grant Level |
|------------------|----------------|-------------|
| **Project-Level** | `compute.viewer`, `monitoring.viewer` | Per Project |
| **Folder-Level** | `compute.viewer`, `monitoring.viewer`, `browser` | Folder Level |
| **Organization-Level** | `compute.viewer`, `monitoring.viewer`, `resourcemanager.organizationViewer`, `browser` | Organization Level |

## 🎯 Quick Setup Commands

### **Organization-Level Assessment (Recommended)**
```bash
# Set variables
ORG_ID="123456789012"
USER_EMAIL="your-email@company.com"

# Grant all required roles
gcloud organizations add-iam-policy-binding $ORG_ID \
    --member="user:$USER_EMAIL" \
    --role="roles/compute.viewer"

gcloud organizations add-iam-policy-binding $ORG_ID \
    --member="user:$USER_EMAIL" \
    --role="roles/monitoring.viewer"

gcloud organizations add-iam-policy-binding $ORG_ID \
    --member="user:$USER_EMAIL" \
    --role="roles/resourcemanager.organizationViewer"

gcloud organizations add-iam-policy-binding $ORG_ID \
    --member="user:$USER_EMAIL" \
    --role="roles/browser"

# Additional roles for complete assessment
gcloud organizations add-iam-policy-binding $ORG_ID \
    --member="user:$USER_EMAIL" \
    --role="roles/storage.objectViewer"

gcloud organizations add-iam-policy-binding $ORG_ID \
    --member="user:$USER_EMAIL" \
    --role="roles/container.viewer"

gcloud organizations add-iam-policy-binding $ORG_ID \
    --member="user:$USER_EMAIL" \
    --role="roles/dns.reader"
```

### **Service Account Setup (For Automation)**
```bash
# Create service account
ADMIN_PROJECT="your-admin-project"
SA_NAME="gcp-assessor"

gcloud iam service-accounts create $SA_NAME \
    --display-name="GCP Assessment Service Account" \
    --project=$ADMIN_PROJECT

SA_EMAIL="${SA_NAME}@${ADMIN_PROJECT}.iam.gserviceaccount.com"

# Grant organization-level permissions
gcloud organizations add-iam-policy-binding $ORG_ID \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/compute.viewer"

gcloud organizations add-iam-policy-binding $ORG_ID \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/monitoring.viewer"

gcloud organizations add-iam-policy-binding $ORG_ID \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/resourcemanager.organizationViewer"

gcloud organizations add-iam-policy-binding $ORG_ID \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/browser"

gcloud organizations add-iam-policy-binding $ORG_ID \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/storage.objectViewer"

gcloud organizations add-iam-policy-binding $ORG_ID \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/container.viewer"

gcloud organizations add-iam-policy-binding $ORG_ID \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/dns.reader"

# Create and download key
gcloud iam service-accounts keys create gcp-assessor-key.json \
    --iam-account=$SA_EMAIL

# Use the service account
export GOOGLE_APPLICATION_CREDENTIALS="./gcp-assessor-key.json"
```

## 📋 Detailed Role Permissions

### **Core Roles**

#### **roles/compute.viewer**
```yaml
Purpose: Read access to Compute Engine resources
Permissions:
  - compute.instances.list
  - compute.instances.get
  - compute.machineTypes.get
  - compute.disks.get
  - compute.zones.list
  - compute.regions.list
  - compute.networks.list
  - compute.subnetworks.list
  - compute.firewalls.list
  - compute.forwardingRules.list
  - compute.urlMaps.list
  - compute.routers.list
```

#### **roles/monitoring.viewer**
```yaml
Purpose: Read access to Cloud Monitoring metrics
Permissions:
  - monitoring.metricDescriptors.list
  - monitoring.timeSeries.list
  - monitoring.monitoredResourceDescriptors.list
```

#### **roles/resourcemanager.organizationViewer**
```yaml
Purpose: Read access to organization structure
Permissions:
  - resourcemanager.organizations.get
  - resourcemanager.projects.list
  - resourcemanager.folders.list
```

#### **roles/browser**
```yaml
Purpose: Basic read access to resources
Permissions:
  - resourcemanager.projects.get
  - resourcemanager.projects.list
  - resourcemanager.folders.list
```

### **Service-Specific Roles**

#### **roles/storage.objectViewer**
```yaml
Purpose: Read access to GCS buckets and objects
Permissions:
  - storage.buckets.list
  - storage.buckets.get
  - storage.objects.list
  - storage.objects.get
```

#### **roles/container.viewer**
```yaml
Purpose: Read access to GKE clusters
Permissions:
  - container.clusters.list
  - container.clusters.get
  - container.nodes.list
  - container.pods.list
```

#### **roles/dns.reader**
```yaml
Purpose: Read access to DNS zones
Permissions:
  - dns.managedZones.list
  - dns.managedZones.get
  - dns.resourceRecordSets.list
```

## 🔧 Setup by Use Case

### **Development Team (Project-Level)**
```bash
# For specific projects only
PROJECTS=("dev-project-1" "dev-project-2")
DEV_EMAIL="developer@company.com"

for PROJECT in "${PROJECTS[@]}"; do
    gcloud projects add-iam-policy-binding $PROJECT \
        --member="user:$DEV_EMAIL" \
        --role="roles/compute.viewer"
    
    gcloud projects add-iam-policy-binding $PROJECT \
        --member="user:$DEV_EMAIL" \
        --role="roles/monitoring.viewer"
    
    gcloud projects add-iam-policy-binding $PROJECT \
        --member="user:$DEV_EMAIL" \
        --role="roles/storage.objectViewer"
done
```

### **Platform Team (Folder-Level)**
```bash
# For business unit/folder
FOLDER_ID="folders/123456789"
PLATFORM_EMAIL="platform-team@company.com"

gcloud resource-manager folders add-iam-policy-binding $FOLDER_ID \
    --member="user:$PLATFORM_EMAIL" \
    --role="roles/compute.viewer"

gcloud resource-manager folders add-iam-policy-binding $FOLDER_ID \
    --member="user:$PLATFORM_EMAIL" \
    --role="roles/monitoring.viewer"

gcloud resource-manager folders add-iam-policy-binding $FOLDER_ID \
    --member="user:$PLATFORM_EMAIL" \
    --role="roles/browser"

gcloud resource-manager folders add-iam-policy-binding $FOLDER_ID \
    --member="user:$PLATFORM_EMAIL" \
    --role="roles/storage.objectViewer"

gcloud resource-manager folders add-iam-policy-binding $FOLDER_ID \
    --member="user:$PLATFORM_EMAIL" \
    --role="roles/container.viewer"
```

### **Security Team (Organization-Level)**
```bash
# Full organization access
SECURITY_EMAIL="security-team@company.com"

# Use the organization-level commands from the quick setup above
# Replace USER_EMAIL with SECURITY_EMAIL
```

## 🔍 Permission Validation

### **Check Current Permissions**
```bash
# Check user permissions on organization
gcloud organizations get-iam-policy $ORG_ID \
    --flatten="bindings[].members" \
    --format="table(bindings.role)" \
    --filter="bindings.members:$USER_EMAIL"

# Check user permissions on project
gcloud projects get-iam-policy $PROJECT_ID \
    --flatten="bindings[].members" \
    --format="table(bindings.role)" \
    --filter="bindings.members:$USER_EMAIL"

# Check service account permissions
gcloud organizations get-iam-policy $ORG_ID \
    --flatten="bindings[].members" \
    --format="table(bindings.role)" \
    --filter="bindings.members:$SA_EMAIL"
```

### **Test API Access**
```bash
# Test compute API
gcloud compute instances list --project=$PROJECT_ID --limit=1

# Test monitoring API
gcloud monitoring metrics list --project=$PROJECT_ID --limit=1

# Test storage API
gsutil ls -p $PROJECT_ID

# Test container API
gcloud container clusters list --project=$PROJECT_ID

# Test DNS API
gcloud dns managed-zones list --project=$PROJECT_ID
```

## 🚨 Troubleshooting Permissions

### **Common Error Messages**

#### **"Permission denied on resource project"**
```bash
# Missing: roles/compute.viewer
# Solution:
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="user:$USER_EMAIL" \
    --role="roles/compute.viewer"
```

#### **"User does not have permission to access organization"**
```bash
# Missing: roles/resourcemanager.organizationViewer
# Solution:
gcloud organizations add-iam-policy-binding $ORG_ID \
    --member="user:$USER_EMAIL" \
    --role="roles/resourcemanager.organizationViewer"
```

#### **"API has not been used in project"**
```bash
# Missing: API not enabled
# Solution:
gcloud services enable compute.googleapis.com --project=$PROJECT_ID
gcloud services enable monitoring.googleapis.com --project=$PROJECT_ID
gcloud services enable storage.googleapis.com --project=$PROJECT_ID
gcloud services enable container.googleapis.com --project=$PROJECT_ID
```

#### **"Insufficient permissions for monitoring data"**
```bash
# Missing: roles/monitoring.viewer
# Solution:
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="user:$USER_EMAIL" \
    --role="roles/monitoring.viewer"
```

#### **"Access denied to GCS bucket"**
```bash
# Missing: roles/storage.objectViewer
# Solution:
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="user:$USER_EMAIL" \
    --role="roles/storage.objectViewer"
```

## 🔒 Security Best Practices

### **Principle of Least Privilege**
```bash
# Grant permissions at the lowest possible level
# Project-level for development teams
# Folder-level for business units
# Organization-level only for security/compliance teams
```

### **Service Account Security**
```bash
# Rotate keys regularly (every 90 days)
gcloud iam service-accounts keys create new-key.json \
    --iam-account=$SA_EMAIL

# Delete old keys
gcloud iam service-accounts keys delete $KEY_ID \
    --iam-account=$SA_EMAIL

# Monitor service account usage
gcloud logging read "protoPayload.authenticationInfo.principalEmail=$SA_EMAIL" \
    --limit=10 --format="table(timestamp,protoPayload.methodName)"
```

### **Audit and Monitoring**
```bash
# Enable audit logging for IAM changes
gcloud logging sinks create iam-audit-sink \
    bigquery.googleapis.com/projects/$PROJECT_ID/datasets/audit_logs \
    --log-filter='protoPayload.serviceName="iam.googleapis.com"'

# Monitor assessment tool usage
gcloud logging read 'protoPayload.authenticationInfo.principalEmail="$SA_EMAIL"' \
    --limit=50 --format="table(timestamp,protoPayload.methodName,protoPayload.resourceName)"
```

## 📊 Permission Matrix by Assessment

| Assessment | Required Roles | Optional Roles | APIs Required |
|------------|----------------|----------------|---------------|
| **Compute** | `compute.viewer`, `monitoring.viewer` | - | `compute.googleapis.com`, `monitoring.googleapis.com` |
| **Networking** | `compute.viewer` | `dns.reader` | `compute.googleapis.com`, `dns.googleapis.com` |
| **Storage** | `storage.objectViewer` | `storage.legacyBucketReader` | `storage.googleapis.com` |
| **GKE** | `container.viewer` | `container.clusterViewer` | `container.googleapis.com` |
| **All Services** | All above roles | - | All above APIs |

## 🎯 Validation Checklist

Before running assessments, verify:

- [ ] **Authentication**: `gcloud auth list` shows active account
- [ ] **Organization Access**: `gcloud organizations list` shows your org
- [ ] **Project Access**: `gcloud projects list --limit=5` shows projects
- [ ] **Compute API**: `gcloud compute instances list --limit=1` works
- [ ] **Monitoring API**: `gcloud monitoring metrics list --limit=1` works
- [ ] **Storage API**: `gsutil ls -p PROJECT_ID` works
- [ ] **Container API**: `gcloud container clusters list` works
- [ ] **Required APIs Enabled**: Check in Cloud Console or via gcloud

## 🔧 Automated Permission Setup Script

```bash
#!/bin/bash
# setup_permissions.sh

set -e

# Configuration
ORG_ID="${1:-$GCP_ORGANIZATION_ID}"
USER_EMAIL="${2:-$(gcloud config get-value account)}"

if [ -z "$ORG_ID" ]; then
    echo "Usage: $0 <ORG_ID> [USER_EMAIL]"
    echo "Or set GCP_ORGANIZATION_ID environment variable"
    exit 1
fi

echo "Setting up GCP Assessment permissions..."
echo "Organization: $ORG_ID"
echo "User: $USER_EMAIL"

# Core roles
ROLES=(
    "roles/compute.viewer"
    "roles/monitoring.viewer"
    "roles/resourcemanager.organizationViewer"
    "roles/browser"
    "roles/storage.objectViewer"
    "roles/container.viewer"
    "roles/dns.reader"
)

for ROLE in "${ROLES[@]}"; do
    echo "Granting $ROLE..."
    gcloud organizations add-iam-policy-binding $ORG_ID \
        --member="user:$USER_EMAIL" \
        --role="$ROLE" \
        --quiet
done

echo "Permission setup completed!"
echo "Run 'python3 validate_org_setup.py' to verify setup."
```

This permissions guide provides everything needed to properly configure access for the GCP assessment suite at any organizational level!
