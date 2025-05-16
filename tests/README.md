# Cloud VM Manager - Test Suite

This directory contains the test suite for the Cloud VM Manager application. The tests cover all major components of the application and their interactions.

## Overview

The test suite includes:

- **Unit tests** for individual components:
  - `test_disk_manager.py`: Tests for the disk management functionality
  - `test_vm_manager.py`: Tests for the VM management functionality
  - `test_docker_manager.py`: Tests for the Docker management functionality

- **Integration tests**:
  - `test_integration.py`: Tests for component interactions and workflows

- **Test runner and reporting**:
  - `run_tests.py`: Script to run all tests and generate a report

## Prerequisites

Before running the tests, ensure you have the following:

1. Python 3.8 or higher
2. No additional packages are required for basic testing

For HTML reports (optional):
```
pip install html-testRunner
```

## Running the Tests

### Running All Tests

To run the complete test suite:

```bash
python run_tests.py
```

This will:
- Run all unit and integration tests
- Generate a text report in the `test_reports` directory
- Provide a summary of the results in the console

### Running Individual Test Modules

To run specific test modules:

```bash
python -m unittest test_disk_manager.py
python -m unittest test_vm_manager.py
python -m unittest test_docker_manager.py
python -m unittest test_integration.py
```

### Running Specific Tests

To run a specific test case or method:

```bash
# Run a specific test class
python -m unittest test_disk_manager.TestDiskManager

# Run a specific test method
python -m unittest test_disk_manager.TestDiskManager.test_create_disk_success
```

## Test Reports

The test runner generates a comprehensive text report with:
- Detailed test results
- Error messages and tracebacks for failed tests
- Summary statistics

Reports are saved in the `test_reports` directory with timestamps in their filenames.

The report format follows standard unittest text output with additional summary information.

## Interpreting Test Results

The test results include:

- **Total Tests**: Number of test methods executed
- **Passed**: Number of tests that passed
- **Failed**: Number of tests that failed assertions
- **Errors**: Number of tests that encountered exceptions

## Modifying Tests

When modifying the application code, ensure the tests are updated to reflect the changes:

1. Update test cases that depend on modified functionality
2. Add new tests for added features
3. Remove tests for removed functionality

## Mock Dependencies

The tests use Python's unittest.mock module to mock external dependencies:

- External processes (subprocess.run, subprocess.Popen)
- File system operations for isolation

This ensures that:
- Tests run in a controlled environment
- External systems are not affected
- Tests are reproducible

## Test Data

Tests create their own isolated test data in the `test_data` directory, which is cleaned up after each test run.

## Troubleshooting

If tests are failing, check:

1. That the application code matches the expectations in the tests
2. That dependencies are correctly installed
3. That the test environment is properly set up

For detailed error information, refer to the generated test reports.

## Continuous Integration

These tests can be integrated into a CI/CD pipeline by running:

```bash
python run_tests.py
```

The script returns exit code 0 if all tests pass, or non-zero if any tests fail or encounter errors. 