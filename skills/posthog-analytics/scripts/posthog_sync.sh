#!/bin/bash
# PostHog Dashboard Sync Script
# Usage: ./posthog_sync.sh <command> <config_file> [dashboard_id]

set -e

API_KEY="${POSTHOG_PERSONAL_API_KEY}"
BASE_URL="${POSTHOG_HOST:-https://us.i.posthog.com}/api/projects/@current"

if [ -z "$API_KEY" ]; then
    echo "Error: POSTHOG_PERSONAL_API_KEY not set"
    exit 1
fi

# Build insight query from type
build_query() {
    local type=$1
    local domain=$2
    local display=${3:-BoldNumber}
    local math=${4:-total}
    local event=${5:-\$pageview}
    local date_range=${6:--30d}
    local breakdown=$7
    
    local properties='{
        "type": "AND",
        "values": [{
            "type": "AND", 
            "values": [{
                "key": "$current_url",
                "value": "'"$domain"'",
                "operator": "icontains",
                "type": "event"
            }]
        }]
    }'
    
    local breakdown_filter=""
    if [ -n "$breakdown" ]; then
        breakdown_filter=',"breakdownFilter": {"breakdown": "'"$breakdown"'", "breakdown_type": "event"}'
    fi
    
    local interval=""
    if [ "$display" = "ActionsLineGraph" ]; then
        interval=',"interval": "day"'
    fi
    
    echo '{
        "kind": "InsightVizNode",
        "source": {
            "kind": "TrendsQuery",
            "series": [{"kind": "EventsNode", "math": "'"$math"'", "event": "'"$event"'"}],
            "properties": '"$properties"',
            "dateRange": {"date_from": "'"$date_range"'"},
            "trendsFilter": {"display": "'"$display"'"}'"$breakdown_filter$interval"'
        }
    }'
}

create_dashboard() {
    local config_file=$1
    local name=$(jq -r '.name' "$config_file")
    local description=$(jq -r '.description // ""' "$config_file")
    local domain=$(jq -r '.domain_filter // ""' "$config_file")
    
    echo "Creating dashboard: $name"
    
    # Create dashboard
    local dashboard=$(curl -s -X POST "$BASE_URL/dashboards/" \
        -H "Authorization: Bearer $API_KEY" \
        -H "Content-Type: application/json" \
        -d '{"name": "'"$name"'", "description": "'"$description"'"}')
    
    local dashboard_id=$(echo "$dashboard" | jq -r '.id')
    echo "Dashboard created: ID $dashboard_id"
    
    # Create insights
    local insights=$(jq -c '.insights[]' "$config_file")
    while IFS= read -r insight; do
        local insight_name=$(echo "$insight" | jq -r '.name')
        local insight_type=$(echo "$insight" | jq -r '.type')
        local display=$(echo "$insight" | jq -r '.display // "BoldNumber"')
        local math=$(echo "$insight" | jq -r '.math // "total"')
        local event=$(echo "$insight" | jq -r '.event // "$pageview"')
        local date_range=$(echo "$insight" | jq -r '.date_range // "-30d"')
        local breakdown=$(echo "$insight" | jq -r '.breakdown // ""')
        
        # Map type to display/math defaults
        case $insight_type in
            pageviews_total) display="BoldNumber"; math="total" ;;
            unique_users) display="BoldNumber"; math="dau" ;;
            traffic_trend) display="ActionsLineGraph"; math="total" ;;
            top_pages) display="ActionsTable"; breakdown="\$current_url" ;;
        esac
        
        local query=$(build_query "$insight_type" "$domain" "$display" "$math" "$event" "$date_range" "$breakdown")
        
        echo "Creating insight: $insight_name"
        curl -s -X POST "$BASE_URL/insights/" \
            -H "Authorization: Bearer $API_KEY" \
            -H "Content-Type: application/json" \
            -d '{
                "name": "'"$insight_name"'",
                "dashboards": ['"$dashboard_id"'],
                "query": '"$query"'
            }' | jq '{id, name}'
    done <<< "$insights"
    
    # Update config with dashboard_id
    jq '.dashboard_id = '"$dashboard_id" "$config_file" > "${config_file}.tmp" && mv "${config_file}.tmp" "$config_file"
    
    echo ""
    echo "Dashboard URL: https://us.i.posthog.com/dashboard/$dashboard_id"
}

