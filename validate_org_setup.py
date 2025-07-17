#!/usr/bin/env python3
"""
Organization-Level GCP Setup Validation Script
Validates authentication, permissions, and access for organization-wide assessment.
"""

import subprocess
import json
import sys
import os
from typing import Dict, List, Tuple

class OrgSetupValidator:
    def __init__(self):
        self.organization_id = os.getenv('GCP_ORGANIZATION_ID')
        self.folder_id = os.getenv('GCP_FOLDER_ID')
        self.validation_results = []

    def run_command(self, command: List[str]) -> Tuple[bool, str]:
        """Run a command and return success status and output."""
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            return True, result.stdout.strip()
        except subprocess.CalledProcessError as e:
            return False, e.stderr.strip()

    def print_result(self, test_name: str, success: bool, message: str, details: str = ""):
        """Print formatted test result."""
        status = "✓" if success else "✗"
        print(f"{status} {test_name}")
        if message:
            print(f"  {message}")
        if details:
            for line in details.split('\n'):
                if line.strip():
                    print(f"    {line}")
        print()
        
        self.validation_results.append({
            'test': test_name,
            'success': success,
            'message': message,
            'details': details
        })

    def validate_gcloud_installation(self) -> bool:
        """Test 1: Check if gcloud is installed and configured."""
        print("1. Validating gcloud CLI installation...")
        
        success, output = self.run_command(["gcloud", "version"])
        if success:
            version_info = output.split('\n')[0] if output else "Unknown version"
            self.print_result(
                "gcloud CLI Installation", 
                True, 
                f"gcloud CLI is installed: {version_info}"
            )
            return True
        else:
            self.print_result(
                "gcloud CLI Installation", 
                False, 
                "gcloud CLI not found. Please install Google Cloud SDK.",
                "Visit: https://cloud.google.com/sdk/docs/install"
            )
            return False

    def validate_authentication(self) -> bool:
        """Test 2: Check authentication status."""
        print("2. Validating authentication...")
        
        success, output = self.run_command(["gcloud", "auth", "list", "--format=json"])
        if not success:
            self.print_result(
                "Authentication Check", 
                False, 
                "Error checking authentication status"
            )
            return False

        try:
            auth_data = json.loads(output)
            active_accounts = [acc for acc in auth_data if acc.get('status') == 'ACTIVE']
            
            if active_accounts:
                account_info = f"Active account: {active_accounts[0]['account']}"
                account_type = "Service Account" if "@" in active_accounts[0]['account'] and ".iam.gserviceaccount.com" in active_accounts[0]['account'] else "User Account"
                
                self.print_result(
                    "Authentication Status", 
                    True, 
                    f"Authentication configured ({account_type})",
                    account_info
                )
                return True
            else:
                self.print_result(
                    "Authentication Status", 
                    False, 
                    "No active authentication found",
                    "Run 'gcloud auth login' or 'gcloud auth activate-service-account'"
                )
                return False
                
        except json.JSONDecodeError:
            self.print_result(
                "Authentication Status", 
                False, 
                "Error parsing authentication data"
            )
            return False

    def validate_organization_access(self) -> bool:
        """Test 3: Check organization access."""
        print("3. Validating organization access...")
        
        # List all accessible organizations
        success, output = self.run_command(["gcloud", "organizations", "list", "--format=json"])
        if not success:
            self.print_result(
                "Organization Access", 
                False, 
                "Cannot list organizations. Check IAM permissions.",
                "Required role: roles/resourcemanager.organizationViewer"
            )
            return False

        try:
            orgs = json.loads(output)
            if not orgs:
                self.print_result(
                    "Organization Access", 
                    False, 
                    "No accessible organizations found",
                    "Verify organization-level IAM permissions"
                )
                return False

            org_details = []
            for org in orgs:
                org_details.append(f"- {org['name']} (ID: {org['organizationId']})")
            
            # Check specific organization if provided
            if self.organization_id:
                target_org = next((org for org in orgs if org['organizationId'] == self.organization_id), None)
                if target_org:
                    self.print_result(
                        "Organization Access", 
                        True, 
                        f"Target organization accessible: {target_org['name']}",
                        f"Organization ID: {self.organization_id}"
                    )
                else:
                    self.print_result(
                        "Organization Access", 
                        False, 
                        f"Target organization {self.organization_id} not accessible",
                        "Available organizations:\n" + "\n".join(org_details)
                    )
                    return False
            else:
                self.print_result(
                    "Organization Access", 
                    True, 
                    f"Access to {len(orgs)} organization(s)",
                    "Available organizations:\n" + "\n".join(org_details)
                )
            
            return True
            
        except json.JSONDecodeError:
            self.print_result(
                "Organization Access", 
                False, 
                "Error parsing organization data"
            )
            return False

    def validate_project_listing(self) -> bool:
        """Test 4: Check project listing capabilities."""
        print("4. Validating project listing access...")
        
        # Check if specific projects are provided via environment
        specific_projects = os.getenv('GCP_PROJECT_IDS')
        if specific_projects:
            project_ids = [pid.strip() for pid in specific_projects.split(',')]
            scope = f"specific projects: {', '.join(project_ids)}"
            
            # Test access to each specific project
            accessible_projects = []
            for project_id in project_ids:
                success, output = self.run_command([
                    "gcloud", "projects", "describe", project_id, "--format=json"
                ])
                if success:
                    try:
                        project_data = json.loads(output)
                        if project_data.get('lifecycleState') == 'ACTIVE':
                            accessible_projects.append(project_data)
                    except json.JSONDecodeError:
                        pass
            
            if accessible_projects:
                project_summary = [f"- {p['projectId']} ({p['name']})" for p in accessible_projects]
                self.print_result(
                    "Project Access", 
                    True, 
                    f"Access to {len(accessible_projects)}/{len(project_ids)} specified projects",
                    "\n".join(project_summary)
                )
            else:
                self.print_result(
                    "Project Access", 
                    False, 
                    f"No access to specified projects: {', '.join(project_ids)}"
                )
                return False
        
        elif self.organization_id:
            filter_clause = f"--filter=parent.id={self.organization_id}"
            scope = f"organization {self.organization_id}"
        elif self.folder_id:
            folder_num = self.folder_id.replace('folders/', '')
            filter_clause = f"--filter=parent.id={folder_num}"
            scope = f"folder {self.folder_id}"
        else:
            filter_clause = ""
            scope = "all accessible projects"
        
        if not specific_projects:
            command = ["gcloud", "projects", "list", "--format=json"]
            if filter_clause:
                command.append(filter_clause)
            
            success, output = self.run_command(command)
            if not success:
                self.print_result(
                    "Project Listing", 
                    False, 
                    f"Cannot list projects for {scope}",
                    "Check resourcemanager.projects.list permission"
                )
                return False

            try:
                projects = json.loads(output)
                active_projects = [p for p in projects if p.get('lifecycleState') == 'ACTIVE']
                
                if active_projects:
                    project_summary = []
                    for i, project in enumerate(active_projects[:5]):  # Show first 5
                        project_summary.append(f"- {project['projectId']} ({project['name']})")
                    
                    if len(active_projects) > 5:
                        project_summary.append(f"... and {len(active_projects) - 5} more projects")
                    
                    self.print_result(
                        "Project Listing", 
                        True, 
                        f"Access to {len(active_projects)} active project(s) in {scope}",
                        "\n".join(project_summary)
                    )
                else:
                    self.print_result(
                        "Project Listing", 
                        True, 
                        f"No active projects found in {scope}",
                        "This may be expected if the organization/folder is empty"
                    )
                
            except json.JSONDecodeError:
                self.print_result(
                    "Project Listing", 
                    False, 
                    "Error parsing project data"
                )
                return False
            
        return True

    def validate_compute_api_access(self) -> bool:
        """Test 5: Check Compute Engine API access."""
        print("5. Validating Compute Engine API access...")
        
        # Get a sample project to test with
        success, output = self.run_command(["gcloud", "projects", "list", "--limit=1", "--format=json"])
        if not success:
            self.print_result(
                "Compute API Access", 
                False, 
                "Cannot get test project for API validation"
            )
            return False

        try:
            projects = json.loads(output)
            if not projects:
                self.print_result(
                    "Compute API Access", 
                    False, 
                    "No projects available for API testing"
                )
                return False

            test_project = projects[0]['projectId']
            
            # Test compute instances list
            success, output = self.run_command([
                "gcloud", "compute", "instances", "list", 
                f"--project={test_project}", 
                "--format=json",
                "--limit=1"
            ])
            
            if success:
                self.print_result(
                    "Compute API Access", 
                    True, 
                    f"Compute Engine API access verified",
                    f"Test project: {test_project}"
                )
                return True
            else:
                error_msg = "API access denied or not enabled"
                if "API has not been used" in output:
                    error_msg = "Compute Engine API not enabled"
                elif "Permission denied" in output:
                    error_msg = "Insufficient IAM permissions"
                
                self.print_result(
                    "Compute API Access", 
                    False, 
                    error_msg,
                    f"Test project: {test_project}\nRequired role: roles/compute.viewer"
                )
                return False
                
        except json.JSONDecodeError:
            self.print_result(
                "Compute API Access", 
                False, 
                "Error parsing API response"
            )
            return False

    def validate_monitoring_api_access(self) -> bool:
        """Test 6: Check Cloud Monitoring API access."""
        print("6. Validating Cloud Monitoring API access...")
        
        # Get a sample project to test with
        success, output = self.run_command(["gcloud", "projects", "list", "--limit=1", "--format=json"])
        if not success:
            self.print_result(
                "Monitoring API Access", 
                False, 
                "Cannot get test project for monitoring validation"
            )
            return False

        try:
            projects = json.loads(output)
            if not projects:
                self.print_result(
                    "Monitoring API Access", 
                    False, 
                    "No projects available for monitoring testing"
                )
                return False

            test_project = projects[0]['projectId']
            
            # Test monitoring metrics list (basic check)
            success, output = self.run_command([
                "gcloud", "monitoring", "metrics", "list",
                f"--project={test_project}",
                "--limit=1",
                "--format=json"
            ])
            
            if success:
                self.print_result(
                    "Monitoring API Access", 
                    True, 
                    "Cloud Monitoring API access verified",
                    f"Test project: {test_project}"
                )
                return True
            else:
                error_msg = "Monitoring API access denied or not enabled"
                if "API has not been used" in output:
                    error_msg = "Cloud Monitoring API not enabled"
                elif "Permission denied" in output:
                    error_msg = "Insufficient monitoring permissions"
                
                self.print_result(
                    "Monitoring API Access", 
                    False, 
                    error_msg,
                    f"Test project: {test_project}\nRequired role: roles/monitoring.viewer"
                )
                return False
                
        except json.JSONDecodeError:
            self.print_result(
                "Monitoring API Access", 
                False, 
                "Error parsing monitoring API response"
            )
            return False

    def validate_environment_variables(self) -> bool:
        """Test 7: Check environment variables."""
        print("7. Validating environment variables...")
        
        env_status = []
        
        # Check for service account key
        sa_key_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if sa_key_path:
            if os.path.exists(sa_key_path):
                env_status.append("✓ GOOGLE_APPLICATION_CREDENTIALS set and file exists")
            else:
                env_status.append("✗ GOOGLE_APPLICATION_CREDENTIALS set but file not found")
        else:
            env_status.append("- GOOGLE_APPLICATION_CREDENTIALS not set (using gcloud auth)")
        
        # Check organization ID
        if self.organization_id:
            env_status.append(f"✓ GCP_ORGANIZATION_ID: {self.organization_id}")
        else:
            env_status.append("- GCP_ORGANIZATION_ID not set")
        
        # Check folder ID
        if self.folder_id:
            env_status.append(f"✓ GCP_FOLDER_ID: {self.folder_id}")
        else:
            env_status.append("- GCP_FOLDER_ID not set")
        
        # Check specific project IDs
        project_ids = os.getenv('GCP_PROJECT_IDS')
        if project_ids:
            project_list = [pid.strip() for pid in project_ids.split(',')]
            env_status.append(f"✓ GCP_PROJECT_IDS: {len(project_list)} project(s)")
            for pid in project_list[:3]:  # Show first 3
                env_status.append(f"  - {pid}")
            if len(project_list) > 3:
                env_status.append(f"  ... and {len(project_list) - 3} more")
        else:
            env_status.append("- GCP_PROJECT_IDS not set")
        
        self.print_result(
            "Environment Variables", 
            True, 
            "Environment variable status:",
            "\n".join(env_status)
        )
        return True

    def generate_summary(self):
        """Generate validation summary."""
        print("="*60)
        print("VALIDATION SUMMARY")
        print("="*60)
        
        passed_tests = sum(1 for result in self.validation_results if result['success'])
        total_tests = len(self.validation_results)
        
        print(f"Tests passed: {passed_tests}/{total_tests}")
        print()
        
        # Show failed tests
        failed_tests = [result for result in self.validation_results if not result['success']]
        if failed_tests:
            print("FAILED TESTS:")
            for test in failed_tests:
                print(f"✗ {test['test']}: {test['message']}")
            print()
        
        # Recommendations
        print("RECOMMENDATIONS:")
        if passed_tests == total_tests:
            print("✓ All validations passed! You can run the organization assessment.")
            print("  Command: python3 gcp_org_compute_inventory.py --org-id YOUR_ORG_ID")
        else:
            print("Please address the failed validations before running the assessment:")
            print("1. Review the PREREQUISITES.md file")
            print("2. Ensure proper IAM roles are assigned")
            print("3. Enable required APIs in your projects")
            print("4. Verify authentication setup")
        
        print("="*60)
        
        return passed_tests == total_tests

def main():
    print("GCP Organization-Level Setup Validation")
    print("="*60)
    print()
    
    validator = OrgSetupValidator()
    
    # Run all validations
    validations = [
        validator.validate_gcloud_installation,
        validator.validate_authentication,
        validator.validate_organization_access,
        validator.validate_project_listing,
        validator.validate_compute_api_access,
        validator.validate_monitoring_api_access,
        validator.validate_environment_variables
    ]
    
    all_passed = True
    for validation in validations:
        try:
            result = validation()
            all_passed = all_passed and result
        except Exception as e:
            print(f"Error during validation: {e}")
            all_passed = False
    
    # Generate summary
    validator.generate_summary()
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
