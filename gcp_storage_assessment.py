#!/usr/bin/env python3
"""
Google Cloud Storage (GCS) Assessment Script
Assesses GCS buckets, storage usage, lifecycle policies, and access controls.
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
        logging.FileHandler('gcp_storage_assessment.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class GCPStorageAssessor:
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

    def run_gsutil_command(self, command: List[str]) -> str:
        """Execute gsutil command and return output."""
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logger.error(f"gsutil command failed: {' '.join(command)}")
            logger.error(f"Error: {e.stderr}")
            return ""

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
        
        logger.info(f"Found {len(projects)} active projects for storage assessment")
        return projects

    def assess_project_storage(self, project: Dict[str, str]) -> Dict[str, List]:
        """Assess storage resources for a single project."""
        project_id = project['project_id']
        logger.info(f"Assessing storage for project: {project_id}")
        
        storage_data = {
            'buckets': [],
            'bucket_usage': []
        }
        
        try:
            # Get GCS buckets
            storage_data['buckets'] = self.get_gcs_buckets(project_id, project)
            
            # Get bucket usage statistics
            storage_data['bucket_usage'] = self.get_bucket_usage(project_id, project, storage_data['buckets'])
            
        except Exception as e:
            logger.error(f"Error assessing storage for project {project_id}: {e}")
        
        return storage_data

    def get_gcs_buckets(self, project_id: str, project: Dict) -> List[Dict]:
        """Get GCS buckets for a project."""
        command = [
            "gsutil", "ls", "-L", "-b", f"gs://*",
            "-p", project_id
        ]
        
        # Alternative approach using gcloud
        gcloud_command = [
            "gcloud", "storage", "buckets", "list",
            f"--project={project_id}",
            "--format=json"
        ]
        
        buckets_data = []
        
        # Try gcloud storage command first (newer)
        buckets = self.run_gcloud_command(gcloud_command)
        
        if buckets:
            for bucket in buckets:
                bucket_name = bucket.get('name', 'N/A')
                
                # Get detailed bucket information
                bucket_details = self.get_bucket_details(bucket_name, project_id, project)
                buckets_data.append(bucket_details)
        else:
            # Fallback to gsutil if gcloud storage is not available
            logger.info(f"Using gsutil for bucket listing in project {project_id}")
            # This would require parsing gsutil output, which is more complex
            # For now, we'll focus on the gcloud approach
        
        time.sleep(self.request_delay)
        return buckets_data

    def get_bucket_details(self, bucket_name: str, project_id: str, project: Dict) -> Dict:
        """Get detailed information about a specific bucket."""
        command = [
            "gcloud", "storage", "buckets", "describe", f"gs://{bucket_name}",
            "--format=json"
        ]
        
        bucket_info = self.run_gcloud_command(command)
        
        if not bucket_info:
            # Fallback bucket info
            bucket_info = {'name': bucket_name}
        
        # Get lifecycle configuration
        lifecycle_config = self.get_bucket_lifecycle(bucket_name)
        
        # Get IAM policy
        iam_policy = self.get_bucket_iam_policy(bucket_name)
        
        # Get CORS configuration
        cors_config = self.get_bucket_cors(bucket_name)
        
        bucket_details = {
            'organization_id': self.organization_id or 'N/A',
            'project_id': project_id,
            'project_name': project['name'],
            'bucket_name': bucket_name,
            'location': bucket_info.get('location', 'N/A'),
            'location_type': bucket_info.get('locationType', 'N/A'),
            'storage_class': bucket_info.get('storageClass', 'N/A'),
            'versioning_enabled': str(bucket_info.get('versioning', {}).get('enabled', False)),
            'lifecycle_rules_count': str(len(lifecycle_config)),
            'public_access_prevention': bucket_info.get('publicAccessPrevention', 'N/A'),
            'uniform_bucket_level_access': str(bucket_info.get('uniformBucketLevelAccess', {}).get('enabled', False)),
            'retention_policy': json.dumps(bucket_info.get('retentionPolicy', {})),
            'encryption_type': bucket_info.get('encryption', {}).get('defaultKmsKeyName', 'Google-managed'),
            'cors_enabled': str(len(cors_config) > 0),
            'labels': json.dumps(bucket_info.get('labels', {})),
            'creation_time': bucket_info.get('timeCreated', 'N/A'),
            'updated_time': bucket_info.get('updated', 'N/A'),
            'iam_members_count': str(len(iam_policy.get('bindings', []))),
            'website_config': json.dumps(bucket_info.get('website', {}))
        }
        
        return bucket_details

    def get_bucket_lifecycle(self, bucket_name: str) -> List[Dict]:
        """Get lifecycle configuration for a bucket."""
        command = [
            "gsutil", "lifecycle", "get", f"gs://{bucket_name}"
        ]
        
        try:
            result = self.run_gsutil_command(command)
            if result:
                lifecycle_data = json.loads(result)
                return lifecycle_data.get('rule', [])
        except:
            pass
        
        return []

    def get_bucket_iam_policy(self, bucket_name: str) -> Dict:
        """Get IAM policy for a bucket."""
        command = [
            "gsutil", "iam", "get", f"gs://{bucket_name}"
        ]
        
        try:
            result = self.run_gsutil_command(command)
            if result:
                return json.loads(result)
        except:
            pass
        
        return {}

    def get_bucket_cors(self, bucket_name: str) -> List[Dict]:
        """Get CORS configuration for a bucket."""
        command = [
            "gsutil", "cors", "get", f"gs://{bucket_name}"
        ]
        
        try:
            result = self.run_gsutil_command(command)
            if result:
                return json.loads(result)
        except:
            pass
        
        return []

    def get_bucket_usage(self, project_id: str, project: Dict, buckets: List[Dict]) -> List[Dict]:
        """Get usage statistics for buckets."""
        usage_data = []
        
        for bucket in buckets:
            bucket_name = bucket['bucket_name']
            
            try:
                # Get bucket size and object count using gsutil
                du_command = ["gsutil", "du", "-s", f"gs://{bucket_name}"]
                size_result = self.run_gsutil_command(du_command)
                
                # Parse size (format: "size_bytes gs://bucket_name")
                total_size_bytes = 0
                if size_result:
                    parts = size_result.split()
                    if len(parts) >= 2:
                        try:
                            total_size_bytes = int(parts[0])
                        except ValueError:
                            pass
                
                # Get object count
                ls_command = ["gsutil", "ls", "-l", f"gs://{bucket_name}/**"]
                ls_result = self.run_gsutil_command(ls_command)
                
                object_count = 0
                if ls_result:
                    # Count lines that represent objects (not directories or summary)
                    lines = ls_result.split('\n')
                    object_count = len([line for line in lines if line.strip() and not line.startswith('TOTAL:')])
                
                usage_info = {
                    'organization_id': self.organization_id or 'N/A',
                    'project_id': project_id,
                    'project_name': project['name'],
                    'bucket_name': bucket_name,
                    'total_size_bytes': str(total_size_bytes),
                    'total_size_gb': str(round(total_size_bytes / (1024**3), 2)) if total_size_bytes > 0 else '0',
                    'total_size_tb': str(round(total_size_bytes / (1024**4), 4)) if total_size_bytes > 0 else '0',
                    'object_count': str(object_count),
                    'storage_class': bucket.get('storage_class', 'N/A'),
                    'location': bucket.get('location', 'N/A'),
                    'assessment_date': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
                }
                
                usage_data.append(usage_info)
                
                # Small delay to avoid rate limits
                time.sleep(self.request_delay)
                
            except Exception as e:
                logger.error(f"Error getting usage for bucket {bucket_name}: {e}")
                continue
        
        return usage_data

    def export_storage_data(self, all_storage_data: Dict, base_filename: str):
        """Export storage data to separate CSV files."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Export Buckets
        if all_storage_data['buckets']:
            buckets_filename = f"{base_filename}_buckets_{timestamp}.csv"
            bucket_fieldnames = [
                'organization_id', 'project_id', 'project_name', 'bucket_name', 'location',
                'location_type', 'storage_class', 'versioning_enabled', 'lifecycle_rules_count',
                'public_access_prevention', 'uniform_bucket_level_access', 'retention_policy',
                'encryption_type', 'cors_enabled', 'labels', 'creation_time', 'updated_time',
                'iam_members_count', 'website_config'
            ]
            self.write_csv(all_storage_data['buckets'], buckets_filename, bucket_fieldnames)
            logger.info(f"Exported {len(all_storage_data['buckets'])} buckets to {buckets_filename}")
        
        # Export Bucket Usage
        if all_storage_data['bucket_usage']:
            usage_filename = f"{base_filename}_usage_{timestamp}.csv"
            usage_fieldnames = [
                'organization_id', 'project_id', 'project_name', 'bucket_name',
                'total_size_bytes', 'total_size_gb', 'total_size_tb', 'object_count',
                'storage_class', 'location', 'assessment_date'
            ]
            self.write_csv(all_storage_data['bucket_usage'], usage_filename, usage_fieldnames)
            logger.info(f"Exported {len(all_storage_data['bucket_usage'])} bucket usage records to {usage_filename}")

    def write_csv(self, data: List[Dict], filename: str, fieldnames: List[str]):
        """Write data to CSV file."""
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)

    def run_assessment(self, base_filename: str = "gcp_storage", max_workers: int = 10):
        """Run the complete storage assessment."""
        logger.info("Starting GCP Storage Assessment")
        
        projects = self.get_projects()
        if not projects:
            logger.error("No projects found or accessible")
            return False
        
        all_storage_data = {
            'buckets': [],
            'bucket_usage': []
        }
        
        # Process projects in parallel
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_project = {
                executor.submit(self.assess_project_storage, project): project
                for project in projects
            }
            
            for future in as_completed(future_to_project):
                project = future_to_project[future]
                try:
                    project_storage = future.result()
                    
                    # Aggregate data
                    all_storage_data['buckets'].extend(project_storage['buckets'])
                    all_storage_data['bucket_usage'].extend(project_storage['bucket_usage'])
                    
                    logger.info(f"Completed storage assessment for project {project['project_id']}")
                    
                except Exception as e:
                    logger.error(f"Error processing project {project['project_id']}: {e}")
        
        # Export results
        self.export_storage_data(all_storage_data, base_filename)
        
        # Calculate totals
        total_size_gb = sum(float(usage.get('total_size_gb', 0)) for usage in all_storage_data['bucket_usage'])
        total_objects = sum(int(usage.get('object_count', 0)) for usage in all_storage_data['bucket_usage'])
        
        # Summary
        logger.info("="*60)
        logger.info("STORAGE ASSESSMENT COMPLETED")
        logger.info(f"Projects processed: {len(projects)}")
        logger.info(f"Total buckets found: {len(all_storage_data['buckets'])}")
        logger.info(f"Total storage size: {total_size_gb:.2f} GB ({total_size_gb/1024:.2f} TB)")
        logger.info(f"Total objects: {total_objects:,}")
        logger.info("="*60)
        
        return True

def main():
    parser = argparse.ArgumentParser(description='GCP Storage Assessment Tool')
    
    scope_group = parser.add_mutually_exclusive_group()
    scope_group.add_argument('--org-id', help='Organization ID to assess')
    scope_group.add_argument('--folder-id', help='Folder ID to assess')
    scope_group.add_argument('--project-ids', help='Comma-separated list of project IDs')
    
    parser.add_argument('--output-prefix', default='gcp_storage', help='Output file prefix')
    parser.add_argument('--max-workers', type=int, default=10, help='Maximum parallel workers')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                       default='INFO', help='Logging level')
    
    args = parser.parse_args()
    
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    project_ids = None
    if args.project_ids:
        project_ids = [pid.strip() for pid in args.project_ids.split(',')]
    
    assessor = GCPStorageAssessor(
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
