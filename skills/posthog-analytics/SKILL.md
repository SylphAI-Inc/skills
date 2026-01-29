# PostHog Analytics Skill

Automate PostHog dashboard creation, sync, and export via API.

## When to Use

- Setting up analytics dashboards for new projects
- Syncing dashboard configs between environments (add new insights without duplicates)
- Exporting existing dashboards to version-controlled configs
- Querying PostHog events programmatically

## Prerequisites

```bash
# Required environment variable
export POSTHOG_PERSONAL_API_KEY=phx_xxx  # Get from PostHog Settings → Personal API Keys
```

## Workflow

### 1. Create New Dashboard
```bash
./scripts/posthog_sync.sh create examples/blog_dashboard.json
```
Creates dashboard + all insights. Updates config with `dashboard_id`.

### 2. Sync Changes (Add New Insights)
```bash
# Edit config to add new insights, then:
./scripts/posthog_sync.sh sync examples/app_dashboard.json
```
Only creates NEW insights. Existing ones are detected by name and skipped.

### 3. Export Existing Dashboard
```bash
./scripts/posthog_sync.sh export 1126158 > my_dashboard.json
```
Exports dashboard with all insight names and IDs.

## Config Schema

```json
{
  "name": "Dashboard Name",
  "description": "Description",
  "domain_filter": "app.sylph.ai",
  "dashboard_id": null,
  "insights": [
    {
      "name": "Pageviews (Total)",
      "type": "pageviews_total",
      "display": "BoldNumber",
      "date_range": "-30d"
    }
  ]
}
```

### Insight Types

| Type | Display | Math | Description |
|------|---------|------|-------------|
| `pageviews_total` | BoldNumber | total | Total pageview count |
| `unique_users` | BoldNumber | dau | Daily unique users |
| `traffic_trend` | ActionsLineGraph | total | Line chart over time |
| `top_pages` | ActionsTable | total | Table with URL breakdown |
| `custom` | Any | Any | Full control via params |

### Math Options

| Math | Description |
|------|-------------|
| `total` | Total count |
| `dau` | Daily active users |
| `weekly_active` | Weekly active users |
| `monthly_active` | Monthly active users |

### Display Options

| Display | Description |
|---------|-------------|
| `BoldNumber` | Single large number |
| `ActionsLineGraph` | Line chart |
| `ActionsTable` | Table with breakdown |
| `ActionsBar` | Vertical bar chart |

## API Quick Reference

```bash
# List dashboards
curl -H "Authorization: Bearer $KEY" "https://us.i.posthog.com/api/projects/@current/dashboards/"

# Query events
curl -H "Authorization: Bearer $KEY" "https://us.i.posthog.com/api/projects/@current/events?limit=100" | \
  jq '.results[:5] | .[] | "\(.event) | \(.properties["$current_url"])"'

# Filter events by domain
curl -s -H "Authorization: Bearer $KEY" ".../events?limit=100" | \
  jq '[.results[] | select(.properties["$current_url"] | contains("yourdomain"))] | length'
```

## Example Configs

### Blog Analytics
```json
{
  "name": "Blog Analytics",
  "domain_filter": "blog.sylph.ai",
  "insights": [
    {"name": "Pageviews", "type": "pageviews_total"},
    {"name": "Unique Readers", "type": "unique_users"},
    {"name": "Traffic Trend", "type": "traffic_trend"},
    {"name": "Top Posts", "type": "top_pages"}
  ]
}
```

### App Product Metrics
```json
{
  "name": "App Product Metrics",
  "domain_filter": "app.sylph.ai",
  "insights": [
    {"name": "DAU", "type": "unique_users"},
    {"name": "WAU", "type": "unique_users", "math": "weekly_active"},
    {"name": "Pageviews", "type": "pageviews_total"},
    {"name": "Usage Trend", "type": "traffic_trend"},
    {"name": "Top Pages", "type": "top_pages"}
  ]
}
```

## Files

- `SKILL.md` - This guide
- `dashboard_schema.json` - JSON schema for validation
- `scripts/posthog_sync.sh` - Create/sync/export script
- `examples/blog_dashboard.json` - Blog dashboard config
- `examples/app_dashboard.json` - App dashboard config

## References

- [PostHog API Docs](https://posthog.com/docs/api) - Full API reference
- [Insights API](https://posthog.com/docs/api/insights) - Creating/querying insights
- [Dashboards API](https://posthog.com/docs/api/dashboards) - Dashboard management
- [Events API](https://posthog.com/docs/api/events) - Event querying
- [HogQL](https://posthog.com/docs/hogql) - PostHog query language for advanced queries
