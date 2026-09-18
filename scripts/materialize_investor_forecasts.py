#!/usr/bin/env python3
"""Build or resume the versioned investor opportunity forecast catalog."""

import argparse
import json
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
MARKET = REPO / "market-simulator"
sys.path.insert(0, str(MARKET))
sys.path.insert(0, str(REPO / "scripts"))

from forecast_catalog import ForecastCatalog  # noqa: E402
from live_model_worker import Worker  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--refresh", action="store_true",
                        help="recompute eligible rows even if they already exist")
    args = parser.parse_args()
    if not 1 <= args.batch_size <= 256:
        parser.error("--batch-size must be between 1 and 256")
    universe = json.loads((MARKET / "runtime/universe-v3.json").read_text())
    cutoff = universe["start"]
    catalog = ForecastCatalog(
        MARKET / "runtime" / f"investor-forecast-catalog-{cutoff}.json", cutoff)
    worker = Worker()
    worker.extend_histories(cutoff)
    eligible = set(worker.histories.groups)
    pending = [item["id"] for item in universe["companies"]
               if item["id"] in eligible and
               (args.refresh or item["id"] not in catalog.rows)]
    # Similar lengths in one batch avoid padding a short-history enterprise to
    # the longest enterprise in the entire website cohort.
    pending.sort(key=lambda company: (len(worker.histories.groups[company]), company))
    if args.limit is not None:
        pending = pending[:max(0, args.limit)]
    completed = 0
    for offset in range(0, len(pending), args.batch_size):
        companies = pending[offset:offset + args.batch_size]
        results = worker.run_many(companies, cutoff)
        final = offset + args.batch_size >= len(pending)
        catalog.record_many(results, persist=final or (offset // args.batch_size) % 10 == 9)
        completed += len(companies)
        print(f"{completed}/{len(pending)} requested · {len(catalog.rows)} available", flush=True)
    if pending:
        catalog.save()
    print(json.dumps({"requested": completed, "available": len(catalog.rows),
                      "path": str(catalog.path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
