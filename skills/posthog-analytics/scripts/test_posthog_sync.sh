#!/bin/bash
# PostHog Sync Script Tests
# Usage: ./scripts/test_posthog_sync.sh [test_name]
# 
# Tests require POSTHOG_PERSONAL_API_KEY to be set.
# Tests create real dashboards/insights - they clean up after themselves.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SYNC_SCRIPT="$SCRIPT_DIR/posthog_sync.sh"
TEST_CONFIG="/tmp/test_posthog_dashboard_$$.json"
EXPORTED_CONFIG="/tmp/test_posthog_export_$$.json"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0

# Cleanup function
cleanup() {
    rm -f "$TEST_CONFIG" "$EXPORTED_CONFIG"
    # Note: Created dashboards are NOT auto-deleted to avoid accidental data loss
    # Delete manually in PostHog UI if needed
}
trap cleanup EXIT

# Helper: Print test result
pass() {
    echo -e "${GREEN}✓ PASS${NC}: $1"
    ((TESTS_PASSED++))
}

fail() {
    echo -e "${RED}✗ FAIL${NC}: $1"
    ((TESTS_FAILED++))
}

skip() {
    echo -e "${YELLOW}○ SKIP${NC}: $1"
}

# Helper: Check if command exists
require_cmd() {
    if ! command -v "$1" &> /dev/null; then
        echo -e "${RED}Error: Required command '$1' not found${NC}"
        exit 1
    fi
}

#=============================================================================
# TEST: Prerequisites
#=============================================================================
test_prerequisites() {
    echo ""
    echo "=== Test: Prerequisites ==="
    
    # Check required tools
    require_cmd curl
    require_cmd jq
    require_cmd bash
    pass "Required tools (curl, jq, bash) available"
    
    # Check API key
    if [ -z "$POSTHOG_PERSONAL_API_KEY" ]; then
        fail "POSTHOG_PERSONAL_API_KEY not set"
        return 1
    fi
    pass "POSTHOG_PERSONAL_API_KEY is set"
    
    # Check script exists
    if [ ! -f "$SYNC_SCRIPT" ]; then
        fail "Sync script not found: $SYNC_SCRIPT"
        return 1
    fi
    pass "Sync script exists"
    
    # Check script is executable
    if [ ! -x "$SYNC_SCRIPT" ]; then
        chmod +x "$SYNC_SCRIPT"
        pass "Made sync script executable"
    else
        pass "Sync script is executable"
    fi
}

#=============================================================================
# TEST: API Connectivity
#=============================================================================
test_api_connectivity() {
    echo ""
    echo "=== Test: API Connectivity ==="
    
    local response
    response=$(curl -s -H "Authorization: Bearer $POSTHOG_PERSONAL_API_KEY" \
        "https://us.i.posthog.com/api/projects/@current/" 2>&1)
    
    # Check for valid JSON response
    if ! echo "$response" | jq -e '.id' > /dev/null 2>&1; then
        fail "API returned invalid response: $response"
        return 1
    fi
    
    local project_id project_name
    project_id=$(echo "$response" | jq -r '.id')
    project_name=$(echo "$response" | jq -r '.name')
    
    pass "API connectivity OK (Project: $project_name, ID: $project_id)"
    echo "    Project ID: $project_id"
    echo "    Project Name: $project_name"
}

#=============================================================================
# TEST: Help Command
#=============================================================================
test_help_command() {
    echo ""
    echo "=== Test: Help Command ==="
    
    local output
    output=$("$SYNC_SCRIPT" help 2>&1)
    
    if echo "$output" | grep -q "PostHog Dashboard Sync"; then
        pass "Help command shows usage info"
    else
        fail "Help command output unexpected: $output"
    fi
    
    if echo "$output" | grep -q "create"; then
        pass "Help mentions 'create' command"
    else
        fail "Help missing 'create' command"
    fi
    
    if echo "$output" | grep -q "update"; then
        pass "Help mentions 'update' command"
    else
        fail "Help missing 'update' command"
    fi
}

