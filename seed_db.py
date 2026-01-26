# public/seed_db.py
"""
Database Seeding Script
=======================

This script provides command-line utilities to seed a database with either
a small dataset (for testing/development) or a large dataset (for performance
and scalability testing).

It supports two modes:
- `small`: Insert a specified number of records, with optional CSV export.
- `large`: Insert a very large dataset in batches.

Usage:
    python seed.py small --records 500 --export-csv --csv-dir data/output
    python seed.py large --batch-size 100000 --total-records 5000000

Requirements:
    - A valid database configuration (via environment variables or config files).
    - Properly initialized `DbManager` and seeding functions.

"""

import sys
import argparse
import asyncio
from scripts.db import seed_db, seed_large_dataset, DEFAULT_DATA_TEMPLATE
from app.db import DbManager
from common.config import get_config, initialize_config
from common.api_error import ConfigurationError
from dotenv import load_dotenv


def get_db_config():
    """
    Load and validate database configuration.

    Returns:
        tuple: (config, db_config)

    Raises:
        SystemExit: If configuration cannot be loaded.

    Example:
        >>> config, db_cfg = get_db_config()
    """

    def _try_get():
        cfg = get_config()
        return cfg, getattr(cfg, "database", None)

    config, db_cfg = _try_get()
    if config and db_cfg:
        return config, db_cfg

    try:
        initialize_config()
        config, db_cfg = _try_get()
        if config and db_cfg:
            return config, db_cfg
        raise RuntimeError("Database configuration required after initialization")
    except ConfigurationError as e:
        print(f"FATAL: Configuration error:\n{e}")
        sys.exit()


async def run_seed_db(
    _db_config,
    records: int,
    export_csv: bool,
    csv_dir: str,
):
    """
    Run small dataset seeding.

    Args:
        _db_config (dict): Database configuration.
        records (int): Number of records to insert.
        export_csv (bool): Whether to export to CSV.
        csv_dir (str): Directory for CSV export.

    Example:
        >>> asyncio.run(run_seed_db(db_cfg, records=200, export_csv=True, csv_dir="data/test"))
    """
    db_manager = DbManager.from_config(_db_config)
    await db_manager.verify_connection()
    await seed_db(
        db_manager=db_manager,
        data_template=DEFAULT_DATA_TEMPLATE,
        records=records,
        export_csv=export_csv,
        csv_dir=csv_dir,
    )
    await db_manager.dispose()


async def run_seed_large(
    _db_config,
    batch_size: int,
    total_records: int,
):
    """
    Run large dataset seeding.

    Args:
        _db_config (dict): Database configuration.
        batch_size (int): Number of records per batch.
        total_records (int): Total number of records to insert.

    Example:
        >>> asyncio.run(run_seed_large(db_cfg, batch_size=100000, total_records=10000000))
    """
    db_manager = DbManager.from_config(_db_config)
    await db_manager.verify_connection()
    await seed_large_dataset(
        db_manager=db_manager,
        data_template=DEFAULT_DATA_TEMPLATE,
        batch_size=batch_size,
        total_records=total_records,
    )
    await db_manager.dispose()


def main():
    """
    CLI entry point for database seeding.

    Example:
        Small dataset:
            python seed.py small --records 500 --export-csv --csv-dir data/output

        Large dataset:
            python seed.py large --batch-size 100000 --total-records 5000000
    """
    parser = argparse.ArgumentParser(description="Seed database manager")
    subparsers = parser.add_subparsers(dest="mode", required=True)

    # Small mode parser
    small_parser = subparsers.add_parser("small", help="Seed a small dataset")
    small_parser.add_argument(
        "--records",
        type=int,
        required=True,
        help="Number of records to insert (REQUIRED)",
    )
    small_parser.add_argument(
        "--export-csv", action="store_true", help="Export seeded data to CSV"
    )
    small_parser.add_argument(
        "--csv-dir", type=str, default="data/seed", help="Directory to export CSV files"
    )

    # Large mode parser
    large_parser = subparsers.add_parser("large", help="Seed a large dataset")
    large_parser.add_argument(
        "--batch-size",
        type=int,
        required=True,
        help="Batch size for inserts (REQUIRED)",
    )
    large_parser.add_argument(
        "--total-records",
        type=int,
        required=True,
        help="Total number of records to insert (REQUIRED)",
    )

    args = parser.parse_args()
    config, _db_config = get_db_config()

    if args.mode == "small":
        print("Required: --records")
        print("All args: --records, --export-csv, --csv-dir")
        asyncio.run(
            run_seed_db(_db_config, args.records, args.export_csv, args.csv_dir)
        )
    elif args.mode == "large":
        print("Required: --batch-size, --total-records")
        print("All args: --batch-size, --total-records")
        asyncio.run(run_seed_large(_db_config, args.batch_size, args.total_records))


if __name__ == "__main__":
    try:
        load_dotenv()
        initialize_config()
    except ConfigurationError as e:
        print(f"FATAL: Configuration error:\n{e}")
        sys.exit()
    main()
