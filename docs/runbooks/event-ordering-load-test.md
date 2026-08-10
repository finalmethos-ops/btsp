# Live Ordering Load Test

Use `scripts/load-test-live-ordering.sh` to exercise the live-presentation
ordering endpoint against an isolated test event. The script is dry-run by
default and refuses the production hostname unless two explicit safeguards are
provided.

The endpoint is a `PUT` for the current slide and entity, so repeated requests
from one token update the same order rather than creating independent business
orders. Use separate test users/tokens if you need to model multiple entities.

Example dry run:

```bash
SUB_EVENT_ID=<test-sub-event-id> \
AUTH_TOKEN=<test-access-token> \
scripts/load-test-live-ordering.sh
```

Example isolated run:

```bash
BASE_URL=http://localhost:18080/api/v1 \
SUB_EVENT_ID=<test-sub-event-id> \
AUTH_TOKEN=<test-access-token> \
REQUESTS=1000 \
CONCURRENCY=32 \
DRY_RUN=0 \
scripts/load-test-live-ordering.sh
```

Do not point this at production. If a controlled production test is ever
approved, it requires both `ALLOW_PRODUCTION_ORDER_LOAD=YES` and
`PRODUCTION_ORDER_LOAD_CONFIRM=I_UNDERSTAND_THIS_WRITES_TEST_ORDERS` and must
be coordinated with an explicit cleanup plan.

For a fully reconciled test with distinct authenticated users, use the guarded
PostgreSQL harness. It drops and recreates its target schema and therefore
refuses every database whose name does not contain `stress`:

```bash
DATABASE_URL=postgresql+psycopg://btsp:btsp@localhost:5433/btsp_stress \
python scripts/stress-test-live-ordering.py \
  --users 200 \
  --concurrency 40 \
  --display-readers 8 \
  --max-order-p95-ms 10000 \
  --max-display-p95-ms 3000 \
  --min-orders-per-second 2
```

The harness creates a three-product combined slide with different prices,
minimum quantities, and exact per-product capacity limits. Every simulated
entity submits its own product-specific quantity mix. It fails unless each
saved order and revision, weighted order value, per-model projector total, and
combined total reconcile exactly. It also attempts one order beyond a filled
product limit and verifies that the order is rejected without changing the
previously committed order. Optional latency and throughput thresholds make
major performance regressions fail CI without relaxing order correctness.