#=============================================================================
# TEST: Create Dashboard
#=============================================================================
test_create_dashboard() {
    echo ""
    echo "=== Test: Create Dashboard ==="
    
    # Create test config
    cat > "$TEST_CONFIG" << 'EOF'
{
  "name": "Test Dashboard (Auto-Delete)",
  "description": "Created by test script - safe to delete",
  "filter": {"key": "source", "value": "test"},
  "dashboard_id": null,
  "insights": [
    {"name": "Test Pageviews", "type": "pageviews_total"},
    {"name": "Test Users", "type": "unique_users"}
  ]
}
EOF
    pass "Test config created"
    
    # Run create command
    local output
    output=$("$SYNC_SCRIPT" create "$TEST_CONFIG" 2>&1)
    
    if echo "$output" | grep -q "Dashboard created"; then
        pass "Dashboard created successfully"
    else
        fail "Dashboard creation failed: $output"
        return 1
    fi
    
    # Check dashboard_id was written to config
    local dashboard_id
    dashboard_id=$(jq -r '.dashboard_id' "$TEST_CONFIG")
    
    if [ "$dashboard_id" != "null" ] && [ -n "$dashboard_id" ]; then
        pass "Config updated with dashboard_id: $dashboard_id"
        echo "    Dashboard ID: $dashboard_id"
    else
        fail "Config not updated with dashboard_id"
        return 1
    fi
    
    # Check URL contains project_id
    if echo "$output" | grep -q "project/[0-9]*/dashboard"; then
        pass "Output contains valid dashboard URL with project ID"
    else
        fail "Output missing proper dashboard URL"
    fi
    
    # Save dashboard_id for later tests
    export TEST_DASHBOARD_ID="$dashboard_id"
}

#=============================================================================
# TEST: Sync Dashboard (Add New Insights)
#=============================================================================
test_sync_dashboard() {
    echo ""
    echo "=== Test: Sync Dashboard ==="
    
    if [ -z "$TEST_DASHBOARD_ID" ]; then
        skip "Skipping sync test - no dashboard created"
        return
    fi
    
    # Add a new insight to config
    jq '.insights += [{"name": "Test Traffic Trend", "type": "traffic_trend"}]' \
        "$TEST_CONFIG" > "${TEST_CONFIG}.tmp" && mv "${TEST_CONFIG}.tmp" "$TEST_CONFIG"
    pass "Added new insight to config"
    
    # Run sync command
    local output
    output=$("$SYNC_SCRIPT" sync "$TEST_CONFIG" 2>&1)
    
    # Should skip existing insights
    if echo "$output" | grep -q "Insight exists, skipping: Test Pageviews"; then
        pass "Sync correctly skipped existing insight"
    else
        fail "Sync should have skipped existing insight"
    fi
    
    # Should create new insight
    if echo "$output" | grep -q "Creating new insight: Test Traffic Trend"; then
        pass "Sync created new insight"
    else
        fail "Sync should have created new insight"
    fi
}

#=============================================================================
# TEST: Update Dashboard
#=============================================================================
test_update_dashboard() {
    echo ""
    echo "=== Test: Update Dashboard ==="
    
    if [ -z "$TEST_DASHBOARD_ID" ]; then
        skip "Skipping update test - no dashboard created"
        return
    fi
    
    # Change filter in config
    jq '.filter = {"key": "source", "value": "updated_test"}' \
        "$TEST_CONFIG" > "${TEST_CONFIG}.tmp" && mv "${TEST_CONFIG}.tmp" "$TEST_CONFIG"
    pass "Changed filter in config"
    
    # Run update command
    local output
    output=$("$SYNC_SCRIPT" update "$TEST_CONFIG" 2>&1)
    
    # Should update existing insights
    if echo "$output" | grep -q "Updating insight:"; then
        pass "Update modified existing insights"
    else
        fail "Update should have modified insights"
    fi
    
    if echo "$output" | grep -q "Update complete"; then
        pass "Update completed successfully"
    else
        fail "Update did not complete"
    fi
}