export_dashboard() {
    local dashboard_id=$1
    
    # Get dashboard with tiles
    local dashboard=$(curl -s -H "Authorization: Bearer $API_KEY" "$BASE_URL/dashboards/$dashboard_id/")
    local name=$(echo "$dashboard" | jq -r '.name')
    local description=$(echo "$dashboard" | jq -r '.description // ""')
    
    # Extract insights from tiles (tiles contain insight objects)
    local insights=$(echo "$dashboard" | jq -c '[.tiles[]? | select(.insight != null) | {name: .insight.name, insight_id: .insight.id, type: "custom"}]')
    
    # Build output JSON
    echo "$dashboard" | jq '{
        name: .name,
        description: (.description // ""),
        dashboard_id: .id,
        domain_filter: "",
        insights: [.tiles[]? | select(.insight != null) | {
            name: .insight.name,
            insight_id: .insight.id,
            type: "custom"
        }]
    }'
}

sync_dashboard() {
    local config_file=$1
    local dashboard_id=$(jq -r '.dashboard_id' "$config_file")
    local domain=$(jq -r '.domain_filter // ""' "$config_file")
    
    if [ "$dashboard_id" = "null" ] || [ -z "$dashboard_id" ]; then
        echo "Error: No dashboard_id in config. Run 'create' first or add dashboard_id manually."
        exit 1
    fi
    
    echo "Syncing to dashboard: $dashboard_id"
    
    # Get existing insights on dashboard
    local existing=$(curl -s -H "Authorization: Bearer $API_KEY" "$BASE_URL/dashboards/$dashboard_id/" | \
        jq -r '[.tiles[]? | select(.insight != null) | .insight.name] | @json')
    
    echo "Existing insights: $existing"
    
    # Process each insight in config
    local insights=$(jq -c '.insights[]' "$config_file")
    while IFS= read -r insight; do
        local insight_name=$(echo "$insight" | jq -r '.name')
        local insight_id=$(echo "$insight" | jq -r '.insight_id // empty')
        local insight_type=$(echo "$insight" | jq -r '.type')
        local display=$(echo "$insight" | jq -r '.display // "BoldNumber"')
        local math=$(echo "$insight" | jq -r '.math // "total"')
        local event=$(echo "$insight" | jq -r '.event // "$pageview"')
        local date_range=$(echo "$insight" | jq -r '.date_range // "-30d"')
        local breakdown=$(echo "$insight" | jq -r '.breakdown // ""')
        
        # Map type to display/math defaults
        case $insight_type in
            pageviews_total) display="BoldNumber"; math="total" ;;
            unique_users) display="BoldNumber"; math="dau" ;;
            traffic_trend) display="ActionsLineGraph"; math="total" ;;
            top_pages) display="ActionsTable"; breakdown="\$current_url" ;;
        esac
        
        local query=$(build_query "$insight_type" "$domain" "$display" "$math" "$event" "$date_range" "$breakdown")
        
        # Check if insight exists (by name in existing list)
        if echo "$existing" | jq -e 'index("'"$insight_name"'")' > /dev/null 2>&1; then
            echo "Insight exists, skipping: $insight_name"
        else
            echo "Creating new insight: $insight_name"
            local result=$(curl -s -X POST "$BASE_URL/insights/" \
                -H "Authorization: Bearer $API_KEY" \
                -H "Content-Type: application/json" \
                -d '{
                    "name": "'"$insight_name"'",
                    "dashboards": ['"$dashboard_id"'],
                    "query": '"$query"'
                }')
            echo "$result" | jq '{id, name}'
        fi
    done <<< "$insights"
    
    echo ""
    echo "Sync complete: https://us.i.posthog.com/dashboard/$dashboard_id"
}

# Main
case "${1:-help}" in
    create)
        [ -z "$2" ] && echo "Usage: $0 create <config.json>" && exit 1
        create_dashboard "$2"
        ;;
    sync)
        [ -z "$2" ] && echo "Usage: $0 sync <config.json>" && exit 1
        sync_dashboard "$2"
        ;;
    export)
        [ -z "$2" ] && echo "Usage: $0 export <dashboard_id>" && exit 1
        export_dashboard "$2"
        ;;
    help|*)
        echo "PostHog Dashboard Sync"
        echo ""
        echo "Usage:"
        echo "  $0 create <config.json>     Create new dashboard from config"
        echo "  $0 sync <config.json>       Sync config to existing dashboard (adds new insights)"
        echo "  $0 export <dashboard_id>    Export dashboard to config"
        echo ""
        echo "Environment:"
        echo "  POSTHOG_PERSONAL_API_KEY    Required - API key (phx_...)"
        echo "  POSTHOG_HOST                Optional - API host (default: us.i.posthog.com)"
        ;;
esac
