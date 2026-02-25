#!/bin/bash
# Verification Script for Phase 95.1 Cleanup
# Run before executing any code deletions

set -e

echo "=================================================="
echo "PHASE 95.1 CLEANUP VERIFICATION SCRIPT"
echo "=================================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ERRORS=0
WARNINGS=0

# Helper functions
print_check() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
    ((ERRORS++))
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
    ((WARNINGS++))
}

echo ""
echo "== 1. Checking File Existence =="
echo ""

# Check if files exist
if [ -f "src/elisya/api_gateway.py" ]; then
    print_check "api_gateway.py exists"
else
    print_error "api_gateway.py NOT FOUND"
fi

if [ -f "src/elisya/api_aggregator_v3.py" ]; then
    print_check "api_aggregator_v3.py exists"
else
    print_error "api_aggregator_v3.py NOT FOUND"
fi

if [ -f "src/initialization/dependency_check.py" ]; then
    print_check "dependency_check.py exists"
else
    print_error "dependency_check.py NOT FOUND"
fi

if [ -f "src/initialization/components_init.py" ]; then
    print_check "components_init.py exists"
else
    print_error "components_init.py NOT FOUND"
fi

echo ""
echo "== 2. Searching for Code to Delete (CLEANUP-AGG-001) =="
echo ""

if grep -q "class OpenRouterProvider(APIProvider):" src/elisya/api_aggregator_v3.py 2>/dev/null; then
    print_check "OpenRouterProvider class found (ready for deletion)"
else
    print_error "OpenRouterProvider class NOT FOUND in expected location"
fi

echo ""
echo "== 3. Searching for Boilerplate Methods (CLEANUP-AGG-002) =="
echo ""

if grep -q "def add_key(" src/elisya/api_aggregator_v3.py 2>/dev/null; then
    print_check "add_key() method found"

    # Verify it's not called anywhere
    if grep -r "\.add_key(" src/ --include="*.py" 2>/dev/null | grep -v "def add_key" | grep -v "#"; then
        print_error "add_key() IS CALLED somewhere (safe to delete)"
        ((ERRORS++))
    else
        print_check "add_key() is NOT called anywhere (safe to delete)"
    fi
else
    print_warning "add_key() method NOT FOUND (may already be deleted)"
fi

echo ""
echo "== 4. Searching for PROVIDER_CLASSES (CLEANUP-AGG-003) =="
echo ""

if grep -q "PROVIDER_CLASSES = {" src/elisya/api_aggregator_v3.py 2>/dev/null; then
    print_check "PROVIDER_CLASSES dict found"

    # Verify it's not used anywhere
    if grep -r "PROVIDER_CLASSES" src/ --include="*.py" 2>/dev/null | grep -v "PROVIDER_CLASSES = {" | grep -v "#"; then
        print_error "PROVIDER_CLASSES IS REFERENCED somewhere"
        ((ERRORS++))
    else
        print_check "PROVIDER_CLASSES is NOT referenced anywhere (safe to delete)"
    fi
else
    print_warning "PROVIDER_CLASSES dict NOT FOUND (may already be deleted)"
fi

echo ""
echo "== 5. Checking for api_gateway Usage (CLEANUP-GW-001) =="
echo ""

# Count api_gateway references
GATEWAY_REFS=$(grep -r "api_gateway" src/ --include="*.py" 2>/dev/null | wc -l)
echo "Total 'api_gateway' references in code: $GATEWAY_REFS"

if grep -r "\.call_model(" src/ --include="*.py" 2>/dev/null | grep -v "test" | grep -v "#"; then
    print_warning "Found .call_model() calls (check if these are APIGateway)"
else
    print_check "No suspicious .call_model() calls found"
fi

echo ""
echo "== 6. Checking Direct API Functions (CLEANUP-GW-004) =="
echo ""

# Check if direct API functions exist
if grep -q "async def call_openai_direct" src/elisya/api_gateway.py 2>/dev/null; then
    print_check "call_openai_direct() found in api_gateway.py"
else
    print_error "call_openai_direct() NOT FOUND"
fi

if grep -q "async def call_anthropic_direct" src/elisya/api_gateway.py 2>/dev/null; then
    print_check "call_anthropic_direct() found in api_gateway.py"
else
    print_error "call_anthropic_direct() NOT FOUND"
fi

if grep -q "async def call_google_direct" src/elisya/api_gateway.py 2>/dev/null; then
    print_check "call_google_direct() found in api_gateway.py"
