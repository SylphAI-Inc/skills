# Stripe CLI

## Setup & Auth

```bash
# Install
brew install stripe/stripe-cli/stripe   # macOS
# Or download from https://github.com/stripe/stripe-cli/releases

# Login (opens browser for OAuth)
stripe login

# Use API key directly (non-interactive, CI/CD)
stripe config --api-key sk_test_xxx

# Check current config
stripe config --list

# Switch between accounts
stripe config --project-name myproject
```

### API Key Types

| Key prefix | Environment | Use |
|------------|-------------|-----|
| `sk_test_` | Test mode | Development, CI/CD |
| `sk_live_` | Live mode | Production (never in code) |
| `pk_test_` | Test publishable | Frontend test |
| `pk_live_` | Live publishable | Frontend production |
| `rk_test_` | Restricted test | Limited permissions |

> **⚠️ Never use `sk_live_` in CLI scripts or CI/CD.** Use restricted keys (`rk_`) with only the permissions you need.

## Webhook Testing

```bash
# Forward webhooks to local server
stripe listen --forward-to localhost:3000/webhook

# Forward specific events only
stripe listen --forward-to localhost:3000/webhook \
  --events checkout.session.completed,payment_intent.succeeded

# Get the webhook signing secret (printed on start)
# Use this as STRIPE_WEBHOOK_SECRET in your app

# Forward to multiple endpoints
stripe listen --forward-to localhost:3000/webhook \
  --forward-connect-to localhost:3000/connect-webhook

# Listen with latest API version
stripe listen --forward-to localhost:3000/webhook --latest
```

### Trigger Test Events

```bash
# Trigger a specific event
stripe trigger payment_intent.succeeded

# Trigger checkout flow (creates multiple events)
stripe trigger checkout.session.completed

# Trigger with custom data via fixtures
stripe trigger customer.subscription.created \
  --override customer:name="Test User"

# List available trigger events
stripe trigger --list
```

## API Requests

```bash
# Create a customer
stripe customers create --name "Jane Doe" --email jane@example.com

# Retrieve a resource
stripe customers retrieve cus_xxx

# List with filters
stripe customers list --limit 10 --created gt:2024-01-01

# Update a resource
stripe customers update cus_xxx --name "Jane Smith"

# Delete a resource
stripe customers delete cus_xxx

# Create a payment intent
stripe payment_intents create --amount 2000 --currency usd

# Confirm a payment intent
stripe payment_intents confirm pi_xxx --payment-method pm_card_visa

# Create a subscription
stripe subscriptions create --customer cus_xxx --price price_xxx
```

### Output Formatting

```bash
# JSON output (default)
stripe customers list --limit 5

# Get specific field with jq
stripe customers retrieve cus_xxx | jq '.email'

# List IDs only
stripe customers list --limit 100 | jq -r '.data[].id'

# Auto-paginate all results
stripe customers list --limit 100 --auto-paginate | jq '.data | length'
```

## Fixtures & Test Data

```bash
# Create a full payment flow fixture
stripe fixtures /path/to/fixture.json

# Example fixture file (fixture.json):
# {
#   "_meta": { "template_version": 0 },
#   "fixtures": [
#     {
#       "name": "customer",
#       "path": "/v1/customers",
#       "method": "post",
#       "params": { "name": "Test", "email": "test@example.com" }
#     },
#     {
#       "name": "payment_intent",
#       "path": "/v1/payment_intents",
#       "method": "post",
#       "params": {
#         "amount": 2000,
#         "currency": "usd",
#         "customer": "${customer:id}"
#       }
#     }
#   ]
# }

# Use fixtures for seeding test data
stripe fixtures seed.json
```

## Logs & Debugging

```bash
# Tail API request logs in real-time
stripe logs tail

# Filter by status
stripe logs tail --filter-status-code 400

# Filter by HTTP method
stripe logs tail --filter-http-method POST

# Filter by API path
stripe logs tail --filter-request-path /v1/charges

# Combine filters
stripe logs tail --filter-status-code 500 --filter-http-method POST
```

## Resources & Samples

```bash
# Open Stripe Dashboard
stripe open dashboard

# Open specific dashboard page
stripe open dashboard/payments
stripe open dashboard/webhooks

# Open API docs
stripe open api

# List available samples
stripe samples list

# Create a sample project
stripe samples create accept-a-payment
```

## Common Patterns

### CI/CD Webhook Testing

```bash
# In CI: use --api-key instead of login
export STRIPE_API_KEY=sk_test_xxx
stripe listen --forward-to localhost:3000/webhook --api-key $STRIPE_API_KEY &
STRIPE_PID=$!

# Run tests
npm test

# Cleanup
kill $STRIPE_PID
```

### Idempotent Requests

```bash
# Use idempotency key to prevent duplicate charges
stripe payment_intents create \
  --amount 2000 \
  --currency usd \
  --idempotency-key "order_12345"
```

### Test Card Numbers

| Card | Number | Use |
|------|--------|-----|
| Visa (success) | `4242424242424242` | Successful payment |
| Visa (decline) | `4000000000000002` | Card declined |
| 3D Secure | `4000002760003184` | Requires authentication |
| Insufficient funds | `4000000000009995` | Decline — insufficient funds |
| Expired | `4000000000000069` | Expired card |

> Use `pm_card_visa` as a shorthand payment method in CLI commands.

## Gotchas

1. **`stripe listen` must be running** — Webhooks won't reach localhost without it. Start it *before* triggering events.
2. **Webhook signing secret changes** — Every time you restart `stripe listen`, you get a new `whsec_` secret. Update your env var.
3. **Test vs Live mode** — CLI defaults to test mode. Never pass `--live` unless you intend to affect real data.
4. **`--auto-paginate` can be slow** — For large datasets, it fetches everything. Use `--limit` and manual pagination in scripts.
5. **API version matters** — Your account has a default API version. Use `--stripe-version` to pin a specific version in automation.
6. **`stripe trigger` creates real test objects** — It actually creates customers, payments, etc. in your test account. Clean up after testing.
7. **Rate limits apply** — Test mode has generous but real rate limits (100 reads/sec, 100 writes/sec). Bulk operations can hit them.
