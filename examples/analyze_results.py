#!/usr/bin/env python3
"""
Example: Analyze GCP Assessment Results
This script demonstrates how to analyze the CSV outputs from the GCP Assessment Suite.
"""

import pandas as pd
import glob
import json
from datetime import datetime

def load_assessment_data():
    """Load all assessment data files."""
    data = {}
    
    try:
        # Load compute data
        compute_files = glob.glob('gcp_compute_inventory_*.csv')
        if compute_files:
            data['compute'] = pd.read_csv(compute_files[0])
            print(f"✓ Loaded compute data: {len(data['compute'])} instances")
        
        # Load storage data
        storage_files = glob.glob('gcp_storage_usage_*.csv')
        if storage_files:
            data['storage'] = pd.read_csv(storage_files[0])
            print(f"✓ Loaded storage data: {len(data['storage'])} buckets")
        
        # Load GKE data
        gke_files = glob.glob('gcp_gke_clusters_*.csv')
        if gke_files:
            data['gke'] = pd.read_csv(gke_files[0])
            print(f"✓ Loaded GKE data: {len(data['gke'])} clusters")
        
        # Load networking data
        vpc_files = glob.glob('gcp_networking_vpcs_*.csv')
        if vpc_files:
            data['vpcs'] = pd.read_csv(vpc_files[0])
            print(f"✓ Loaded VPC data: {len(data['vpcs'])} VPCs")
            
    except Exception as e:
        print(f"Error loading data: {e}")
    
    return data

def generate_executive_summary(data):
    """Generate executive summary report."""
    print("\n" + "=" * 60)
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
        
        running_instances = len(compute_df[compute_df['status'] == 'RUNNING'])
        print(f"Running Instances: {running_instances:,}")
        
        if 'vcpus' in compute_df.columns:
            total_vcpus = compute_df['vcpus'].astype(str).str.replace('N/A', '0').astype(float).sum()
            print(f"Total vCPUs: {total_vcpus:,.0f}")
        
        if 'memory_gb' in compute_df.columns:
            total_memory = compute_df['memory_gb'].astype(str).str.replace('N/A', '0').astype(float).sum()
            print(f"Total Memory: {total_memory:,.1f} GB")
        
        if 'total_storage_gb' in compute_df.columns:
            total_storage = compute_df['total_storage_gb'].astype(str).str.replace('N/A', '0').astype(float).sum()
            print(f"Total Storage: {total_storage:,.1f} GB")
        
        print()
        
        # OS distribution
        if 'os_family' in compute_df.columns:
            print("Operating System Distribution:")
            os_dist = compute_df['os_family'].value_counts()
            for os_name, count in os_dist.head().items():
                if os_name != 'N/A':
                    print(f"  {os_name}: {count:,} instances")
            print()
    
    # Storage summary
    if 'storage' in data:
        storage_df = data['storage']
        print("STORAGE INFRASTRUCTURE")
        print("-" * 30)
        print(f"Total Buckets: {len(storage_df):,}")
        
        if 'total_size_tb' in storage_df.columns:
            total_storage_tb = storage_df['total_size_tb'].astype(str).str.replace('N/A', '0').astype(float).sum()
            print(f"Total Storage: {total_storage_tb:.2f} TB")
        
        if 'object_count' in storage_df.columns:
            total_objects = storage_df['object_count'].astype(str).str.replace('N/A', '0').astype(float).sum()
            print(f"Total Objects: {total_objects:,.0f}")
        
        print()
        
        # Storage by class
        if 'storage_class' in storage_df.columns:
            print("Storage by Class:")
            storage_by_class = storage_df.groupby('storage_class')['total_size_gb'].sum()
            for storage_class, size_gb in storage_by_class.items():
                if storage_class != 'N/A':
                    print(f"  {storage_class}: {size_gb:,.1f} GB")
            print()
    
    # GKE summary
    if 'gke' in data:
        gke_df = data['gke']
        print("KUBERNETES INFRASTRUCTURE")
        print("-" * 30)
        print(f"Total Clusters: {len(gke_df):,}")
        
        if 'node_count' in gke_df.columns:
            total_nodes = gke_df['node_count'].astype(str).str.replace('N/A', '0').astype(float).sum()
            print(f"Total Nodes: {total_nodes:,.0f}")
        
        if 'total_vcpus' in gke_df.columns:
            total_k8s_vcpus = gke_df['total_vcpus'].astype(str).str.replace('N/A', '0').astype(float).sum()
            print(f"Total K8s vCPUs: {total_k8s_vcpus:,.0f}")
        
        if 'total_memory_gb' in gke_df.columns:
            total_k8s_memory = gke_df['total_memory_gb'].astype(str).str.replace('N/A', '0').astype(float).sum()
            print(f"Total K8s Memory: {total_k8s_memory:,.1f} GB")
        
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
    
    opportunities = []
    
    if 'compute' in data:
        compute_df = data['compute']
        
        # High-cost storage
        if 'storage_types' in compute_df.columns:
            ssd_instances = compute_df[compute_df['storage_types'].str.contains('pd-ssd', na=False)]
            if len(ssd_instances) > 0:
                opportunities.append(f"• {len(ssd_instances)} instances using expensive SSD storage")
        
        # Preemptible opportunities
        if 'labels' in compute_df.columns and 'preemptible' in compute_df.columns:
            non_preemptible_dev = compute_df[
                (compute_df['labels'].str.contains('development', na=False)) & 
                (compute_df['preemptible'] == 'False')
            ]
            if len(non_preemptible_dev) > 0:
                opportunities.append(f"• {len(non_preemptible_dev)} development instances could be preemptible")
        
        # Deletion protection
        if 'labels' in compute_df.columns and 'deletion_protection' in compute_df.columns:
            unprotected_prod = compute_df[
                (compute_df['labels'].str.contains('production', na=False)) & 
                (compute_df['deletion_protection'] == 'False')
            ]
            if len(unprotected_prod) > 0:
                opportunities.append(f"• {len(unprotected_prod)} production instances lack deletion protection")
    
    if 'storage' in data:
        storage_df = data['storage']
        
        # Large buckets
        if 'total_size_gb' in storage_df.columns:
            large_buckets = storage_df[storage_df['total_size_gb'].astype(str).str.replace('N/A', '0').astype(float) > 1000]
            if len(large_buckets) > 0:
                opportunities.append(f"• {len(large_buckets)} buckets over 1TB may benefit from lifecycle policies")
    
    if opportunities:
        for opportunity in opportunities:
            print(opportunity)
    else:
        print("• No obvious optimization opportunities identified")
    
    print()

