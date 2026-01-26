# public/scripts/seed_large_dataset.py
from app.db import DbManager
from .seed_db import seed_db
from typing import Any
from .data_template import DEFAULT_DATA_TEMPLATE


async def seed_large_dataset(
    db_manager: DbManager,
    data_template: dict[str, dict[str, Any]] = DEFAULT_DATA_TEMPLATE,  # Add parameter
    batch_size: int = 100_000,
    total_records: int = 10_000_000,
):
    """Seed 10M records in batches to avoid memory issues."""

    for start_idx in range(0, total_records, batch_size):
        print(f"Processing batch {start_idx // batch_size + 1}...")

        # Generate and export batch to CSV
        await seed_db(
            db_manager=db_manager,
            data_template=data_template,  # Now properly typed
            records=min(batch_size, total_records - start_idx),
            start_index=start_idx,
            export_csv=True,
            csv_dir=f"data/seed/batch_{start_idx // batch_size}",
        )


__all__ = ["seed_large_dataset"]
