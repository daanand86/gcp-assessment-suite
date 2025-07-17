#!/usr/bin/env python3
"""
Google Cloud Networking Assessment Script
Assesses VPCs, subnets, firewall rules, load balancers, and other networking resources.
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
        logging.FileHandler('gcp_networking_assessment.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class GCPNetworkingAssessor:
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
        
        logger.info(f"Found {len(projects)} active projects for networking assessment")
        return projects

    def assess_project_networking(self, project: Dict[str, str]) -> Dict[str, List]:
        """Assess networking resources for a single project."""
        project_id = project['project_id']
        logger.info(f"Assessing networking for project: {project_id}")
        
        networking_data = {
            'vpcs': [],
            'subnets': [],
            'firewall_rules': [],
            'load_balancers': [],
            'nat_gateways': [],
            'vpn_gateways': [],
            'interconnects': [],
            'dns_zones': []
        }
        
        try:
            # Get VPC networks
            networking_data['vpcs'] = self.get_vpc_networks(project_id, project)
            
            # Get subnets
            networking_data['subnets'] = self.get_subnets(project_id, project)
            
            # Get firewall rules
            networking_data['firewall_rules'] = self.get_firewall_rules(project_id, project)
            
            # Get load balancers
            networking_data['load_balancers'] = self.get_load_balancers(project_id, project)
            
            # Get NAT gateways
            networking_data['nat_gateways'] = self.get_nat_gateways(project_id, project)
            
            # Get VPN gateways
            networking_data['vpn_gateways'] = self.get_vpn_gateways(project_id, project)
            
            # Get DNS zones
            networking_data['dns_zones'] = self.get_dns_zones(project_id, project)
            
        except Exception as e:
            logger.error(f"Error assessing networking for project {project_id}: {e}")
        
        return networking_data

    def get_vpc_networks(self, project_id: str, project: Dict) -> List[Dict]:
        """Get VPC networks for a project."""
        command = [
            "gcloud", "compute", "networks", "list",
            f"--project={project_id}",
            "--format=json"
        ]
        
        networks = self.run_gcloud_command(command)
        vpc_data = []
        
        if networks:
            for network in networks:
                vpc_info = {
                    'organization_id': self.organization_id or 'N/A',
                    'project_id': project_id,
                    'project_name': project['name'],
                    'vpc_name': network.get('name', 'N/A'),
                    'vpc_mode': network.get('routingConfig', {}).get('routingMode', 'N/A'),
                    'auto_create_subnetworks': str(network.get('autoCreateSubnetworks', False)),
                    'mtu': str(network.get('mtu', 'N/A')),
                    'creation_timestamp': network.get('creationTimestamp', 'N/A'),
                    'description': network.get('description', 'N/A')
                }
                vpc_data.append(vpc_info)
        
        time.sleep(self.request_delay)
        return vpc_data

    def get_subnets(self, project_id: str, project: Dict) -> List[Dict]:
        """Get subnets for a project."""
        command = [
            "gcloud", "compute", "networks", "subnets", "list",
            f"--project={project_id}",
            "--format=json"
        ]
        
        subnets = self.run_gcloud_command(command)
        subnet_data = []
        
        if subnets:
            for subnet in subnets:
                subnet_info = {
                    'organization_id': self.organization_id or 'N/A',
                    'project_id': project_id,
                    'project_name': project['name'],
                    'subnet_name': subnet.get('name', 'N/A'),
                    'network_name': subnet.get('network', 'N/A').split('/')[-1],
                    'region': subnet.get('region', 'N/A').split('/')[-1],
                    'ip_cidr_range': subnet.get('ipCidrRange', 'N/A'),
                    'gateway_address': subnet.get('gatewayAddress', 'N/A'),
                    'private_ip_google_access': str(subnet.get('privateIpGoogleAccess', False)),
                    'secondary_ranges': json.dumps(subnet.get('secondaryIpRanges', [])),
                    'creation_timestamp': subnet.get('creationTimestamp', 'N/A'),
                    'description': subnet.get('description', 'N/A')
                }
                subnet_data.append(subnet_info)
        
        time.sleep(self.request_delay)
        return subnet_data

    def get_firewall_rules(self, project_id: str, project: Dict) -> List[Dict]:
        """Get firewall rules for a project."""
        command = [
            "gcloud", "compute", "firewall-rules", "list",
            f"--project={project_id}",
            "--format=json"
        ]
        
        firewall_rules = self.run_gcloud_command(command)
        firewall_data = []
        
        if firewall_rules:
            for rule in firewall_rules:
                firewall_info = {
                    'organization_id': self.organization_id or 'N/A',
                    'project_id': project_id,
                    'project_name': project['name'],
                    'rule_name': rule.get('name', 'N/A'),
                    'network_name': rule.get('network', 'N/A').split('/')[-1],
                    'direction': rule.get('direction', 'N/A'),
                    'priority': str(rule.get('priority', 'N/A')),
                    'action': 'ALLOW' if rule.get('allowed') else 'DENY',
                    'source_ranges': json.dumps(rule.get('sourceRanges', [])),
                    'destination_ranges': json.dumps(rule.get('destinationRanges', [])),
                    'source_tags': json.dumps(rule.get('sourceTags', [])),
                    'target_tags': json.dumps(rule.get('targetTags', [])),
                    'protocols_ports': json.dumps(rule.get('allowed', rule.get('denied', []))),
                    'disabled': str(rule.get('disabled', False)),
                    'creation_timestamp': rule.get('creationTimestamp', 'N/A'),
                    'description': rule.get('description', 'N/A')
                }
                firewall_data.append(firewall_info)
        
        time.sleep(self.request_delay)
        return firewall_data

    def get_load_balancers(self, project_id: str, project: Dict) -> List[Dict]:
        """Get load balancers for a project."""
        lb_data = []
        
        # Get HTTP(S) load balancers
        command = [
            "gcloud", "compute", "url-maps", "list",
            f"--project={project_id}",
            "--format=json"
        ]
        
        url_maps = self.run_gcloud_command(command)
        if url_maps:
            for url_map in url_maps:
                lb_info = {
                    'organization_id': self.organization_id or 'N/A',
                    'project_id': project_id,
                    'project_name': project['name'],
                    'lb_name': url_map.get('name', 'N/A'),
                    'lb_type': 'HTTP(S)',
                    'default_service': url_map.get('defaultService', 'N/A').split('/')[-1],
                    'host_rules_count': str(len(url_map.get('hostRules', []))),
                    'path_matchers_count': str(len(url_map.get('pathMatchers', []))),
                    'creation_timestamp': url_map.get('creationTimestamp', 'N/A'),
                    'description': url_map.get('description', 'N/A')
                }
                lb_data.append(lb_info)
        
        # Get Network load balancers
        command = [
            "gcloud", "compute", "forwarding-rules", "list",
            f"--project={project_id}",
            "--format=json"
        ]
        
        forwarding_rules = self.run_gcloud_command(command)
        if forwarding_rules:
            for rule in forwarding_rules:
                if rule.get('loadBalancingScheme') in ['EXTERNAL', 'INTERNAL']:
                    lb_info = {
                        'organization_id': self.organization_id or 'N/A',
                        'project_id': project_id,
                        'project_name': project['name'],
                        'lb_name': rule.get('name', 'N/A'),
                        'lb_type': f"Network ({rule.get('loadBalancingScheme', 'N/A')})",
                        'ip_address': rule.get('IPAddress', 'N/A'),
                        'port_range': rule.get('portRange', 'N/A'),
                        'target': rule.get('target', 'N/A').split('/')[-1] if rule.get('target') else 'N/A',
                        'creation_timestamp': rule.get('creationTimestamp', 'N/A'),
                        'description': rule.get('description', 'N/A')
                    }
                    lb_data.append(lb_info)
        
        time.sleep(self.request_delay)
        return lb_data

    def get_nat_gateways(self, project_id: str, project: Dict) -> List[Dict]:
        """Get NAT gateways for a project."""
        nat_data = []
        
        # Get routers first, then NAT configs
        command = [
            "gcloud", "compute", "routers", "list",
            f"--project={project_id}",
            "--format=json"
        ]
        
        routers = self.run_gcloud_command(command)
        if routers:
            for router in routers:
                router_name = router.get('name', '')
                region = router.get('region', '').split('/')[-1]
                
                # Get NAT configurations for this router
                nat_command = [
                    "gcloud", "compute", "routers", "describe", router_name,
                    f"--region={region}",
                    f"--project={project_id}",
                    "--format=json"
                ]
                
                router_details = self.run_gcloud_command(nat_command)
                if router_details and router_details.get('nats'):
                    for nat in router_details['nats']:
                        nat_info = {
                            'organization_id': self.organization_id or 'N/A',
                            'project_id': project_id,
                            'project_name': project['name'],
                            'nat_name': nat.get('name', 'N/A'),
                            'router_name': router_name,
                            'region': region,
                            'source_subnetwork_ip_ranges': nat.get('sourceSubnetworkIpRangesToNat', 'N/A'),
                            'nat_ip_allocate_option': nat.get('natIpAllocateOption', 'N/A'),
                            'min_ports_per_vm': str(nat.get('minPortsPerVm', 'N/A')),
                            'creation_timestamp': router.get('creationTimestamp', 'N/A')
                        }
                        nat_data.append(nat_info)
        
        time.sleep(self.request_delay)
        return nat_data

    def get_vpn_gateways(self, project_id: str, project: Dict) -> List[Dict]:
        """Get VPN gateways for a project."""
        vpn_data = []
        
        command = [
            "gcloud", "compute", "vpn-gateways", "list",
            f"--project={project_id}",
            "--format=json"
        ]
        
        vpn_gateways = self.run_gcloud_command(command)
        if vpn_gateways:
            for gateway in vpn_gateways:
                vpn_info = {
                    'organization_id': self.organization_id or 'N/A',
                    'project_id': project_id,
                    'project_name': project['name'],
                    'vpn_gateway_name': gateway.get('name', 'N/A'),
                    'region': gateway.get('region', 'N/A').split('/')[-1],
                    'network': gateway.get('network', 'N/A').split('/')[-1],
                    'vpn_interfaces_count': str(len(gateway.get('vpnInterfaces', []))),
                    'creation_timestamp': gateway.get('creationTimestamp', 'N/A'),
                    'description': gateway.get('description', 'N/A')
                }
                vpn_data.append(vpn_info)
        
        time.sleep(self.request_delay)
        return vpn_data

    def get_dns_zones(self, project_id: str, project: Dict) -> List[Dict]:
        """Get DNS zones for a project."""
        command = [
            "gcloud", "dns", "managed-zones", "list",
            f"--project={project_id}",
            "--format=json"
        ]
        
        dns_zones = self.run_gcloud_command(command)
        dns_data = []
        
        if dns_zones:
            for zone in dns_zones:
                dns_info = {
                    'organization_id': self.organization_id or 'N/A',
                    'project_id': project_id,
                    'project_name': project['name'],
                    'zone_name': zone.get('name', 'N/A'),
                    'dns_name': zone.get('dnsName', 'N/A'),
                    'visibility': zone.get('visibility', 'N/A'),
                    'dnssec_state': zone.get('dnssecConfig', {}).get('state', 'N/A'),
                    'name_servers': json.dumps(zone.get('nameServers', [])),
                    'creation_time': zone.get('creationTime', 'N/A'),
                    'description': zone.get('description', 'N/A')
                }
                dns_data.append(dns_info)
        
        time.sleep(self.request_delay)
        return dns_data

    def export_networking_data(self, all_networking_data: Dict, base_filename: str):
        """Export networking data to separate CSV files."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Export VPCs
        if all_networking_data['vpcs']:
            vpc_filename = f"{base_filename}_vpcs_{timestamp}.csv"
            vpc_fieldnames = [
                'organization_id', 'project_id', 'project_name', 'vpc_name', 'vpc_mode',
                'auto_create_subnetworks', 'mtu', 'creation_timestamp', 'description'
            ]
            self.write_csv(all_networking_data['vpcs'], vpc_filename, vpc_fieldnames)
            logger.info(f"Exported {len(all_networking_data['vpcs'])} VPCs to {vpc_filename}")
        
        # Export Subnets
        if all_networking_data['subnets']:
            subnet_filename = f"{base_filename}_subnets_{timestamp}.csv"
            subnet_fieldnames = [
                'organization_id', 'project_id', 'project_name', 'subnet_name', 'network_name',
                'region', 'ip_cidr_range', 'gateway_address', 'private_ip_google_access',
                'secondary_ranges', 'creation_timestamp', 'description'
            ]
            self.write_csv(all_networking_data['subnets'], subnet_filename, subnet_fieldnames)
            logger.info(f"Exported {len(all_networking_data['subnets'])} subnets to {subnet_filename}")
        
        # Export Firewall Rules
        if all_networking_data['firewall_rules']:
            firewall_filename = f"{base_filename}_firewall_rules_{timestamp}.csv"
            firewall_fieldnames = [
                'organization_id', 'project_id', 'project_name', 'rule_name', 'network_name',
                'direction', 'priority', 'action', 'source_ranges', 'destination_ranges',
                'source_tags', 'target_tags', 'protocols_ports', 'disabled',
                'creation_timestamp', 'description'
            ]
            self.write_csv(all_networking_data['firewall_rules'], firewall_filename, firewall_fieldnames)
            logger.info(f"Exported {len(all_networking_data['firewall_rules'])} firewall rules to {firewall_filename}")
        
        # Export Load Balancers
        if all_networking_data['load_balancers']:
            lb_filename = f"{base_filename}_load_balancers_{timestamp}.csv"
            # Use flexible fieldnames based on data structure
            if all_networking_data['load_balancers']:
                lb_fieldnames = list(all_networking_data['load_balancers'][0].keys())
                self.write_csv(all_networking_data['load_balancers'], lb_filename, lb_fieldnames)
                logger.info(f"Exported {len(all_networking_data['load_balancers'])} load balancers to {lb_filename}")
        
        # Export NAT Gateways
        if all_networking_data['nat_gateways']:
            nat_filename = f"{base_filename}_nat_gateways_{timestamp}.csv"
            nat_fieldnames = [
                'organization_id', 'project_id', 'project_name', 'nat_name', 'router_name',
                'region', 'source_subnetwork_ip_ranges', 'nat_ip_allocate_option',
                'min_ports_per_vm', 'creation_timestamp'
            ]
            self.write_csv(all_networking_data['nat_gateways'], nat_filename, nat_fieldnames)
            logger.info(f"Exported {len(all_networking_data['nat_gateways'])} NAT gateways to {nat_filename}")
        
        # Export VPN Gateways
        if all_networking_data['vpn_gateways']:
            vpn_filename = f"{base_filename}_vpn_gateways_{timestamp}.csv"
            vpn_fieldnames = [
                'organization_id', 'project_id', 'project_name', 'vpn_gateway_name',
                'region', 'network', 'vpn_interfaces_count', 'creation_timestamp', 'description'
            ]
            self.write_csv(all_networking_data['vpn_gateways'], vpn_filename, vpn_fieldnames)
            logger.info(f"Exported {len(all_networking_data['vpn_gateways'])} VPN gateways to {vpn_filename}")
        
        # Export DNS Zones
        if all_networking_data['dns_zones']:
            dns_filename = f"{base_filename}_dns_zones_{timestamp}.csv"
            dns_fieldnames = [
                'organization_id', 'project_id', 'project_name', 'zone_name', 'dns_name',
                'visibility', 'dnssec_state', 'name_servers', 'creation_time', 'description'
            ]
            self.write_csv(all_networking_data['dns_zones'], dns_filename, dns_fieldnames)
            logger.info(f"Exported {len(all_networking_data['dns_zones'])} DNS zones to {dns_filename}")

    def write_csv(self, data: List[Dict], filename: str, fieldnames: List[str]):
        """Write data to CSV file."""
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)

    def run_assessment(self, base_filename: str = "gcp_networking", max_workers: int = 10):
        """Run the complete networking assessment."""
        logger.info("Starting GCP Networking Assessment")
        
        projects = self.get_projects()
        if not projects:
            logger.error("No projects found or accessible")
            return False
        
        all_networking_data = {
            'vpcs': [],
            'subnets': [],
            'firewall_rules': [],
            'load_balancers': [],
            'nat_gateways': [],
            'vpn_gateways': [],
            'dns_zones': []
        }
        
        # Process projects in parallel
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_project = {
                executor.submit(self.assess_project_networking, project): project
                for project in projects
            }
            
            for future in as_completed(future_to_project):
                project = future_to_project[future]
                try:
                    project_networking = future.result()
                    
                    # Aggregate data
                    for resource_type in all_networking_data.keys():
                        all_networking_data[resource_type].extend(project_networking[resource_type])
                    
                    logger.info(f"Completed networking assessment for project {project['project_id']}")
                    
                except Exception as e:
                    logger.error(f"Error processing project {project['project_id']}: {e}")
        
        # Export results
        self.export_networking_data(all_networking_data, base_filename)
        
        # Summary
        logger.info("="*60)
        logger.info("NETWORKING ASSESSMENT COMPLETED")
        logger.info(f"Projects processed: {len(projects)}")
        logger.info(f"VPCs found: {len(all_networking_data['vpcs'])}")
        logger.info(f"Subnets found: {len(all_networking_data['subnets'])}")
        logger.info(f"Firewall rules found: {len(all_networking_data['firewall_rules'])}")
        logger.info(f"Load balancers found: {len(all_networking_data['load_balancers'])}")
        logger.info(f"NAT gateways found: {len(all_networking_data['nat_gateways'])}")
        logger.info(f"VPN gateways found: {len(all_networking_data['vpn_gateways'])}")
        logger.info(f"DNS zones found: {len(all_networking_data['dns_zones'])}")
        logger.info("="*60)
        
        return True

def main():
    parser = argparse.ArgumentParser(description='GCP Networking Assessment Tool')
    
    scope_group = parser.add_mutually_exclusive_group()
    scope_group.add_argument('--org-id', help='Organization ID to assess')
    scope_group.add_argument('--folder-id', help='Folder ID to assess')
    scope_group.add_argument('--project-ids', help='Comma-separated list of project IDs')
    
    parser.add_argument('--output-prefix', default='gcp_networking', help='Output file prefix')
    parser.add_argument('--max-workers', type=int, default=10, help='Maximum parallel workers')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                       default='INFO', help='Logging level')
    
    args = parser.parse_args()
    
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    project_ids = None
    if args.project_ids:
        project_ids = [pid.strip() for pid in args.project_ids.split(',')]
    
    assessor = GCPNetworkingAssessor(
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