else
    print_error "call_google_direct() NOT FOUND"
fi

# Check if these are imported in api_aggregator_v3.py
if grep -q "from src.elisya.api_gateway import call_openai_direct" src/elisya/api_aggregator_v3.py 2>/dev/null; then
    print_check "call_openai_direct imported in api_aggregator_v3.py"
else
    print_warning "call_openai_direct NOT imported as expected (may be wrong import path)"
fi

echo ""
echo "== 7. Checking init_api_gateway Usage (CLEANUP-GW-003) =="
echo ""

# Find where init_api_gateway is called
INIT_CALLS=$(grep -r "init_api_gateway" src/ --include="*.py" 2>/dev/null | grep -v "def init_api_gateway" | grep -v "#" | grep -v ".get('init')")
if [ -n "$INIT_CALLS" ]; then
    print_warning "init_api_gateway called at:"
    echo "$INIT_CALLS"
else
    print_check "init_api_gateway is NOT directly called (safe to delete)"
fi

echo ""
echo "== 8. Checking dependency_check.py (CLEANUP-DEP-001) =="
echo ""

if grep -q "from src.elisya.api_gateway import init_api_gateway" src/initialization/dependency_check.py 2>/dev/null; then
    print_check "api_gateway import check found in dependency_check.py"
else
    print_warning "api_gateway import check NOT FOUND (may already be deleted)"
fi

echo ""
echo "== 9. Checking components_init.py References =="
echo ""

COMPONENTS_REFS=$(grep -c "api_gateway" src/initialization/components_init.py 2>/dev/null || echo 0)
echo "Found $COMPONENTS_REFS references to api_gateway in components_init.py"

if grep -q "API_GATEWAY_AVAILABLE" src/initialization/components_init.py 2>/dev/null; then
    print_check "API_GATEWAY_AVAILABLE flag found"
else
    print_warning "API_GATEWAY_AVAILABLE flag NOT FOUND"
fi

echo ""
echo "== 10. Checking health_routes.py References =="
echo ""

if grep -q "'api_gateway'" src/api/routes/health_routes.py 2>/dev/null; then
    print_check "'api_gateway' component reference found in health_routes.py"
else
    print_warning "'api_gateway' component reference NOT FOUND"
fi

echo ""
echo "== 11. Unused Imports Check (CLEANUP-GW-002) =="
echo ""

# Check for Tuple import
if grep -q "from typing import.*Tuple" src/elisya/api_gateway.py 2>/dev/null; then
    print_check "Tuple imported in api_gateway.py"

    # Verify it's not used
    if grep -q "Tuple\[" src/elisya/api_gateway.py 2>/dev/null; then
        print_error "Tuple IS USED in api_gateway.py (don't delete import)"
        ((ERRORS++))
    else
        print_check "Tuple is imported but NOT USED (can delete)"
    fi
fi

# Check for timedelta import
if grep -q "timedelta" src/elisya/api_gateway.py 2>/dev/null; then
    print_check "timedelta imported in api_gateway.py"

    # Count usage
    TIMEDELTA_USAGE=$(grep -c "timedelta(" src/elisya/api_gateway.py 2>/dev/null || echo 0)
    if [ "$TIMEDELTA_USAGE" -eq 0 ]; then
        print_check "timedelta is imported but NOT USED (can delete)"
    else
        print_error "timedelta IS USED $TIMEDELTA_USAGE times (don't delete import)"
        ((ERRORS++))
    fi
fi

echo ""
echo "== 12. Archive Check =="
echo ""

if [ -d "docs/95_ph/archived_code" ]; then
    print_check "Archive directory exists"
else
    print_warning "Archive directory does NOT exist (will be created)"
fi

echo ""
echo "=================================================="
echo "SUMMARY"
echo "=================================================="
echo -e "Errors found: ${RED}$ERRORS${NC}"
echo -e "Warnings: ${YELLOW}$WARNINGS${NC}"
echo ""

if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✓ READY FOR CLEANUP${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Review CLEANUP_QUICK_REFERENCE.md"
    echo "2. Create src/elisya/direct_api_calls.py (move 3 functions)"
    echo "3. Update imports in api_aggregator_v3.py"
    echo "4. Run cleanup steps in order"
    echo "5. Run pytest tests/ -v to verify"
    exit 0
else
    echo -e "${RED}✗ ISSUES FOUND - DO NOT PROCEED${NC}"
    echo ""
    echo "Fix issues before running cleanup"
    exit 1
fi
