#!/usr/bin/env python3
"""
Pandas Build Issue Resolver - Complete Solution Package
Handles installation issues, web research, and automated ticket generation
"""

import requests
from bs4 import BeautifulSoup
import re
import time
from datetime import datetime
import json
import subprocess
import sys
import os
from pathlib import Path
import argparse

class ComprehensivePandasResolver:
    def __init__(self):
        self.issue_data = {
            'title': 'Pandas Build Failure: Comprehensive Analysis and Solutions',
            'description': '',
            'environment': {},
            'error_type': 'Build/Installation',
            'severity': 'Medium',
            'reproducibility': 'Consistent',
            'references': [],
            'solutions_tried': []
        }
        self.setup_environment_info()
    
    def setup_environment_info(self):
        """Gather comprehensive environment information"""
        try:
            import platform
            self.issue_data['environment'] = {
                'python_version': sys.version,
                'platform': platform.platform(),
                'processor': platform.processor(),
                'pip_version': self.get_pip_version(),
                'setuptools_version': self.get_setuptools_version()
            }
        except Exception as e:
            self.issue_data['environment'] = {'error': str(e)}
    
    def get_pip_version(self):
        """Get pip version"""
        try:
            result = subprocess.run([sys.executable, '-m', 'pip', '--version'], 
                                  capture_output=True, text=True)
            return result.stdout.strip()
        except:
            return "Unknown"
    
    def get_setuptools_version(self):
        """Get setuptools version"""
        try:
            import setuptools
            return setuptools.__version__
        except:
            return "Unknown"
    
    def enhanced_web_scraper(self, queries):
        """Enhanced web scraper with multiple sources"""
        all_results = []
        
        for query in queries:
            print(f"🔍 Searching: {query}")
            
            # Stack Overflow
            so_results = self.scrape_stackoverflow(query)
            all_results.extend(so_results)
            
            # GitHub Issues
            gh_results = self.scrape_github_issues(query=query)
            all_results.extend(gh_results)
            
            # Python Package Index (PyPI)
            pypi_results = self.check_pypi_compatibility()
            all_results.extend(pypi_results)
            
            time.sleep(1)  # Be respectful to servers
        
        # Remove duplicates
        unique_results = []
        seen_urls = set()
        for result in all_results:
            if result['url'] not in seen_urls:
                unique_results.append(result)
                seen_urls.add(result['url'])
        
        return unique_results
    
    def scrape_stackoverflow(self, query):
        """Scrape Stack Overflow with enhanced error handling"""
        try:
            search_url = f"https://api.stackexchange.com/2.3/search/advanced"
            params = {
                'order': 'desc',
                'sort': 'relevance',
                'q': query,
                'site': 'stackoverflow',
                'pagesize': 5
            }
            
            response = requests.get(search_url, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                results = []
                for item in data.get('items', []):
                    results.append({
                        'title': item['title'],
                        'url': item['link'],
                        'source': 'Stack Overflow',
                        'score': item.get('score', 0),
                        'answer_count': item.get('answer_count', 0)
                    })
                return results
        except Exception as e:
            print(f"Stack Overflow API failed: {e}")
        
        # Fallback to HTML scraping
        try:
            search_url = f"https://stackoverflow.com/search?q={query.replace(' ', '+')}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(search_url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            results = []
            for item in soup.select('.question-hyperlink')[:5]:
                title = item.get_text()
                link = "https://stackoverflow.com" + item.get('href')
                results.append({
                    'title': title,
                    'url': link,
                    'source': 'Stack Overflow',
                    'score': 0,
                    'answer_count': 0
                })
            
            return results
        except Exception as e:
            print(f"Stack Overflow scraping failed: {e}")
            return []
    
    def scrape_github_issues(self, repo="pandas-dev/pandas", query=""):
        """Enhanced GitHub issues scraper"""
        try:
            search_url = f"https://api.github.com/search/issues"
            params = {
                'q': f'repo:{repo} {query}',
                'sort': 'created',
                'order': 'desc',
                'per_page': 5
            }
            headers = {
                'Accept': 'application/vnd.github.v3+json',
                'User-Agent': 'Pandas-Build-Helper/1.0'
            }
            
            response = requests.get(search_url, params=params, headers=headers, timeout=15)
            if response.status_code == 200:
                data = response.json()
                results = []
                for item in data.get('items', []):
                    results.append({
                        'title': item['title'],
                        'url': item['html_url'],
                        'source': 'GitHub',
                        'state': item['state'],
                        'created_at': item['created_at']
                    })
                return results
        except Exception as e:
            print(f"GitHub API failed: {e}")
        
        # HTML fallback
        try:
            search_url = f"https://github.com/{repo}/issues?q={query.replace(' ', '+')}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(search_url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            results = []
            for item in soup.select('[data-hovercard-type="issue"]')[:5]:
                title = item.get_text().strip()
                link = "https://github.com" + item.get('href')
                results.append({
                    'title': title,
                    'url': link,
                    'source': 'GitHub',
                    'state': 'unknown',
                    'created_at': 'unknown'
                })
            
            return results
        except Exception as e:
            print(f"GitHub scraping failed: {e}")
            return []
    
    def check_pypi_compatibility(self):
        """Check PyPI for pandas compatibility information"""
        try:
            url = "https://pypi.org/pypi/pandas/json"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                info = data.get('info', {})
                
                return [{
                    'title': f"PyPI: pandas {info.get('version', 'unknown')} - {info.get('summary', '')}",
                    'url': f"https://pypi.org/project/pandas/{info.get('version', '')}/",
                    'source': 'PyPI',
                    'requires_python': info.get('requires_python', 'Not specified')
                }]
        except Exception as e:
            print(f"PyPI check failed: {e}")
        
        return []
    
    def deep_log_analysis(self, log_content):
        """Comprehensive log analysis with pattern matching"""
        analysis = {
            'critical_issues': [],
            'warnings': [],
            'suggestions': [],
            'statistics': {}
        }
        
        # Pattern matching for different issue types
        patterns = {
            'numpy_headers': r"dependency.*numpy.*won't be automatically included",
            'package_config': r"Package.*is absent from the.*packages.*configuration",
            'compilation_error': r"error:|Error:|ERROR:",
            'warning_messages': r"warning:|Warning:|WARNING:",
            'python_version': r"python3\.(\d+)",
            'build_success': r"Successfully installed|Running setup\.py install for",
            'missing_dependencies': r"ModuleNotFoundError|ImportError"
        }
        
        for category, pattern in patterns.items():
            matches = re.findall(pattern, log_content, re.IGNORECASE)
            analysis['statistics'][category] = len(matches)
            
            if category == 'numpy_headers' and matches:
                analysis['critical_issues'].append(f"NumPy header path issues: {len(matches)} warnings")
            elif category == 'package_config' and matches:
                analysis['warnings'].append(f"Package configuration issues: {len(matches)} warnings")
            elif category == 'compilation_error' and matches:
                analysis['critical_issues'].append(f"Compilation errors: {len(matches)} found")
            elif category == 'build_success' and matches:
                analysis['suggestions'].append("Build completed (with warnings)")
        
        # Additional analysis
        if analysis['statistics'].get('numpy_headers', 0) > 50:
            analysis['critical_issues'].append("High volume of NumPy header warnings - potential path configuration issue")
        
        return analysis
    
    def execute_solution(self, solution_name, commands):
        """Execute a solution and track results"""
        print(f"🚀 Executing: {solution_name}")
        
        results = {
            'solution': solution_name,
            'commands': commands,
            'outputs': [],
            'success': False,
            'error': None
        }
        
        try:
            for command in commands:
                if command.startswith('#'):
                    print(f"  💡 {command}")
                    continue
                    
                if command.strip() in ['', 'or']:
                    continue
                    
                print(f"  ▶️  Running: {command}")
                
                # Execute command
                if command.startswith('pip install'):
                    result = subprocess.run(
                        command.split(),
                        capture_output=True,
                        text=True,
                        timeout=300  # 5 minute timeout
                    )
                    
                    results['outputs'].append({
                        'command': command,
                        'returncode': result.returncode,
                        'stdout': result.stdout,
                        'stderr': result.stderr
                    })
                    
                    if result.returncode == 0:
                        print(f"    ✅ Success: {command}")
                        results['success'] = True
                    else:
                        print(f"    ❌ Failed: {command}")
                        results['error'] = result.stderr
                else:
                    print(f"    ⚠️  Skipping (non-pip command): {command}")
        
        except subprocess.TimeoutExpired:
            results['error'] = "Command timed out after 5 minutes"
        except Exception as e:
            results['error'] = str(e)
        
        self.issue_data['solutions_tried'].append(results)
        return results
    
    def get_comprehensive_solutions(self):
        """Get all possible solutions with prioritization"""
        return [
            {
                'priority': 1,
                'title': 'Quick Fix - Pre-built Wheels',
                'description': 'Use pre-compiled wheels to avoid build issues',
                'commands': [
                    '# Try installing with pre-built wheels',
                    'pip install --upgrade pip',
                    'pip install --only-binary=all pandas',
                    '# Verify installation',
                    'python -c "import pandas; print(f\"Pandas version: {pandas.__version__}\")"'
                ]
            },
            {
                'priority': 2,
                'title': 'Build Dependencies Setup',
                'description': 'Ensure all build dependencies are properly installed',
                'commands': [
                    '# Upgrade build tools',
                    'pip install --upgrade pip setuptools wheel',
                    '# Install build dependencies',
                    'pip install numpy cython',
                    '# Install pandas with build isolation',
                    'pip install pandas --no-build-isolation',
                    '# Alternative: build in development mode',
                    'pip install -e . --no-build-isolation'
                ]
            },
            {
                'priority': 3,
                'title': 'System Library Installation',
                'description': 'Install system-level dependencies',
                'commands': [
                    '# For Ubuntu/Debian systems',
                    '# sudo apt-get update',
                    '# sudo apt-get install build-essential python3-dev',
                    '# For CentOS/RHEL systems', 
                    '# sudo yum groupinstall "Development Tools"',
                    '# sudo yum install python3-devel',
                    '# Then retry pandas installation',
                    'pip install pandas'
                ]
            },
            {
                'priority': 4,
                'title': 'Version-Specific Installation',
                'description': 'Install specific compatible versions',
                'commands': [
                    '# Install specific pandas version',
                    'pip install "pandas<2.2"',
                    '# Or try the latest pre-release',
                    'pip install --pre pandas',
                    '# Install with version constraints',
                    'pip install "pandas>=2.1,<2.2" "numpy>=1.21,<1.25"'
                ]
            },
            {
                'priority': 5,
                'title': 'Alternative Installation Methods',
                'description': 'Try different installation approaches',
                'commands': [
                    '# Using conda (if available)',
                    '# conda install pandas',
                    '# conda install -c conda-forge pandas',
                    '# Using pip with cache clearance',
                    'pip cache purge',
                    'pip install pandas --no-cache-dir',
                    '# Install from GitHub main branch',
                    '# pip install git+https://github.com/pandas-dev/pandas.git'
                ]
            }
        ]
    
    def generate_comprehensive_report(self, log_analysis, references, solutions_executed):
        """Generate a comprehensive report with all findings"""
        
        # Executive Summary
        critical_count = len(log_analysis['critical_issues'])
        warning_count = len(log_analysis['warnings'])
        
        report = f"""
# 🐼 Pandas Build Issue Resolution Report

## 📊 Executive Summary
- **Critical Issues Found**: {critical_count}
- **Warnings Identified**: {warning_count}  
- **Solutions Attempted**: {len(solutions_executed)}
- **References Collected**: {len(references)}

---

## 🔍 Detailed Analysis

### Environment Information
```json
{json.dumps(self.issue_data['environment'], indent=2)}
