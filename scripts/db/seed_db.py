# public/app/scripts/seed_db.py
import csv
from pathlib import Path
from pydantic import BaseModel
from datetime import date

from app.db import DbManager
from app.db.models import Doctor, Patient
from app.db.schemas import DoctorCreate, PatientCreate


SCHEMA_MAP = {
    "doctors": DoctorCreate,
    "patients": PatientCreate,
}

MODEL_MAP = {
    "doctors": Doctor,
    "patients": Patient,
}


def write_records_to_csv(filename: str, records: list[BaseModel]):
    """Write Pydantic schema records to CSV."""
    if not records:
        return

    path = Path(filename)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Convert first record to get fieldnames
    first_dict = records[0].model_dump(mode="python")
    fieldnames = list(first_dict.keys())

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            # Convert dates and other types to strings for CSV
            row_dict = record.model_dump(mode="python")
            # Handle date serialization
            for key, value in row_dict.items():
                if isinstance(value, date):
                    row_dict[key] = value.isoformat()
            writer.writerow(row_dict)


async def insert_from_csv(db_manager: DbManager, table: str, filename: str):
    """Read CSV and insert into database using ORM models."""
    if not hasattr(db_manager, "session_maker") or db_manager.session_maker is None:
        raise RuntimeError(
            "DbManager not properly initialized. "
            "Ensure verify_connection() was called during startup."
        )

    model_cls = MODEL_MAP[table]
    schema_cls = SCHEMA_MAP[table]

    objs = []
    with open(filename, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Convert CSV row to Pydantic schema for validation
            # Handle date conversion if needed
            if "date_of_birth" in row and isinstance(row["date_of_birth"], str):
                row["date_of_birth"] = date.fromisoformat(row["date_of_birth"])

            schema_obj = schema_cls(**row)
            # Convert Pydantic schema to ORM model
            orm_obj = model_cls(**schema_obj.model_dump())  # type: ignore[attr-defined]
            objs.append(orm_obj)

    async with db_manager.session() as session:
        session.add_all(objs)
        # Commit happens automatically on context exit


async def seed_db(
    db_manager: DbManager,
    data_template: dict[str, dict],
    records: int,
    start_index: int = 0,
    export_csv: bool = False,
    csv_dir: str = "data/seed",
):
    """
    Seed database with generated records.

    Args:
        db_manager: Initialized DbManager instance
        data_template: Dict mapping table names to template dicts
        records: Number of records to generate per table
        start_index: Starting index for record generation
        export_csv: Whether to export generated records to CSV
        csv_dir: Directory to save CSV files

    Returns:
        Dict mapping table names to lists of generated Pydantic schemas
    """
    if not hasattr(db_manager, "session_maker") or db_manager.session_maker is None:
        raise RuntimeError(
            "DbManager not properly initialized. "
            "Ensure verify_connection() was called during startup."
        )

    all_records_by_table = {}

    for table, template in data_template.items():
        schema_cls = SCHEMA_MAP[table]
        model_cls = MODEL_MAP[table]

        # Generate Pydantic schema records
        schema_records = schema_cls.seed_records(template, records, start_index)  # type: ignore[attr-defined]
        all_records_by_table[table] = schema_records

        # Optionally export to CSV
        if export_csv:
            csv_path = Path(csv_dir) / f"{table}.csv"
            write_records_to_csv(str(csv_path), schema_records)

        # Convert to ORM models for DB insertion
        orm_objects = [model_cls(**record.model_dump()) for record in schema_records]

        # Insert into database
        async with db_manager.session() as session:
            session.add_all(orm_objects)
            # Commit happens automatically on context exit

    return all_records_by_table
