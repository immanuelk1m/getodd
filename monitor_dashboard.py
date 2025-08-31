#!/usr/bin/env python3
"""
GetOdd Real-time Monitoring Dashboard
Provides comprehensive monitoring of scraping progress with statistics and alerts
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple
import subprocess

# ANSI color codes
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def clear_screen():
    """Clear terminal screen"""
    os.system('clear' if os.name == 'posix' else 'cls')

def get_file_stats(output_dir: Path) -> Dict:
    """Get statistics from output files"""
    stats = {
        'csv_files': [],
        'total_records': 0,
        'file_sizes': {},
        'last_modified': None
    }
    
    # Get CSV files
    csv_files = list(output_dir.glob('*.csv'))
    for csv_file in csv_files:
        if csv_file.stat().st_size > 0:
            stats['csv_files'].append(csv_file.name)
            stats['file_sizes'][csv_file.name] = csv_file.stat().st_size
            
            # Count lines (minus header)
            try:
                with open(csv_file, 'r') as f:
                    line_count = sum(1 for line in f) - 1
                    stats['total_records'] += max(0, line_count)
            except:
                pass
            
            # Track last modified
            mtime = datetime.fromtimestamp(csv_file.stat().st_mtime)
            if stats['last_modified'] is None or mtime > stats['last_modified']:
                stats['last_modified'] = mtime
    
    return stats

def parse_log_file(log_file: Path, tail_lines: int = 100) -> Dict:
    """Parse processing log for statistics"""
    stats = {
        'total_processed': 0,
        'total_failed': 0,
        'recent_successes': [],
        'recent_failures': [],
        'workers_active': set(),
        'processing_rate': 0,
        'error_types': {}
    }
    
    if not log_file.exists():
        return stats
    
    # Read entire file for totals
    try:
        with open(log_file, 'r') as f:
            lines = f.readlines()
            
        for line in lines:
            if '✓' in line:
                stats['total_processed'] += 1
            elif '✗' in line:
                stats['total_failed'] += 1
                
            # Track worker activity
            if 'Worker' in line:
                parts = line.split('Worker')
                if len(parts) > 1:
                    worker_num = parts[1].split(':')[0].strip()
                    if worker_num.isdigit():
                        stats['workers_active'].add(int(worker_num))
            
            # Track error types
            if 'Error' in line or 'error' in line:
                error_type = 'Unknown'
                if 'timeout' in line.lower():
                    error_type = 'Timeout'
                elif 'chrome' in line.lower():
                    error_type = 'Chrome Error'
                elif 'connection' in line.lower():
                    error_type = 'Connection'
                stats['error_types'][error_type] = stats['error_types'].get(error_type, 0) + 1
        
        # Get recent entries
        for line in lines[-tail_lines:]:
            if '✓' in line:
                # Extract timestamp if available
                parts = line.split(']')
                if len(parts) > 1:
                    stats['recent_successes'].append(parts[-1].strip())
            elif '✗' in line:
                parts = line.split(']')
                if len(parts) > 1:
                    stats['recent_failures'].append(parts[-1].strip())
                    
    except Exception as e:
        pass
    
    return stats

def parse_checkpoint(checkpoint_file: Path) -> Dict:
    """Parse checkpoint file for progress info"""
    if not checkpoint_file.exists():
        return {}
    
    try:
        with open(checkpoint_file, 'r') as f:
            return json.load(f)
    except:
        return {}

def get_system_stats() -> Dict:
    """Get system resource statistics"""
    stats = {
        'memory': 'N/A',
        'cpu': 'N/A',
        'disk': 'N/A',
        'chrome_processes': 0,
        'python_processes': 0
    }
    
    try:
        # Memory usage
        result = subprocess.run(['free', '-h'], capture_output=True, text=True)
        if result.returncode == 0:
            lines = result.stdout.split('\n')
            if len(lines) > 1:
                mem_parts = lines[1].split()
                if len(mem_parts) >= 3:
                    stats['memory'] = f"{mem_parts[2]}/{mem_parts[1]}"
        
        # Disk usage
        result = subprocess.run(['df', '-h', '.'], capture_output=True, text=True)
        if result.returncode == 0:
            lines = result.stdout.split('\n')
            if len(lines) > 1:
                disk_parts = lines[1].split()
                if len(disk_parts) >= 5:
                    stats['disk'] = f"{disk_parts[2]}/{disk_parts[1]} ({disk_parts[4]})"
        
        # Process counts
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        if result.returncode == 0:
            processes = result.stdout.lower()
            stats['chrome_processes'] = processes.count('chrome') + processes.count('chromium')
            stats['python_processes'] = processes.count('python')
            
    except:
        pass
    
    return stats

def calculate_eta(total_urls: int, processed: int, start_time: datetime) -> str:
    """Calculate estimated time of arrival"""
    if processed == 0:
        return "Calculating..."
    
    elapsed = (datetime.now() - start_time).total_seconds()
    rate = processed / elapsed
    remaining = total_urls - processed
    
    if rate > 0:
        eta_seconds = remaining / rate
        eta = datetime.now() + timedelta(seconds=eta_seconds)
        return eta.strftime("%H:%M:%S")
    
    return "Unknown"

def format_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f}TB"

def display_dashboard(country: str, output_dir: Path, refresh_rate: int = 5):
    """Display monitoring dashboard"""
    start_time = datetime.now()
    
    while True:
        try:
            clear_screen()
            
            # Header
            print(f"{Colors.BOLD}{Colors.HEADER}{'='*80}{Colors.ENDC}")
            print(f"{Colors.BOLD}{Colors.CYAN}   GetOdd Monitoring Dashboard - {country.upper()}{Colors.ENDC}")
            print(f"{Colors.BOLD}{Colors.HEADER}{'='*80}{Colors.ENDC}")
            print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"Running for: {str(datetime.now() - start_time).split('.')[0]}")
            print()
            
            # Check if output directory exists
            if not output_dir.exists():
                print(f"{Colors.YELLOW}⚠ Output directory not found: {output_dir}{Colors.ENDC}")
                print(f"Waiting for scraping to start...")
                time.sleep(refresh_rate)
                continue
            
            # File statistics
            file_stats = get_file_stats(output_dir)
            print(f"{Colors.BOLD}📁 Output Files:{Colors.ENDC}")
            if file_stats['csv_files']:
                for csv_file in sorted(file_stats['csv_files']):
                    size = format_size(file_stats['file_sizes'][csv_file])
                    print(f"  • {csv_file}: {Colors.GREEN}{size}{Colors.ENDC}")
                print(f"  Total records: {Colors.CYAN}{file_stats['total_records']:,}{Colors.ENDC}")
                if file_stats['last_modified']:
                    last_update = (datetime.now() - file_stats['last_modified']).total_seconds()
                    if last_update < 60:
                        print(f"  Last update: {Colors.GREEN}{int(last_update)}s ago{Colors.ENDC}")
                    else:
                        print(f"  Last update: {Colors.YELLOW}{int(last_update/60)}m ago{Colors.ENDC}")
            else:
                print(f"  {Colors.YELLOW}No CSV files yet{Colors.ENDC}")
            print()
            
            # Log statistics
            log_file = output_dir / 'processing_log.txt'
            log_stats = parse_log_file(log_file)
            
            print(f"{Colors.BOLD}📊 Processing Statistics:{Colors.ENDC}")
            success_rate = 0
            if log_stats['total_processed'] + log_stats['total_failed'] > 0:
                success_rate = (log_stats['total_processed'] / 
                              (log_stats['total_processed'] + log_stats['total_failed'])) * 100
            
            print(f"  Successful: {Colors.GREEN}{log_stats['total_processed']}{Colors.ENDC}")
            print(f"  Failed: {Colors.RED}{log_stats['total_failed']}{Colors.ENDC}")
            print(f"  Success rate: {Colors.CYAN}{success_rate:.1f}%{Colors.ENDC}")
            
            if log_stats['workers_active']:
                print(f"  Active workers: {Colors.BLUE}{sorted(log_stats['workers_active'])}{Colors.ENDC}")
            print()
            
            # Checkpoint info
            checkpoint_file = output_dir / 'checkpoint.json'
            checkpoint = parse_checkpoint(checkpoint_file)
            if checkpoint:
                print(f"{Colors.BOLD}🎯 Checkpoint Info:{Colors.ENDC}")
                if 'current_file' in checkpoint:
                    print(f"  Current file: {Colors.CYAN}{Path(checkpoint['current_file']).name}{Colors.ENDC}")
                if 'processed_urls' in checkpoint:
                    print(f"  Processed URLs: {Colors.GREEN}{len(checkpoint['processed_urls'])}{Colors.ENDC}")
                if 'total_urls' in checkpoint and 'processed_urls' in checkpoint:
                    total = checkpoint['total_urls']
                    processed = len(checkpoint['processed_urls'])
                    progress = (processed / total) * 100 if total > 0 else 0
                    eta = calculate_eta(total, processed, start_time)
                    print(f"  Progress: {Colors.CYAN}{processed}/{total} ({progress:.1f}%){Colors.ENDC}")
                    print(f"  ETA: {Colors.YELLOW}{eta}{Colors.ENDC}")
                print()
            
            # System statistics
            sys_stats = get_system_stats()
            print(f"{Colors.BOLD}💻 System Resources:{Colors.ENDC}")
            print(f"  Memory: {Colors.CYAN}{sys_stats['memory']}{Colors.ENDC}")
            print(f"  Disk: {Colors.CYAN}{sys_stats['disk']}{Colors.ENDC}")
            print(f"  Chrome processes: {Colors.BLUE}{sys_stats['chrome_processes']}{Colors.ENDC}")
            print(f"  Python processes: {Colors.BLUE}{sys_stats['python_processes']}{Colors.ENDC}")
            print()
            
            # Recent activity
            if log_stats['recent_successes'] or log_stats['recent_failures']:
                print(f"{Colors.BOLD}📜 Recent Activity:{Colors.ENDC}")
                for success in log_stats['recent_successes'][-3:]:
                    print(f"  {Colors.GREEN}✓{Colors.ENDC} {success[:80]}")
                for failure in log_stats['recent_failures'][-2:]:
                    print(f"  {Colors.RED}✗{Colors.ENDC} {failure[:80]}")
                print()
            
            # Error summary
            if log_stats['error_types']:
                print(f"{Colors.BOLD}⚠️  Error Summary:{Colors.ENDC}")
                for error_type, count in sorted(log_stats['error_types'].items(), 
                                               key=lambda x: x[1], reverse=True):
                    print(f"  {error_type}: {Colors.YELLOW}{count}{Colors.ENDC}")
                print()
            
            # Footer
            print(f"{Colors.HEADER}{'='*80}{Colors.ENDC}")
            print(f"Refreshing every {refresh_rate} seconds. Press Ctrl+C to exit.")
            
            time.sleep(refresh_rate)
            
        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}Monitoring stopped.{Colors.ENDC}")
            break
        except Exception as e:
            print(f"{Colors.RED}Error: {e}{Colors.ENDC}")
            time.sleep(refresh_rate)

def main():
    parser = argparse.ArgumentParser(description='Monitor GetOdd scraping progress')
    parser.add_argument('country', nargs='?', default='switzerland',
                       help='Country being scraped (default: switzerland)')
    parser.add_argument('--refresh', type=int, default=5,
                       help='Refresh rate in seconds (default: 5)')
    parser.add_argument('--output-dir', help='Custom output directory')
    
    args = parser.parse_args()
    
    # Determine output directory
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = Path(f"{args.country}_odds_output")
    
    print(f"Starting monitoring for {args.country}...")
    print(f"Output directory: {output_dir}")
    print()
    
    display_dashboard(args.country, output_dir, args.refresh)

if __name__ == "__main__":
    main()