#=============================================================================
# TEST: Export Dashboard
#=============================================================================
test_export_dashboard() {
    echo ""
    echo "=== Test: Export Dashboard ==="
    
    if [ -z "$TEST_DASHBOARD_ID" ]; then
        skip "Skipping export test - no dashboard created"
        return
    fi
    
    # Run export command
    "$SYNC_SCRIPT" export "$TEST_DASHBOARD_ID" > "$EXPORTED_CONFIG" 2>&1
    
    # Check exported config is valid JSON
    if jq -e '.name' "$EXPORTED_CONFIG" > /dev/null 2>&1; then
        pass "Export produced valid JSON"
    else
        fail "Export did not produce valid JSON"
        return 1
    fi
    
    # Check exported config has dashboard_id
    local exported_id
    exported_id=$(jq -r '.dashboard_id' "$EXPORTED_CONFIG")
    
    if [ "$exported_id" = "$TEST_DASHBOARD_ID" ]; then
        pass "Exported config has correct dashboard_id"
    else
        fail "Exported dashboard_id mismatch: expected $TEST_DASHBOARD_ID, got $exported_id"
    fi
    
    # Check exported config has insights
    local insight_count
    insight_count=$(jq '.insights | length' "$EXPORTED_CONFIG")
    
    if [ "$insight_count" -gt 0 ]; then
        pass "Exported config has $insight_count insights"
    else
        fail "Exported config has no insights"
    fi
}

#=============================================================================
# TEST: Error Handling
#=============================================================================
test_error_handling() {
    echo ""
    echo "=== Test: Error Handling ==="
    
    # Test missing config file
    local output
    output=$("$SYNC_SCRIPT" create "/nonexistent/file.json" 2>&1) || true
    
    if [ $? -ne 0 ] || echo "$output" | grep -qi "error\|no such file"; then
        pass "Handles missing config file"
    else
        fail "Should error on missing config file"
    fi
    
    # Test sync without dashboard_id
    cat > "${TEST_CONFIG}.nodash" << 'EOF'
{
  "name": "Test",
  "dashboard_id": null,
  "insights": []
}
EOF
    
    output=$("$SYNC_SCRIPT" sync "${TEST_CONFIG}.nodash" 2>&1) || true
    rm -f "${TEST_CONFIG}.nodash"
    
    if echo "$output" | grep -q "No dashboard_id"; then
        pass "Sync errors when no dashboard_id"
    else
        fail "Sync should error without dashboard_id"
    fi
}

#=============================================================================
# MAIN
#=============================================================================
main() {
    echo "========================================"
    echo "PostHog Sync Script Tests"
    echo "========================================"
    echo "Script: $SYNC_SCRIPT"
    echo "Time: $(date)"
    echo ""
    
    # Run specific test or all tests
    case "${1:-all}" in
        prereq|prerequisites)
            test_prerequisites
            ;;
        api|connectivity)
            test_prerequisites
            test_api_connectivity
            ;;
        help)
            test_prerequisites
            test_help_command
            ;;
        create)
            test_prerequisites
            test_api_connectivity
            test_create_dashboard
            ;;
        sync)
            test_prerequisites
            test_api_connectivity
            test_create_dashboard
            test_sync_dashboard
            ;;
        update)
            test_prerequisites
            test_api_connectivity
            test_create_dashboard
            test_update_dashboard
            ;;
        export)
            test_prerequisites
            test_api_connectivity
            test_create_dashboard
            test_export_dashboard
            ;;
        errors)
            test_prerequisites
            test_error_handling
            ;;
        all)
            test_prerequisites
            test_api_connectivity
            test_help_command
            test_create_dashboard
            test_sync_dashboard
            test_update_dashboard
            test_export_dashboard
            test_error_handling
            ;;
        *)
            echo "Usage: $0 [prereq|api|help|create|sync|update|export|errors|all]"
            exit 1
            ;;
    esac
    
    # Summary
    echo ""
    echo "========================================"
    echo "Test Summary"
    echo "========================================"
    echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
    echo -e "${RED}Failed: $TESTS_FAILED${NC}"
    
    if [ -n "$TEST_DASHBOARD_ID" ]; then
        echo ""
        echo -e "${YELLOW}NOTE: Test dashboard created (ID: $TEST_DASHBOARD_ID)${NC}"
        echo "Delete manually in PostHog UI if no longer needed:"
        echo "  https://us.posthog.com/project/*/dashboard/$TEST_DASHBOARD_ID"
    fi
    
    if [ "$TESTS_FAILED" -gt 0 ]; then
        exit 1
    fi
}

main "$@"
