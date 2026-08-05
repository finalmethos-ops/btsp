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
