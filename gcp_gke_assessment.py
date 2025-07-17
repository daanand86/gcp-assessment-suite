#!/usr/bin/env python3
"""
Google Kubernetes Engine (GKE) Assessment Script
Assesses GKE clusters, node pools, workloads, and resource usage.
"""

import csv
import json
import subprocess
import sys
import os
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('gcp_gke_assessment.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class GCPGKEAssessor:
    def __init__(self, organization_id: Optional[str] = None, folder_id: Optional[str] = None, project_ids: Optional[List[str]] = None):
        self.organization_id = organization_id or os.getenv('GCP_ORGANIZATION_ID')
        self.folder_id = folder_id or os.getenv('GCP_FOLDER_ID')
        self.project_ids = project_ids or []
        self.max_workers = 10
        self.request_delay = 0.1

    def run_gcloud_command(self, command: List[str], timeout: int = 300) -> Dict[Any, Any]:
        """Execute gcloud command and return JSON output."""
        try:
            logger.debug(f"Executing: {' '.join(command)}")
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True,
                timeout=timeout
            )
            
            if result.stdout.strip():
                return json.loads(result.stdout)
            return {}
            
        except subprocess.TimeoutExpired:
            logger.error(f"Command timed out: {' '.join(command)}")
            return {}
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed: {' '.join(command)}")
            logger.error(f"Error: {e.stderr}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            return {}

    def get_projects(self) -> List[Dict[str, str]]:
        """Get projects based on specified scope."""
        projects = []
        
        if self.project_ids:
            for project_id in self.project_ids:
                command = ["gcloud", "projects", "describe", project_id, "--format=json"]
                project_data = self.run_gcloud_command(command)
                if project_data and project_data.get('lifecycleState') == 'ACTIVE':
                    projects.append({
                        'project_id': project_data['projectId'],
                        'name': project_data['name'],
                        'state': project_data['lifecycleState'],
                        'number': project_data['projectNumber']
                    })
        elif self.folder_id:
            command = [
                "gcloud", "projects", "list",
                f"--filter=parent.id={self.folder_id.replace('folders/', '')}",
                "--format=json"
            ]
            projects_data = self.run_gcloud_command(command)
            if projects_data:
                projects = [
                    {
                        'project_id': project['projectId'],
                        'name': project['name'],
                        'state': project['lifecycleState'],
                        'number': project['projectNumber']
                    }
                    for project in projects_data
                    if project.get('lifecycleState') == 'ACTIVE'
                ]
        elif self.organization_id:
            command = [
                "gcloud", "projects", "list",
                f"--filter=parent.id={self.organization_id}",
                "--format=json"
            ]
            projects_data = self.run_gcloud_command(command)
            if projects_data:
                projects = [
                    {
                        'project_id': project['projectId'],
                        'name': project['name'],
                        'state': project['lifecycleState'],
                        'number': project['projectNumber']
                    }
                    for project in projects_data
                    if project.get('lifecycleState') == 'ACTIVE'
                ]
        else:
            command = ["gcloud", "projects", "list", "--format=json"]
            projects_data = self.run_gcloud_command(command)
            if projects_data:
                projects = [
                    {
                        'project_id': project['projectId'],
                        'name': project['name'],
                        'state': project['lifecycleState'],
                        'number': project['projectNumber']
                    }
                    for project in projects_data
                    if project.get('lifecycleState') == 'ACTIVE'
                ]
        
        logger.info(f"Found {len(projects)} active projects for GKE assessment")
        return projects

    def assess_project_gke(self, project: Dict[str, str]) -> Dict[str, List]:
        """Assess GKE resources for a single project."""
        project_id = project['project_id']
        logger.info(f"Assessing GKE for project: {project_id}")
        
        gke_data = {
            'clusters': [],
            'node_pools': [],
            'workloads': []
        }
        
        try:
            # Get GKE clusters
            gke_data['clusters'] = self.get_gke_clusters(project_id, project)
            
            # Get node pools for each cluster
            for cluster in gke_data['clusters']:
                cluster_name = cluster['cluster_name']
                cluster_location = cluster['location']
                node_pools = self.get_cluster_node_pools(project_id, project, cluster_name, cluster_location)
                gke_data['node_pools'].extend(node_pools)
            
            # Get workloads for each cluster
            for cluster in gke_data['clusters']:
                cluster_name = cluster['cluster_name']
                cluster_location = cluster['location']
                workloads = self.get_cluster_workloads(project_id, project, cluster_name, cluster_location)
                gke_data['workloads'].extend(workloads)
            
        except Exception as e:
            logger.error(f"Error assessing GKE for project {project_id}: {e}")
        
        return gke_data

    def get_gke_clusters(self, project_id: str, project: Dict) -> List[Dict]:
        """Get GKE clusters for a project."""
        command = [
            "gcloud", "container", "clusters", "list",
            f"--project={project_id}",
            "--format=json"
        ]
        
        clusters = self.run_gcloud_command(command)
        cluster_data = []
        
        if clusters:
            for cluster in clusters:
                # Get additional cluster details
                cluster_name = cluster.get('name', 'N/A')
                location = cluster.get('location', 'N/A')
                
                cluster_details = self.get_cluster_details(project_id, cluster_name, location)
                
                cluster_info = {
                    'organization_id': self.organization_id or 'N/A',
                    'project_id': project_id,
                    'project_name': project['name'],
                    'cluster_name': cluster_name,
                    'location': location,
                    'location_type': cluster.get('locationType', 'N/A'),
                    'status': cluster.get('status', 'N/A'),
                    'kubernetes_version': cluster.get('currentMasterVersion', 'N/A'),
                    'node_version': cluster.get('currentNodeVersion', 'N/A'),
                    'node_count': str(cluster.get('currentNodeCount', 0)),
                    'machine_type': self.get_default_machine_type(cluster),
                    'disk_size_gb': str(cluster.get('nodeConfig', {}).get('diskSizeGb', 'N/A')),
                    'network': cluster.get('network', 'N/A'),
                    'subnetwork': cluster.get('subnetwork', 'N/A'),
                    'cluster_ipv4_cidr': cluster.get('clusterIpv4Cidr', 'N/A'),
                    'services_ipv4_cidr': cluster.get('servicesIpv4Cidr', 'N/A'),
                    'autopilot_enabled': str(cluster.get('autopilot', {}).get('enabled', False)),
                    'private_cluster': str(cluster.get('privateClusterConfig', {}).get('enablePrivateNodes', False)),
                    'master_authorized_networks': str(len(cluster.get('masterAuthorizedNetworksConfig', {}).get('cidrBlocks', []))),
                    'network_policy_enabled': str(cluster.get('networkPolicy', {}).get('enabled', False)),
                    'pod_security_policy_enabled': str(cluster.get('podSecurityPolicyConfig', {}).get('enabled', False)),
                    'workload_identity_enabled': str(cluster.get('workloadIdentityConfig', {}).get('workloadPool', '') != ''),
                    'binary_authorization_enabled': str(cluster.get('binaryAuthorization', {}).get('enabled', False)),
                    'shielded_nodes_enabled': str(cluster.get('shieldedNodes', {}).get('enabled', False)),
                    'release_channel': cluster.get('releaseChannel', {}).get('channel', 'N/A'),
                    'maintenance_window': json.dumps(cluster.get('maintenancePolicy', {})),
                    'addons_config': json.dumps(cluster.get('addonsConfig', {})),
                    'resource_labels': json.dumps(cluster.get('resourceLabels', {})),
                    'creation_time': cluster.get('createTime', 'N/A'),
                    'endpoint': cluster.get('endpoint', 'N/A'),
                    'initial_cluster_version': cluster.get('initialClusterVersion', 'N/A')
                }
                
                # Add cluster details
                cluster_info.update(cluster_details)
                cluster_data.append(cluster_info)
        
        time.sleep(self.request_delay)
        return cluster_data

    def get_default_machine_type(self, cluster: Dict) -> str:
        """Extract default machine type from cluster config."""
        node_pools = cluster.get('nodePools', [])
        if node_pools:
            return node_pools[0].get('config', {}).get('machineType', 'N/A')
        return cluster.get('nodeConfig', {}).get('machineType', 'N/A')

    def get_cluster_details(self, project_id: str, cluster_name: str, location: str) -> Dict:
        """Get additional cluster details."""
        command = [
            "gcloud", "container", "clusters", "describe", cluster_name,
            f"--location={location}",
            f"--project={project_id}",
            "--format=json"
        ]
        
        cluster_details = self.run_gcloud_command(command)
        
        details = {
            'total_vcpus': 'N/A',
            'total_memory_gb': 'N/A',
            'node_pools_count': 'N/A'
        }
        
        if cluster_details:
            # Calculate total resources
            total_vcpus = 0
            total_memory_gb = 0
            node_pools = cluster_details.get('nodePools', [])
            
            for pool in node_pools:
                node_count = pool.get('initialNodeCount', 0)
                machine_type = pool.get('config', {}).get('machineType', '')
                
                # Get machine type specs (simplified)
                vcpus, memory = self.get_machine_type_specs(machine_type)
                total_vcpus += vcpus * node_count
                total_memory_gb += memory * node_count
            
            details['total_vcpus'] = str(total_vcpus)
            details['total_memory_gb'] = str(total_memory_gb)
            details['node_pools_count'] = str(len(node_pools))
        
        return details

    def get_machine_type_specs(self, machine_type: str) -> tuple:
        """Get vCPUs and memory for a machine type (simplified mapping)."""
        # Simplified machine type mapping
        machine_specs = {
            'e2-micro': (1, 1),
            'e2-small': (1, 2),
            'e2-medium': (1, 4),
            'e2-standard-2': (2, 8),
            'e2-standard-4': (4, 16),
            'e2-standard-8': (8, 32),
            'n1-standard-1': (1, 3.75),
            'n1-standard-2': (2, 7.5),
            'n1-standard-4': (4, 15),
            'n1-standard-8': (8, 30),
            'n1-standard-16': (16, 60),
            'n2-standard-2': (2, 8),
            'n2-standard-4': (4, 16),
            'n2-standard-8': (8, 32),
            'n2-standard-16': (16, 64),
        }
        
        return machine_specs.get(machine_type, (0, 0))

    def get_cluster_node_pools(self, project_id: str, project: Dict, cluster_name: str, location: str) -> List[Dict]:
        """Get node pools for a specific cluster."""
        command = [
            "gcloud", "container", "node-pools", "list",
            f"--cluster={cluster_name}",
            f"--location={location}",
            f"--project={project_id}",
            "--format=json"
        ]
        
        node_pools = self.run_gcloud_command(command)
        node_pool_data = []
        
        if node_pools:
            for pool in node_pools:
                vcpus, memory = self.get_machine_type_specs(pool.get('config', {}).get('machineType', ''))
                node_count = pool.get('initialNodeCount', 0)
                
                pool_info = {
                    'organization_id': self.organization_id or 'N/A',
                    'project_id': project_id,
                    'project_name': project['name'],
                    'cluster_name': cluster_name,
                    'cluster_location': location,
                    'node_pool_name': pool.get('name', 'N/A'),
                    'status': pool.get('status', 'N/A'),
                    'node_count': str(node_count),
                    'machine_type': pool.get('config', {}).get('machineType', 'N/A'),
                    'disk_size_gb': str(pool.get('config', {}).get('diskSizeGb', 'N/A')),
                    'disk_type': pool.get('config', {}).get('diskType', 'N/A'),
                    'image_type': pool.get('config', {}).get('imageType', 'N/A'),
                    'vcpus_per_node': str(vcpus),
                    'memory_gb_per_node': str(memory),
                    'total_vcpus': str(vcpus * node_count),
                    'total_memory_gb': str(memory * node_count),
                    'preemptible': str(pool.get('config', {}).get('preemptible', False)),
                    'spot': str(pool.get('config', {}).get('spot', False)),
                    'autoscaling_enabled': str(pool.get('autoscaling', {}).get('enabled', False)),
                    'min_node_count': str(pool.get('autoscaling', {}).get('minNodeCount', 'N/A')),
                    'max_node_count': str(pool.get('autoscaling', {}).get('maxNodeCount', 'N/A')),
                    'auto_upgrade': str(pool.get('management', {}).get('autoUpgrade', False)),
                    'auto_repair': str(pool.get('management', {}).get('autoRepair', False)),
                    'node_version': pool.get('version', 'N/A'),
                    'locations': json.dumps(pool.get('locations', [])),
                    'network_tags': json.dumps(pool.get('config', {}).get('tags', [])),
                    'labels': json.dumps(pool.get('config', {}).get('labels', {})),
                    'taints': json.dumps(pool.get('config', {}).get('taints', [])),
                    'service_account': pool.get('config', {}).get('serviceAccount', 'N/A'),
                    'oauth_scopes': json.dumps(pool.get('config', {}).get('oauthScopes', []))
                }
                
                node_pool_data.append(pool_info)
        
        time.sleep(self.request_delay)
        return node_pool_data

    def get_cluster_workloads(self, project_id: str, project: Dict, cluster_name: str, location: str) -> List[Dict]:
        """Get workloads (deployments, services, etc.) for a specific cluster."""
        workload_data = []
        
        try:
            # Get cluster credentials first
            cred_command = [
                "gcloud", "container", "clusters", "get-credentials", cluster_name,
                f"--location={location}",
                f"--project={project_id}"
            ]
            
            subprocess.run(cred_command, capture_output=True, check=True)
            
            # Get deployments
            deployments = self.get_kubernetes_resources('deployments', cluster_name, location, project_id, project)
            workload_data.extend(deployments)
            
            # Get services
            services = self.get_kubernetes_resources('services', cluster_name, location, project_id, project)
            workload_data.extend(services)
            
            # Get pods summary
            pods = self.get_kubernetes_resources('pods', cluster_name, location, project_id, project)
            workload_data.extend(pods)
            
        except Exception as e:
            logger.warning(f"Could not get workloads for cluster {cluster_name}: {e}")
        
        return workload_data

    def get_kubernetes_resources(self, resource_type: str, cluster_name: str, location: str, project_id: str, project: Dict) -> List[Dict]:
        """Get Kubernetes resources using kubectl."""
        command = [
            "kubectl", "get", resource_type,
            "--all-namespaces",
            "-o", "json"
        ]
        
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            k8s_data = json.loads(result.stdout)
            
            resources = []
            for item in k8s_data.get('items', []):
                resource_info = {
                    'organization_id': self.organization_id or 'N/A',
                    'project_id': project_id,
                    'project_name': project['name'],
                    'cluster_name': cluster_name,
                    'cluster_location': location,
                    'resource_type': resource_type.rstrip('s'),  # Remove 's' for singular
                    'resource_name': item.get('metadata', {}).get('name', 'N/A'),
                    'namespace': item.get('metadata', {}).get('namespace', 'N/A'),
                    'creation_timestamp': item.get('metadata', {}).get('creationTimestamp', 'N/A'),
                    'labels': json.dumps(item.get('metadata', {}).get('labels', {})),
                    'annotations': json.dumps(item.get('metadata', {}).get('annotations', {}))
                }
                
                # Add resource-specific fields
                if resource_type == 'deployments':
                    spec = item.get('spec', {})
                    status = item.get('status', {})
                    resource_info.update({
                        'replicas': str(spec.get('replicas', 0)),
                        'ready_replicas': str(status.get('readyReplicas', 0)),
                        'available_replicas': str(status.get('availableReplicas', 0)),
                        'strategy_type': spec.get('strategy', {}).get('type', 'N/A')
                    })
                elif resource_type == 'services':
                    spec = item.get('spec', {})
                    resource_info.update({
                        'service_type': spec.get('type', 'N/A'),
                        'cluster_ip': spec.get('clusterIP', 'N/A'),
                        'external_ip': str(spec.get('externalIPs', [])),
                        'ports': json.dumps(spec.get('ports', []))
                    })
                elif resource_type == 'pods':
                    status = item.get('status', {})
                    spec = item.get('spec', {})
                    resource_info.update({
                        'phase': status.get('phase', 'N/A'),
                        'node_name': spec.get('nodeName', 'N/A'),
                        'restart_policy': spec.get('restartPolicy', 'N/A'),
                        'containers_count': str(len(spec.get('containers', [])))
                    })
                
                resources.append(resource_info)
            
            return resources
            
        except Exception as e:
            logger.debug(f"Could not get {resource_type} for cluster {cluster_name}: {e}")
            return []

    def export_gke_data(self, all_gke_data: Dict, base_filename: str):
        """Export GKE data to separate CSV files."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Export Clusters
        if all_gke_data['clusters']:
            clusters_filename = f"{base_filename}_clusters_{timestamp}.csv"
            cluster_fieldnames = [
                'organization_id', 'project_id', 'project_name', 'cluster_name', 'location',
                'location_type', 'status', 'kubernetes_version', 'node_version', 'node_count',
                'machine_type', 'disk_size_gb', 'network', 'subnetwork', 'cluster_ipv4_cidr',
                'services_ipv4_cidr', 'autopilot_enabled', 'private_cluster',
                'master_authorized_networks', 'network_policy_enabled', 'pod_security_policy_enabled',
                'workload_identity_enabled', 'binary_authorization_enabled', 'shielded_nodes_enabled',
                'release_channel', 'maintenance_window', 'addons_config', 'resource_labels',
                'creation_time', 'endpoint', 'initial_cluster_version', 'total_vcpus',
                'total_memory_gb', 'node_pools_count'
            ]
            self.write_csv(all_gke_data['clusters'], clusters_filename, cluster_fieldnames)
            logger.info(f"Exported {len(all_gke_data['clusters'])} clusters to {clusters_filename}")
        
        # Export Node Pools
        if all_gke_data['node_pools']:
            pools_filename = f"{base_filename}_node_pools_{timestamp}.csv"
            pool_fieldnames = [
                'organization_id', 'project_id', 'project_name', 'cluster_name', 'cluster_location',
                'node_pool_name', 'status', 'node_count', 'machine_type', 'disk_size_gb',
                'disk_type', 'image_type', 'vcpus_per_node', 'memory_gb_per_node',
                'total_vcpus', 'total_memory_gb', 'preemptible', 'spot', 'autoscaling_enabled',
                'min_node_count', 'max_node_count', 'auto_upgrade', 'auto_repair',
                'node_version', 'locations', 'network_tags', 'labels', 'taints',
                'service_account', 'oauth_scopes'
            ]
            self.write_csv(all_gke_data['node_pools'], pools_filename, pool_fieldnames)
            logger.info(f"Exported {len(all_gke_data['node_pools'])} node pools to {pools_filename}")
        
        # Export Workloads
        if all_gke_data['workloads']:
            workloads_filename = f"{base_filename}_workloads_{timestamp}.csv"
            # Use flexible fieldnames based on data structure
            if all_gke_data['workloads']:
                workload_fieldnames = list(all_gke_data['workloads'][0].keys())
                self.write_csv(all_gke_data['workloads'], workloads_filename, workload_fieldnames)
                logger.info(f"Exported {len(all_gke_data['workloads'])} workloads to {workloads_filename}")

    def write_csv(self, data: List[Dict], filename: str, fieldnames: List[str]):
        """Write data to CSV file."""
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)

    def run_assessment(self, base_filename: str = "gcp_gke", max_workers: int = 10):
        """Run the complete GKE assessment."""
        logger.info("Starting GCP GKE Assessment")
        
        projects = self.get_projects()
        if not projects:
            logger.error("No projects found or accessible")
            return False
        
        all_gke_data = {
            'clusters': [],
            'node_pools': [],
            'workloads': []
        }
        
        # Process projects in parallel
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_project = {
                executor.submit(self.assess_project_gke, project): project
                for project in projects
            }
            
            for future in as_completed(future_to_project):
                project = future_to_project[future]
                try:
                    project_gke = future.result()
                    
                    # Aggregate data
                    all_gke_data['clusters'].extend(project_gke['clusters'])
                    all_gke_data['node_pools'].extend(project_gke['node_pools'])
                    all_gke_data['workloads'].extend(project_gke['workloads'])
                    
                    logger.info(f"Completed GKE assessment for project {project['project_id']}")
                    
                except Exception as e:
                    logger.error(f"Error processing project {project['project_id']}: {e}")
        
        # Export results
        self.export_gke_data(all_gke_data, base_filename)
        
        # Calculate totals
        total_vcpus = sum(int(cluster.get('total_vcpus', 0)) for cluster in all_gke_data['clusters'] if cluster.get('total_vcpus', 'N/A') != 'N/A')
        total_memory = sum(float(cluster.get('total_memory_gb', 0)) for cluster in all_gke_data['clusters'] if cluster.get('total_memory_gb', 'N/A') != 'N/A')
        total_nodes = sum(int(cluster.get('node_count', 0)) for cluster in all_gke_data['clusters'])
        
        # Summary
        logger.info("="*60)
        logger.info("GKE ASSESSMENT COMPLETED")
        logger.info(f"Projects processed: {len(projects)}")
        logger.info(f"Total clusters found: {len(all_gke_data['clusters'])}")
        logger.info(f"Total node pools found: {len(all_gke_data['node_pools'])}")
        logger.info(f"Total workloads found: {len(all_gke_data['workloads'])}")
        logger.info(f"Total nodes: {total_nodes}")
        logger.info(f"Total vCPUs: {total_vcpus}")
        logger.info(f"Total memory: {total_memory:.2f} GB")
        logger.info("="*60)
        
        return True

def main():
    parser = argparse.ArgumentParser(description='GCP GKE Assessment Tool')
    
    scope_group = parser.add_mutually_exclusive_group()
    scope_group.add_argument('--org-id', help='Organization ID to assess')
    scope_group.add_argument('--folder-id', help='Folder ID to assess')
    scope_group.add_argument('--project-ids', help='Comma-separated list of project IDs')
    
    parser.add_argument('--output-prefix', default='gcp_gke', help='Output file prefix')
    parser.add_argument('--max-workers', type=int, default=10, help='Maximum parallel workers')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                       default='INFO', help='Logging level')
    
    args = parser.parse_args()
    
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    project_ids = None
    if args.project_ids:
        project_ids = [pid.strip() for pid in args.project_ids.split(',')]
    
    assessor = GCPGKEAssessor(
        organization_id=args.org_id,
        folder_id=args.folder_id,
        project_ids=project_ids
    )
    
    success = assessor.run_assessment(
        base_filename=args.output_prefix,
        max_workers=args.max_workers
    )
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
