#!/bin/bash
# Test runner script for Music-stats project

# Set colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🎵 Music-stats Test Suite Runner${NC}"
echo "=================================="

# Set PYTHONPATH
export PYTHONPATH=.

# Parse command line arguments
COVERAGE=false
VERBOSE=false
SPECIFIC_TEST=""
FAIL_FAST=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --coverage|-c)
            COVERAGE=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --test|-t)
            SPECIFIC_TEST="$2"
            shift 2
            ;;
        --fail-fast|-x)
            FAIL_FAST=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  -c, --coverage    Run tests with coverage report"
            echo "  -v, --verbose     Run tests in verbose mode"
            echo "  -t, --test FILE   Run specific test file"
            echo "  -x, --fail-fast   Stop on first failure"
            echo "  -h, --help        Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Build pytest command
PYTEST_CMD="pytest"

if [ "$SPECIFIC_TEST" != "" ]; then
    PYTEST_CMD="$PYTEST_CMD tests/$SPECIFIC_TEST"
else
    PYTEST_CMD="$PYTEST_CMD tests/"
fi

if [ "$VERBOSE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -v"
fi

if [ "$FAIL_FAST" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -x"
fi

if [ "$COVERAGE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD --cov=app --cov-report=term-missing --cov-report=html"
    echo -e "${BLUE}Running tests with coverage...${NC}"
else
    PYTEST_CMD="$PYTEST_CMD --disable-warnings"
    echo -e "${BLUE}Running tests...${NC}"
fi

# Run the tests
if eval $PYTEST_CMD; then
    echo -e "${GREEN}✅ All tests passed!${NC}"
    
    if [ "$COVERAGE" = true ]; then
        echo -e "${BLUE}📊 Coverage report generated in htmlcov/index.html${NC}"
    fi
    
    exit 0
else
    echo -e "${RED}❌ Some tests failed!${NC}"
    exit 1
fi
