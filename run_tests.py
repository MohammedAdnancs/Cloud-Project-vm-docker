#!/usr/bin/env python3
"""
Test runner for Cloud VM Manager testing
Runs all tests and generates a report
"""

import unittest
import sys
import os
import time
import datetime
from unittest.mock import patch

# Add the current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import all test modules
from test_disk_manager import TestDiskManager
from test_vm_manager import TestVMManager
from test_docker_manager import TestDockerManager
from test_integration import TestDiskVMIntegration, TestDockerIntegration

def generate_report():
    """Generate a comprehensive test report"""
    # Create test directory if it doesn't exist
    reports_dir = os.path.join('test_reports')
    os.makedirs(reports_dir, exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = os.path.join(reports_dir, f"cloud_vm_manager_test_report_{timestamp}.txt")
    
    # Set up the test suite
    test_loader = unittest.TestLoader()
    test_suite = unittest.TestSuite()
    
    # Add test cases to the suite
    test_suite.addTests([
        test_loader.loadTestsFromTestCase(TestDiskManager),
        test_loader.loadTestsFromTestCase(TestVMManager),
        test_loader.loadTestsFromTestCase(TestDockerManager),
        test_loader.loadTestsFromTestCase(TestDiskVMIntegration),
        test_loader.loadTestsFromTestCase(TestDockerIntegration)
    ])
    
    # Run the tests and generate report
    with open(report_path, 'w') as f:
        f.write(f"Cloud VM Manager Test Report\n")
        f.write(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"{'='*50}\n\n")
        
        # Create a runner with the file as output
        runner = unittest.TextTestRunner(stream=f, verbosity=2)
        
        # Apply global patches for external dependencies
        with patch('subprocess.run'), patch('subprocess.Popen'):
            # Run the tests
            result = runner.run(test_suite)
        
        # Add summary section to the report
        f.write("\n\n")
        f.write(f"{'='*50}\n")
        f.write("TEST SUMMARY\n")
        f.write(f"{'='*50}\n")
        f.write(f"Total tests: {result.testsRun}\n")
        f.write(f"Passed: {result.testsRun - len(result.errors) - len(result.failures)}\n")
        f.write(f"Failed: {len(result.failures)}\n")
        f.write(f"Errors: {len(result.errors)}\n")
    
    # Also print summary to console
    print("\n===== TEST SUMMARY =====")
    print(f"Total tests: {result.testsRun}")
    print(f"Passed: {result.testsRun - len(result.errors) - len(result.failures)}")
    print(f"Failed: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    print(f"\nTest report generated at: {report_path}")
    
    # Return the test result
    return result

if __name__ == "__main__":
    print("Running Cloud VM Manager tests...")
    
    try:
        # Run tests and generate report
        result = generate_report()
        
        # Return exit code based on test results
        if result.failures or result.errors:
            sys.exit(1)
        else:
            sys.exit(0)
    except Exception as e:
        print(f"Error running tests: {str(e)}")
        sys.exit(1) 