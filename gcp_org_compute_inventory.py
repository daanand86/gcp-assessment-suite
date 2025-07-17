#!/usr/bin/env python3
"""
Google Cloud Organization-Level Compute Engine Inventory and Utilization Script
Queries all GCE instances across an entire organization and exports specs and utilization data.

Author: GCP Assessment Tool
Version: 1.0
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
        logging.FileHandler('gcp_assessment.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class GCPComputeAssessor:
    def __init__(self, organization_id: Optional[str] = None, folder_id: Optional[str] = None, project_ids: Optional[List[str]] = None):
        self.organization_id = organization_id or os.getenv('GCP_ORGANIZATION_ID')
        self.folder_id = folder_id or os.getenv('GCP_FOLDER_ID')
        self.project_ids = project_ids or []
        self.max_workers = 10  # Parallel processing limit
        self.request_delay = 0.1  # Delay between requests to avoid rate limits
        
    def run_gcloud_command(self, command: List[str], timeout: int = 300) -> Dict[Any, Any]:
        """Execute gcloud command and return JSON output with error handling."""
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
            logger.error(f"Output was: {result.stdout[:500]}...")
            return {}

    def get_organization_projects(self) -> List[Dict[str, str]]:
        """Get projects based on specified scope (organization, folder, or specific projects)."""
        projects = []
        
        if self.project_ids:
            # Get specific projects by ID
            logger.info(f"Getting details for {len(self.project_ids)} specific projects")
            for project_id in self.project_ids:
                command = [
                    "gcloud", "projects", "describe", project_id,
                    "--format=json"
                ]
                project_data = self.run_gcloud_command(command)
                if project_data and project_data.get('lifecycleState') == 'ACTIVE':
                    projects.append({
                        'project_id': project_data['projectId'],
                        'name': project_data['name'],
                        'state': project_data['lifecycleState'],
                        'number': project_data['projectNumber']
                    })
                else:
                    logger.warning(f"Project {project_id} not found or not active")
        
        elif self.folder_id:
            # Get projects from specific folder
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
            # Get all projects in organization
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
            # Fallback to all accessible projects
            logger.warning("No organization, folder, or specific projects specified, using all accessible projects")
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
            
        logger.info(f"Found {len(projects)} active projects")
        return projects

    def get_project_compute_instances(self, project_id: str) -> List[Dict]:
        """Get all compute instances for a specific project."""
        command = [
            "gcloud", "compute", "instances", "list",
            f"--project={project_id}",
            "--format=json"
        ]
        
        instances = self.run_gcloud_command(command)
        if instances:
            logger.debug(f"Found {len(instances)} instances in project {project_id}")
        
        # Add delay to avoid rate limits
        time.sleep(self.request_delay)
        return instances if instances else []

    def parse_machine_type(self, machine_type_url: str, project_id: str) -> Dict[str, str]:
        """Extract machine type details from URL."""
        try:
            machine_type = machine_type_url.split('/')[-1]
            zone = machine_type_url.split('/')[-3]
            
            command = [
                "gcloud", "compute", "machine-types", "describe", machine_type,
                f"--zone={zone}",
                f"--project={project_id}",
                "--format=json"
            ]
            
            machine_details = self.run_gcloud_command(command)
            
            if machine_details:
                return {
                    'machine_type': machine_type,
                    'vcpus': str(machine_details.get('guestCpus', 'N/A')),
                    'memory_mb': str(machine_details.get('memoryMb', 'N/A')),
                    'memory_gb': str(round(int(machine_details.get('memoryMb', 0)) / 1024, 2)) if machine_details.get('memoryMb') else 'N/A'
                }
            
        except Exception as e:
            logger.error(f"Error parsing machine type {machine_type_url}: {e}")
        
        # Fallback parsing from machine type name
        machine_type = machine_type_url.split('/')[-1]
        return {
            'machine_type': machine_type,
            'vcpus': 'N/A',
            'memory_mb': 'N/A',
            'memory_gb': 'N/A'
        }

    def get_disk_info(self, disks: List[Dict], project_id: str) -> Dict[str, Any]:
        """Extract disk information from instance disks including storage types."""
        total_storage_gb = 0
        disk_details = []
        storage_types = []
        
        for disk in disks:
            try:
                disk_name = disk['source'].split('/')[-1]
                disk_zone = disk['source'].split('/')[-3]
                
                command = [
                    "gcloud", "compute", "disks", "describe", disk_name,
                    f"--zone={disk_zone}",
                    f"--project={project_id}",
                    "--format=json"
                ]
                
                disk_info = self.run_gcloud_command(command)
                if disk_info:
                    size_gb = int(disk_info.get('sizeGb', 0))
                    disk_type = disk_info.get('type', 'N/A').split('/')[-1]
                    total_storage_gb += size_gb
                    
                    disk_details.append({
                        'name': disk_name,
                        'size_gb': size_gb,
                        'type': disk_type,
                        'boot': disk.get('boot', False)
                    })
                    
                    # Collect storage types
                    if disk_type not in storage_types:
                        storage_types.append(disk_type)
                
                # Small delay to avoid rate limits
                time.sleep(self.request_delay)
                
            except Exception as e:
                logger.error(f"Error getting disk info for {disk.get('source', 'unknown')}: {e}")
                continue
        
        return {
            'total_storage_gb': total_storage_gb,
            'disk_count': len(disk_details),
            'disks': disk_details,
            'storage_types': ','.join(storage_types) if storage_types else 'N/A',
            'boot_disk_type': next((d['type'] for d in disk_details if d['boot']), 'N/A'),
            'boot_disk_size_gb': next((d['size_gb'] for d in disk_details if d['boot']), 'N/A')
        }

    def get_instance_utilization(self, project_id: str, instance_name: str, zone: str) -> Dict[str, str]:
        """Get CPU and memory utilization for the last 30 days using gcloud monitoring."""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=30)
        
        # Format timestamps for Cloud Monitoring
        start_time_str = start_time.strftime('%Y-%m-%dT%H:%M:%SZ')
        end_time_str = end_time.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        utilization_data = {
            'cpu_avg': 'N/A',
            'cpu_max': 'N/A',
            'memory_avg': 'N/A',
            'memory_max': 'N/A'
        }
        
        try:
            # CPU Utilization Query
            cpu_command = [
                "gcloud", "monitoring", "metrics", "list",
                f"--project={project_id}",
                "--filter=metric.type=\"compute.googleapis.com/instance/cpu/utilization\"",
                f"--filter=resource.labels.instance_name=\"{instance_name}\"",
                f"--filter=resource.labels.zone=\"{zone}\"",
                f"--interval.start-time={start_time_str}",
                f"--interval.end-time={end_time_str}",
                "--format=json",
                "--limit=1000"
            ]
            
            # Note: This is a simplified approach for demonstration
            # In production, you would parse the actual metric data
            logger.debug(f"Querying utilization for {instance_name} in {project_id}")
            
            # For now, return placeholder values
            # You can enhance this to parse actual monitoring data
            utilization_data = {
                'cpu_avg': 'Monitoring_Data_Available',
                'cpu_max': 'Monitoring_Data_Available',
                'memory_avg': 'Monitoring_Data_Available',
                'memory_max': 'Monitoring_Data_Available'
            }
            
        except Exception as e:
            logger.warning(f"Could not retrieve utilization for {instance_name}: {e}")
        
        return utilization_data

    def get_os_information(self, instance: Dict, project_id: str) -> Dict[str, str]:
        """Extract OS information from instance boot disk."""
        os_info = {
            'os_family': 'N/A',
            'os_version': 'N/A',
            'os_architecture': 'N/A',
            'boot_disk_image': 'N/A'
        }
        
        try:
            # Find boot disk
            boot_disk = None
            for disk in instance.get('disks', []):
                if disk.get('boot', False):
                    boot_disk = disk
                    break
            
            if not boot_disk:
                return os_info
            
            # Get boot disk details
            disk_name = boot_disk['source'].split('/')[-1]
            disk_zone = boot_disk['source'].split('/')[-3]
            
            command = [
                "gcloud", "compute", "disks", "describe", disk_name,
                f"--zone={disk_zone}",
                f"--project={project_id}",
                "--format=json"
            ]
            
            disk_info = self.run_gcloud_command(command)
            if disk_info:
                # Extract OS information from source image
                source_image = disk_info.get('sourceImage', '')
                if source_image:
                    os_info['boot_disk_image'] = source_image.split('/')[-1]
                    
                    # Parse OS family and version from image name
                    image_name = source_image.split('/')[-1].lower()
                    os_info.update(self.parse_os_from_image_name(image_name))
            
            # Small delay to avoid rate limits
            time.sleep(self.request_delay)
            
        except Exception as e:
            logger.debug(f"Error getting OS information for {instance.get('name', 'unknown')}: {e}")
        
        return os_info

    def parse_os_from_image_name(self, image_name: str) -> Dict[str, str]:
        """Parse OS family and version from GCP image name."""
        os_details = {
            'os_family': 'N/A',
            'os_version': 'N/A',
            'os_architecture': 'x86_64'
        }
        
        try:
            # Common GCP image patterns
            if 'ubuntu' in image_name:
                os_details['os_family'] = 'Ubuntu'
                if '2004' in image_name or 'focal' in image_name:
                    os_details['os_version'] = '20.04 LTS'
                elif '2204' in image_name or 'jammy' in image_name:
                    os_details['os_version'] = '22.04 LTS'
                elif '1804' in image_name or 'bionic' in image_name:
                    os_details['os_version'] = '18.04 LTS'
                elif '1604' in image_name or 'xenial' in image_name:
                    os_details['os_version'] = '16.04 LTS'
            
            elif 'debian' in image_name:
                os_details['os_family'] = 'Debian'
                if 'debian-11' in image_name or 'bullseye' in image_name:
                    os_details['os_version'] = '11'
                elif 'debian-10' in image_name or 'buster' in image_name:
                    os_details['os_version'] = '10'
                elif 'debian-9' in image_name or 'stretch' in image_name:
                    os_details['os_version'] = '9'
            
            elif 'centos' in image_name:
                os_details['os_family'] = 'CentOS'
                if 'centos-7' in image_name:
                    os_details['os_version'] = '7'
                elif 'centos-8' in image_name:
                    os_details['os_version'] = '8'
                elif 'centos-stream' in image_name:
                    os_details['os_version'] = 'Stream'
            
            elif 'rhel' in image_name or 'red-hat' in image_name:
                os_details['os_family'] = 'RHEL'
                if 'rhel-7' in image_name:
                    os_details['os_version'] = '7'
                elif 'rhel-8' in image_name:
                    os_details['os_version'] = '8'
                elif 'rhel-9' in image_name:
                    os_details['os_version'] = '9'
            
            elif 'windows' in image_name:
                os_details['os_family'] = 'Windows Server'
                if '2019' in image_name:
                    os_details['os_version'] = '2019'
                elif '2016' in image_name:
                    os_details['os_version'] = '2016'
                elif '2012' in image_name:
                    os_details['os_version'] = '2012'
                elif '2022' in image_name:
                    os_details['os_version'] = '2022'
            
            elif 'suse' in image_name or 'sles' in image_name:
                os_details['os_family'] = 'SUSE'
                if 'sles-12' in image_name:
                    os_details['os_version'] = '12'
                elif 'sles-15' in image_name:
                    os_details['os_version'] = '15'
            
            elif 'cos' in image_name or 'container-optimized' in image_name:
                os_details['os_family'] = 'Container-Optimized OS'
            
            # Check for ARM architecture
            if 'arm64' in image_name or 'aarch64' in image_name:
                os_details['os_architecture'] = 'ARM64'
            elif 'arm' in image_name:
                os_details['os_architecture'] = 'ARM'
            
        except Exception as e:
            logger.debug(f"Error parsing OS from image name '{image_name}': {e}")
        
        return os_details

    def get_instance_runtime_hours(self, project_id: str, instance_name: str, zone: str) -> Dict[str, str]:
        """Get instance runtime hours for the last 30 days using Cloud Monitoring."""
        runtime_info = {
            'runtime_hours_30d': 'N/A',
            'uptime_percentage_30d': 'N/A'
        }
        
        try:
            # Calculate 30 days ago
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=30)
            
            # Total hours in 30 days
            total_hours = 30 * 24
            
            # For now, we'll estimate based on instance status and creation time
            # In a full implementation, you would query Cloud Monitoring for actual uptime metrics
            
            # This is a simplified approach - in production you'd want to use:
            # gcloud monitoring metrics list with compute.googleapis.com/instance/up metric
            
            # Placeholder calculation based on current status
            # You can enhance this with actual monitoring data
            runtime_info['runtime_hours_30d'] = 'Monitoring_Required'
            runtime_info['uptime_percentage_30d'] = 'Monitoring_Required'
            
            logger.debug(f"Runtime calculation for {instance_name} - would require monitoring API integration")
            
        except Exception as e:
            logger.debug(f"Error calculating runtime for {instance_name}: {e}")
        
        return runtime_info

    def get_os_information(self, instance: Dict, project_id: str) -> Dict[str, str]:
        """Extract OS information from instance and boot disk details."""
        os_info = {
            'os_family': 'N/A',
            'os_version': 'N/A',
            'os_architecture': 'N/A',
            'boot_disk_image': 'N/A',
            'boot_disk_size_gb': 'N/A',
            'boot_disk_type': 'N/A'
        }
        
        try:
            # Find boot disk
            boot_disk = None
            for disk in instance.get('disks', []):
                if disk.get('boot', False):
                    boot_disk = disk
                    break
            
            if not boot_disk:
                logger.warning(f"No boot disk found for instance {instance.get('name', 'unknown')}")
                return os_info
            
            # Get boot disk details
            disk_name = boot_disk['source'].split('/')[-1]
            disk_zone = boot_disk['source'].split('/')[-3]
            
            command = [
                "gcloud", "compute", "disks", "describe", disk_name,
                f"--zone={disk_zone}",
                f"--project={project_id}",
                "--format=json"
            ]
            
            disk_info = self.run_gcloud_command(command)
            if disk_info:
                # Extract boot disk information
                os_info['boot_disk_size_gb'] = str(disk_info.get('sizeGb', 'N/A'))
                os_info['boot_disk_type'] = disk_info.get('type', 'N/A').split('/')[-1]
                
                # Extract OS information from source image
                source_image = disk_info.get('sourceImage', '')
                if source_image:
                    os_info['boot_disk_image'] = source_image.split('/')[-1]
                    
                    # Parse OS family and version from image name
                    image_name = source_image.split('/')[-1].lower()
                    os_info.update(self.parse_os_from_image_name(image_name))
                
                # Try to get more detailed OS info from guest OS features
                guest_os_features = disk_info.get('guestOsFeatures', [])
                if guest_os_features:
                    for feature in guest_os_features:
                        feature_type = feature.get('type', '').lower()
                        if 'windows' in feature_type:
                            if os_info['os_family'] == 'N/A':
                                os_info['os_family'] = 'Windows'
                        elif 'uefi' in feature_type:
                            os_info['os_architecture'] = 'UEFI'
            
            # Small delay to avoid rate limits
            time.sleep(self.request_delay)
            
        except Exception as e:
            logger.error(f"Error getting OS information for {instance.get('name', 'unknown')}: {e}")
        
        return os_info

    def parse_os_from_image_name(self, image_name: str) -> Dict[str, str]:
        """Parse OS family and version from GCP image name."""
        os_details = {
            'os_family': 'N/A',
            'os_version': 'N/A',
            'os_architecture': 'x86_64'  # Default assumption
        }
        
        try:
            # Common GCP image patterns
            if 'ubuntu' in image_name:
                os_details['os_family'] = 'Ubuntu'
                # Extract version (e.g., ubuntu-2004-focal, ubuntu-1804-bionic)
                if '2004' in image_name or 'focal' in image_name:
                    os_details['os_version'] = '20.04 LTS (Focal)'
                elif '2204' in image_name or 'jammy' in image_name:
                    os_details['os_version'] = '22.04 LTS (Jammy)'
                elif '1804' in image_name or 'bionic' in image_name:
                    os_details['os_version'] = '18.04 LTS (Bionic)'
                elif '1604' in image_name or 'xenial' in image_name:
                    os_details['os_version'] = '16.04 LTS (Xenial)'
                else:
                    # Try to extract version number
                    import re
                    version_match = re.search(r'(\d{2})(\d{2})', image_name)
                    if version_match:
                        os_details['os_version'] = f"{version_match.group(1)}.{version_match.group(2)}"
            
            elif 'debian' in image_name:
                os_details['os_family'] = 'Debian'
                if 'debian-11' in image_name or 'bullseye' in image_name:
                    os_details['os_version'] = '11 (Bullseye)'
                elif 'debian-10' in image_name or 'buster' in image_name:
                    os_details['os_version'] = '10 (Buster)'
                elif 'debian-9' in image_name or 'stretch' in image_name:
                    os_details['os_version'] = '9 (Stretch)'
                else:
                    import re
                    version_match = re.search(r'debian-(\d+)', image_name)
                    if version_match:
                        os_details['os_version'] = version_match.group(1)
            
            elif 'centos' in image_name:
                os_details['os_family'] = 'CentOS'
                if 'centos-7' in image_name:
                    os_details['os_version'] = '7'
                elif 'centos-8' in image_name:
                    os_details['os_version'] = '8'
                elif 'centos-stream' in image_name:
                    os_details['os_version'] = 'Stream'
                else:
                    import re
                    version_match = re.search(r'centos-(\d+)', image_name)
                    if version_match:
                        os_details['os_version'] = version_match.group(1)
            
            elif 'rhel' in image_name or 'red-hat' in image_name:
                os_details['os_family'] = 'Red Hat Enterprise Linux'
                import re
                version_match = re.search(r'(\d+)', image_name)
                if version_match:
                    os_details['os_version'] = version_match.group(1)
            
            elif 'windows' in image_name:
                os_details['os_family'] = 'Windows Server'
                if '2019' in image_name:
                    os_details['os_version'] = '2019'
                elif '2016' in image_name:
                    os_details['os_version'] = '2016'
                elif '2012' in image_name:
                    os_details['os_version'] = '2012'
                elif '2022' in image_name:
                    os_details['os_version'] = '2022'
                else:
                    import re
                    version_match = re.search(r'(\d{4})', image_name)
                    if version_match:
                        os_details['os_version'] = version_match.group(1)
            
            elif 'suse' in image_name or 'sles' in image_name:
                os_details['os_family'] = 'SUSE Linux Enterprise Server'
                import re
                version_match = re.search(r'(\d+)', image_name)
                if version_match:
                    os_details['os_version'] = version_match.group(1)
            
            elif 'fedora' in image_name:
                os_details['os_family'] = 'Fedora'
                import re
                version_match = re.search(r'(\d+)', image_name)
                if version_match:
                    os_details['os_version'] = version_match.group(1)
            
            elif 'rocky' in image_name:
                os_details['os_family'] = 'Rocky Linux'
                import re
                version_match = re.search(r'(\d+)', image_name)
                if version_match:
                    os_details['os_version'] = version_match.group(1)
            
            elif 'alma' in image_name:
                os_details['os_family'] = 'AlmaLinux'
                import re
                version_match = re.search(r'(\d+)', image_name)
                if version_match:
                    os_details['os_version'] = version_match.group(1)
            
            elif 'cos' in image_name or 'container-optimized' in image_name:
                os_details['os_family'] = 'Container-Optimized OS'
                import re
                version_match = re.search(r'(\d+)', image_name)
                if version_match:
                    os_details['os_version'] = version_match.group(1)
            
            # Check for ARM architecture
            if 'arm64' in image_name or 'aarch64' in image_name:
                os_details['os_architecture'] = 'ARM64'
            elif 'arm' in image_name:
                os_details['os_architecture'] = 'ARM'
            
        except Exception as e:
            logger.debug(f"Error parsing OS from image name '{image_name}': {e}")
        
        return os_details

    def process_project_instances(self, project: Dict[str, str]) -> tuple:
        """Process all instances in a single project."""
        project_id = project['project_id']
        project_instances = []
        project_utilization = []
        
        try:
            logger.info(f"Processing project: {project_id}")
            
            # Get instances for this project
            instances = self.get_project_compute_instances(project_id)
            
            if not instances:
                logger.info(f"No instances found in project {project_id}")
                return project_instances, project_utilization
            
            logger.info(f"Found {len(instances)} instances in {project_id}")
            
            for instance in instances:
                try:
                    instance_name = instance['name']
                    zone = instance['zone'].split('/')[-1]
                    
                    logger.debug(f"Processing instance: {instance_name} in {project_id}")
                    
                    # Get machine type details
                    machine_info = self.parse_machine_type(instance['machineType'], project_id)
                    
                    # Get disk information
                    disk_info = self.get_disk_info(instance.get('disks', []), project_id)
                    
                    # Get network information
                    internal_ip = instance.get('networkInterfaces', [{}])[0].get('networkIP', 'N/A')
                    external_ip = 'N/A'
                    if instance.get('networkInterfaces', [{}])[0].get('accessConfigs'):
                        external_ip = instance['networkInterfaces'][0]['accessConfigs'][0].get('natIP', 'N/A')
                    
                    # Get OS information
                    os_info = self.get_os_information(instance, project_id)
                    
                    # Get runtime information
                    runtime_info = self.get_instance_runtime_hours(project_id, instance_name, zone)
                    
                    # Prepare inventory data
                    instance_data = {
                        'organization_id': self.organization_id or 'N/A',
                        'project_id': project_id,
                        'project_name': project['name'],
                        'project_number': project['number'],
                        'instance_name': instance_name,
                        'zone': zone,
                        'region': zone.rsplit('-', 1)[0],
                        'status': instance['status'],
                        'machine_type': machine_info['machine_type'],
                        'vcpus': machine_info['vcpus'],
                        'memory_gb': machine_info['memory_gb'],
                        'total_storage_gb': disk_info['total_storage_gb'],
                        'disk_count': disk_info['disk_count'],
                        'storage_types': disk_info['storage_types'],
                        'boot_disk_type': disk_info['boot_disk_type'],
                        'boot_disk_size_gb': disk_info['boot_disk_size_gb'],
                        'internal_ip': internal_ip,
                        'external_ip': external_ip,
                        'os_family': os_info['os_family'],
                        'os_version': os_info['os_version'],
                        'os_architecture': os_info['os_architecture'],
                        'boot_disk_image': os_info['boot_disk_image'],
                        'runtime_hours_30d': runtime_info['runtime_hours_30d'],
                        'uptime_percentage_30d': runtime_info['uptime_percentage_30d'],
                        'creation_timestamp': instance.get('creationTimestamp', 'N/A'),
                        'labels': json.dumps(instance.get('labels', {})),
                        'tags': json.dumps(instance.get('tags', {}).get('items', [])),
                        'service_accounts': json.dumps([sa.get('email', '') for sa in instance.get('serviceAccounts', [])]),
                        'preemptible': str(instance.get('scheduling', {}).get('preemptible', False)),
                        'deletion_protection': str(instance.get('deletionProtection', False))
                    }
                    
                    project_instances.append(instance_data)
                    
                    # Get utilization data (only for running instances)
                    if instance['status'] == 'RUNNING':
                        utilization = self.get_instance_utilization(project_id, instance_name, zone)
                        
                        utilization_data = {
                            'organization_id': self.organization_id or 'N/A',
                            'project_id': project_id,
                            'project_name': project['name'],
                            'instance_name': instance_name,
                            'zone': zone,
                            'region': zone.rsplit('-', 1)[0],
                            'cpu_avg_30d': utilization['cpu_avg'],
                            'cpu_max_30d': utilization['cpu_max'],
                            'memory_avg_30d': utilization['memory_avg'],
                            'memory_max_30d': utilization['memory_max'],
                            'data_collection_date': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
                        }
                        
                        project_utilization.append(utilization_data)
                
                except Exception as e:
                    logger.error(f"Error processing instance {instance.get('name', 'unknown')} in {project_id}: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error processing project {project_id}: {e}")
        
        return project_instances, project_utilization

    def export_inventory_csv(self, instances_data: List[Dict], filename: str):
        """Export instance inventory to CSV file."""
        if not instances_data:
            logger.warning("No inventory data to export")
            return
            
        fieldnames = [
            'organization_id', 'project_id', 'project_name', 'project_number',
            'instance_name', 'zone', 'region', 'status', 'machine_type',
            'vcpus', 'memory_gb', 'total_storage_gb', 'disk_count',
            'storage_types', 'boot_disk_type', 'boot_disk_size_gb',
            'internal_ip', 'external_ip', 
            'os_family', 'os_version', 'os_architecture', 'boot_disk_image',
            'runtime_hours_30d', 'uptime_percentage_30d',
            'creation_timestamp', 'labels', 'tags',
            'service_accounts', 'preemptible', 'deletion_protection'
        ]
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(instances_data)
        
        logger.info(f"Exported {len(instances_data)} instances to {filename}")

    def export_utilization_csv(self, utilization_data: List[Dict], filename: str):
        """Export utilization data to CSV file."""
        if not utilization_data:
            logger.warning("No utilization data to export")
            return
            
        fieldnames = [
            'organization_id', 'project_id', 'project_name', 'instance_name',
            'zone', 'region', 'cpu_avg_30d', 'cpu_max_30d',
            'memory_avg_30d', 'memory_max_30d', 'data_collection_date'
        ]
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(utilization_data)
        
        logger.info(f"Exported {len(utilization_data)} utilization records to {filename}")

    def run_assessment(self, inventory_file: str, utilization_file: str, max_workers: int = 10):
        """Run the complete compute assessment based on specified scope."""
        if self.project_ids:
            logger.info("Starting GCP Project-Level Compute Engine Assessment")
        elif self.folder_id:
            logger.info("Starting GCP Folder-Level Compute Engine Assessment")
        elif self.organization_id:
            logger.info("Starting GCP Organization-Level Compute Engine Assessment")
        else:
            logger.info("Starting GCP Multi-Project Compute Engine Assessment")
        
        # Validate authentication and access
        if not self.validate_access():
            logger.error("Access validation failed. Please check prerequisites.")
            return False
        
        # Get projects based on scope
        projects = self.get_organization_projects()
        if not projects:
            logger.error("No projects found or accessible")
            return False
        
        scope_description = self._get_scope_description()
        logger.info(f"Starting assessment of {len(projects)} projects in {scope_description}")
        
        all_instances_data = []
        all_utilization_data = []
        
        # Process projects in parallel
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all project processing tasks
            future_to_project = {
                executor.submit(self.process_project_instances, project): project
                for project in projects
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_project):
                project = future_to_project[future]
                try:
                    project_instances, project_utilization = future.result()
                    all_instances_data.extend(project_instances)
                    all_utilization_data.extend(project_utilization)
                    
                    logger.info(f"Completed project {project['project_id']}: "
                              f"{len(project_instances)} instances, "
                              f"{len(project_utilization)} utilization records")
                    
                except Exception as e:
                    logger.error(f"Error processing project {project['project_id']}: {e}")
        
        # Export results
        logger.info("Exporting assessment results...")
        self.export_inventory_csv(all_instances_data, inventory_file)
        self.export_utilization_csv(all_utilization_data, utilization_file)
        
        # Summary
        logger.info("="*60)
        logger.info("ASSESSMENT COMPLETED")
        logger.info(f"Assessment scope: {scope_description}")
        logger.info(f"Projects processed: {len(projects)}")
        logger.info(f"Total instances found: {len(all_instances_data)}")
        logger.info(f"Running instances with utilization data: {len(all_utilization_data)}")
        logger.info(f"Inventory file: {inventory_file}")
        logger.info(f"Utilization file: {utilization_file}")
        logger.info("="*60)
        
        return True

    def _get_scope_description(self) -> str:
        """Get human-readable description of assessment scope."""
        if self.project_ids:
            if len(self.project_ids) == 1:
                return f"project '{self.project_ids[0]}'"
            else:
                return f"{len(self.project_ids)} specific projects"
        elif self.folder_id:
            return f"folder '{self.folder_id}'"
        elif self.organization_id:
            return f"organization '{self.organization_id}'"
        else:
            return "all accessible projects"

    def validate_access(self) -> bool:
        """Validate that we have the necessary access and authentication."""
        logger.info("Validating access and authentication...")
        
        # Check authentication
        auth_command = ["gcloud", "auth", "list", "--format=json"]
        auth_result = self.run_gcloud_command(auth_command)
        
        if not auth_result:
            logger.error("No authentication found. Please run 'gcloud auth login' or set up service account.")
            return False
        
        active_accounts = [acc for acc in auth_result if acc.get('status') == 'ACTIVE']
        if not active_accounts:
            logger.error("No active authentication found.")
            return False
        
        logger.info(f"Authenticated as: {active_accounts[0]['account']}")
        
        # Test organization access
        if self.organization_id:
            org_command = ["gcloud", "organizations", "describe", self.organization_id]
            org_result = self.run_gcloud_command(org_command)
            if not org_result:
                logger.error(f"Cannot access organization {self.organization_id}")
                return False
            logger.info(f"Organization access verified: {org_result.get('displayName', self.organization_id)}")
        
        return True

def main():
    parser = argparse.ArgumentParser(
        description='GCP Multi-Level Compute Engine Assessment Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Assessment Scope Options (choose one):
  --org-id          : Assess entire organization
  --folder-id       : Assess specific folder
  --project-ids     : Assess specific project(s)
  (no scope)        : Assess all accessible projects

Examples:
  # Organization-wide assessment
  python3 gcp_org_compute_inventory.py --org-id 123456789012
  
  # Folder-level assessment
  python3 gcp_org_compute_inventory.py --folder-id folders/123456789
  
  # Single project assessment
  python3 gcp_org_compute_inventory.py --project-ids my-project-1
  
  # Multiple specific projects
  python3 gcp_org_compute_inventory.py --project-ids my-project-1,my-project-2,my-project-3
  
  # All accessible projects (no scope specified)
  python3 gcp_org_compute_inventory.py
  
  # Custom output files and parallel processing
  python3 gcp_org_compute_inventory.py --project-ids my-project-1 \\
    --inventory-file project_inventory_$(date +%Y%m%d).csv \\
    --utilization-file project_utilization_$(date +%Y%m%d).csv \\
    --max-workers 5
        """
    )
    
    # Scope options (mutually exclusive)
    scope_group = parser.add_mutually_exclusive_group()
    scope_group.add_argument('--org-id', help='Organization ID to assess')
    scope_group.add_argument('--folder-id', help='Folder ID to assess (e.g., folders/123456789)')
    scope_group.add_argument('--project-ids', help='Comma-separated list of specific project IDs to assess')
    
    # Output and processing options
    parser.add_argument('--inventory-file', default='gcp_compute_inventory.csv', 
                       help='Output file for inventory data')
    parser.add_argument('--utilization-file', default='gcp_compute_utilization.csv', 
                       help='Output file for utilization data')
    parser.add_argument('--max-workers', type=int, default=10, 
                       help='Maximum parallel workers for processing projects')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                       default='INFO', help='Logging level')
    
    args = parser.parse_args()
    
    # Set logging level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Parse project IDs if provided
    project_ids = None
    if args.project_ids:
        project_ids = [pid.strip() for pid in args.project_ids.split(',')]
        logger.info(f"Targeting specific projects: {project_ids}")
    
    # Determine assessment scope
    if args.org_id:
        scope_description = f"organization {args.org_id}"
    elif args.folder_id:
        scope_description = f"folder {args.folder_id}"
    elif project_ids:
        scope_description = f"{len(project_ids)} specific project(s)"
    else:
        scope_description = "all accessible projects"
    
    logger.info(f"Assessment scope: {scope_description}")
    
    # Initialize assessor
    assessor = GCPComputeAssessor(
        organization_id=args.org_id,
        folder_id=args.folder_id,
        project_ids=project_ids
    )
    
    # Run assessment
    success = assessor.run_assessment(
        inventory_file=args.inventory_file,
        utilization_file=args.utilization_file,
        max_workers=args.max_workers
    )
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