def generate_cost_analysis(data):
    """Generate cost analysis insights."""
    print("COST ANALYSIS INSIGHTS")
    print("=" * 30)
    
    if 'compute' in data:
        compute_df = data['compute']
        
        # Machine type distribution
        if 'machine_type' in compute_df.columns:
            print("Top Machine Types:")
            machine_types = compute_df['machine_type'].value_counts().head()
            for machine_type, count in machine_types.items():
                if machine_type != 'N/A':
                    print(f"  {machine_type}: {count} instances")
            print()
        
        # Regional distribution
        if 'region' in compute_df.columns:
            print("Regional Distribution:")
            regions = compute_df['region'].value_counts().head()
            for region, count in regions.items():
                if region != 'N/A':
                    print(f"  {region}: {count} instances")
            print()
    
    if 'storage' in data:
        storage_df = data['storage']
        
        # Storage class distribution
        if 'storage_class' in storage_df.columns:
            print("Storage Class Distribution:")
            storage_classes = storage_df['storage_class'].value_counts()
            for storage_class, count in storage_classes.items():
                if storage_class != 'N/A':
                    print(f"  {storage_class}: {count} buckets")
            print()

def main():
    """Main analysis function."""
    print("GCP Assessment Results Analysis")
    print("This script analyzes the CSV outputs from the GCP Assessment Suite")
    print()
    
    # Load data
    print("Loading assessment data...")
    data = load_assessment_data()
    
    if not data:
        print("No assessment data found. Please run the GCP assessment first.")
        print("Example: python3 gcp_master_assessment.py --org-id YOUR_ORG_ID")
        return
    
    # Generate reports
    generate_executive_summary(data)
    identify_optimization_opportunities(data)
    generate_cost_analysis(data)
    
    print("Analysis completed!")
    print("For more detailed analysis, consider using pandas, matplotlib, or other data analysis tools.")

if __name__ == "__main__":
    main()
