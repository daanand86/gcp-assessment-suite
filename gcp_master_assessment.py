#!/usr/bin/env python3
"""
GCP Master Assessment Script
Runs all GCP service assessments (Compute, Networking, Storage, GKE) in sequence or parallel.
"""

import subprocess
import sys
import os
import time
import argparse
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('gcp_master_assessment.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class GCPMasterAssessor:
    def __init__(self):
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.assessment_scripts = {
            'compute': 'gcp_org_compute_inventory.py',
            'networking': 'gcp_networking_assessment.py',
            'storage': 'gcp_storage_assessment.py',
            'gke': 'gcp_gke_assessment.py'
        }
        
    def run_single_assessment(self, service: str, args: argparse.Namespace) -> dict:
        """Run a single service assessment."""
        script_name = self.assessment_scripts[service]
        script_path = os.path.join(self.script_dir, script_name)
        
        if not os.path.exists(script_path):
            logger.error(f"Assessment script not found: {script_path}")
            return {'service': service, 'success': False, 'error': 'Script not found'}
        
        # Build command
        command = ['python3', script_path]
        
        # Add scope arguments
        if args.org_id:
            command.extend(['--org-id', args.org_id])
        elif args.folder_id:
            command.extend(['--folder-id', args.folder_id])
        elif args.project_ids:
            command.extend(['--project-ids', args.project_ids])
        
        # Add service-specific arguments
        if service == 'compute':
            command.extend([
                '--inventory-file', f'gcp_compute_inventory_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
                '--utilization-file', f'gcp_compute_utilization_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
            ])
        else:
            command.extend(['--output-prefix', f'gcp_{service}'])
        
        # Add common arguments
        command.extend(['--max-workers', str(args.max_workers)])
        command.extend(['--log-level', args.log_level])
        
        logger.info(f"Starting {service.upper()} assessment...")
        start_time = time.time()
        
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True,
                timeout=args.timeout
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            logger.info(f"{service.upper()} assessment completed successfully in {duration:.2f} seconds")
            
            return {
                'service': service,
                'success': True,
                'duration': duration,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
            
        except subprocess.TimeoutExpired:
            logger.error(f"{service.upper()} assessment timed out after {args.timeout} seconds")
            return {
                'service': service,
                'success': False,
                'error': f'Timeout after {args.timeout} seconds'
            }
        except subprocess.CalledProcessError as e:
            logger.error(f"{service.upper()} assessment failed with exit code {e.returncode}")
            logger.error(f"Error output: {e.stderr}")
            return {
                'service': service,
                'success': False,
                'error': f'Exit code {e.returncode}: {e.stderr}'
            }
        except Exception as e:
            logger.error(f"Unexpected error running {service.upper()} assessment: {e}")
            return {
                'service': service,
                'success': False,
                'error': str(e)
            }

    def run_sequential_assessment(self, services: list, args: argparse.Namespace) -> dict:
        """Run assessments sequentially."""
        results = {}
        total_start_time = time.time()
        
        for service in services:
            result = self.run_single_assessment(service, args)
            results[service] = result
            
            if not result['success']:
                logger.warning(f"{service.upper()} assessment failed, continuing with next service...")
        
        total_duration = time.time() - total_start_time
        results['total_duration'] = total_duration
        
        return results

    def run_parallel_assessment(self, services: list, args: argparse.Namespace) -> dict:
        """Run assessments in parallel."""
        results = {}
        total_start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=len(services)) as executor:
            # Submit all assessment tasks
            future_to_service = {
                executor.submit(self.run_single_assessment, service, args): service
                for service in services
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_service):
                service = future_to_service[future]
                try:
                    result = future.result()
                    results[service] = result
                except Exception as e:
                    logger.error(f"Error in {service.upper()} assessment: {e}")
                    results[service] = {
                        'service': service,
                        'success': False,
                        'error': str(e)
                    }
        
        total_duration = time.time() - total_start_time
        results['total_duration'] = total_duration
        
        return results

    def generate_summary_report(self, results: dict, output_file: str):
        """Generate a summary report of all assessments."""
        with open(output_file, 'w') as f:
            f.write("GCP MASTER ASSESSMENT SUMMARY REPORT\n")
            f.write("=" * 50 + "\n")
            f.write(f"Assessment Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
            f.write(f"Total Duration: {results.get('total_duration', 0):.2f} seconds\n\n")
            
            # Service results
            services = ['compute', 'networking', 'storage', 'gke']
            successful_services = []
            failed_services = []
            
            for service in services:
                if service in results:
                    result = results[service]
                    status = "SUCCESS" if result['success'] else "FAILED"
                    duration = result.get('duration', 0)
                    
                    f.write(f"{service.upper()} Assessment: {status}\n")
                    if result['success']:
                        f.write(f"  Duration: {duration:.2f} seconds\n")
                        successful_services.append(service)
                    else:
                        f.write(f"  Error: {result.get('error', 'Unknown error')}\n")
                        failed_services.append(service)
                    f.write("\n")
            
            # Summary
            f.write("SUMMARY\n")
            f.write("-" * 20 + "\n")
            f.write(f"Successful assessments: {len(successful_services)}/{len(services)}\n")
            f.write(f"Successful services: {', '.join(successful_services)}\n")
            if failed_services:
                f.write(f"Failed services: {', '.join(failed_services)}\n")
            
            # Generated files
            f.write("\nGENERATED FILES\n")
            f.write("-" * 20 + "\n")
            f.write("Check the current directory for the following file patterns:\n")
            f.write("- gcp_compute_inventory_*.csv\n")
            f.write("- gcp_compute_utilization_*.csv\n")
            f.write("- gcp_networking_*_*.csv\n")
            f.write("- gcp_storage_*_*.csv\n")
            f.write("- gcp_gke_*_*.csv\n")
            f.write("- *.log (assessment logs)\n")
        
        logger.info(f"Summary report generated: {output_file}")

def main():
    parser = argparse.ArgumentParser(
        description='GCP Master Assessment Tool - Run all service assessments',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all assessments for an organization
  python3 gcp_master_assessment.py --org-id 123456789012
  
  # Run specific services in parallel
  python3 gcp_master_assessment.py --org-id 123456789012 --services compute,networking --parallel
  
  # Run for specific projects
  python3 gcp_master_assessment.py --project-ids proj1,proj2 --services storage,gke
        """
    )
    
    # Scope options
    scope_group = parser.add_mutually_exclusive_group()
    scope_group.add_argument('--org-id', help='Organization ID to assess')
    scope_group.add_argument('--folder-id', help='Folder ID to assess')
    scope_group.add_argument('--project-ids', help='Comma-separated list of project IDs')
    
    # Service selection
    parser.add_argument('--services', 
                       default='compute,networking,storage,gke',
                       help='Comma-separated list of services to assess (compute,networking,storage,gke)')
    
    # Execution options
    parser.add_argument('--parallel', action='store_true',
                       help='Run assessments in parallel (default: sequential)')
    parser.add_argument('--max-workers', type=int, default=10,
                       help='Maximum parallel workers per assessment')
    parser.add_argument('--timeout', type=int, default=3600,
                       help='Timeout per assessment in seconds (default: 1 hour)')
    
    # Output options
    parser.add_argument('--summary-report', default='gcp_assessment_summary.txt',
                       help='Summary report filename')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       default='INFO', help='Logging level')
    
    args = parser.parse_args()
    
    # Set logging level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Parse services
    available_services = ['compute', 'networking', 'storage', 'gke']
    requested_services = [s.strip().lower() for s in args.services.split(',')]
    
    # Validate services
    invalid_services = [s for s in requested_services if s not in available_services]
    if invalid_services:
        logger.error(f"Invalid services: {', '.join(invalid_services)}")
        logger.error(f"Available services: {', '.join(available_services)}")
        sys.exit(1)
    
    # Validate scope
    if not any([args.org_id, args.folder_id, args.project_ids]):
        logger.warning("No scope specified. Will assess all accessible projects.")
    
    logger.info("Starting GCP Master Assessment")
    logger.info(f"Services to assess: {', '.join(requested_services)}")
    logger.info(f"Execution mode: {'Parallel' if args.parallel else 'Sequential'}")
    
    # Initialize assessor
    assessor = GCPMasterAssessor()
    
    # Run assessments
    if args.parallel:
        results = assessor.run_parallel_assessment(requested_services, args)
    else:
        results = assessor.run_sequential_assessment(requested_services, args)
    
    # Generate summary report
    assessor.generate_summary_report(results, args.summary_report)
    
    # Final summary
    successful_count = sum(1 for service in requested_services if results.get(service, {}).get('success', False))
    total_count = len(requested_services)
    
    logger.info("="*60)
    logger.info("GCP MASTER ASSESSMENT COMPLETED")
    logger.info(f"Successful assessments: {successful_count}/{total_count}")
    logger.info(f"Total duration: {results.get('total_duration', 0):.2f} seconds")
    logger.info(f"Summary report: {args.summary_report}")
    logger.info("="*60)
    
    # Exit with appropriate code
    sys.exit(0 if successful_count == total_count else 1)

if __name__ == "__main__":
    main()
