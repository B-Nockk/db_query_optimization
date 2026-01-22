# public/scripts/run_db_seed.py
from app.db import DbManager
from common.config import get_config
from dotenv import load_dotenv
from .seed_db import seed_db
from datetime import date


async def main():
    load_dotenv()
    config = get_config()

    _db_config = config.database
    if not _db_config:
        raise RuntimeError("Database configuration required")

    # Initialize DB manager
    db_manager = DbManager.from_config(_db_config)
    await db_manager.verify_connection()

    data_template = {
        "doctors": {
            "name": "Dr. Smith",
            "specialty": "Cardiology",
            "contact_info": "555-0100",
        },
        "patients": {
            "name": "Patient",
            "date_of_birth": date(1990, 1, 1),
            "contact_info": "555-0200",
            "medical_history": "None",
        },
    }
    # Seed 100 records, export to CSV
    results = await seed_db(
        db_manager=db_manager,
        data_template=data_template,
        records=100,
        start_index=0,
        export_csv=True,
        csv_dir="data/seed",
    )

    print(f"Seeded {sum(len(v) for v in results.values())} total records")

    # For 10M records, generate CSV first, then use insert_from_csv
    # This avoids memory issues

    await db_manager.dispose()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
