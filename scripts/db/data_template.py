"""
Easily extendible template file for data templates
- Add new templates
- Compose them into DEFAULT_DATA_TEMPLATE

    Example: Seed only patients
        await seed_db({"patients": PATIENT_DATA_TEMPLATE}, records=100)

    Example: Seed both doctors and patients
        await seed_db(DEFAULT_DATA_TEMPLATE, records=1000)
"""

from datetime import date
from typing import Any

# Individual templates
PATIENT_DATA_TEMPLATE: dict[str, Any] = {
    "name": "Patient",
    "date_of_birth": date(1990, 1, 1),
    "contact_info": "555-0200",
    "medical_history": "None",
}

DOCTOR_DATA_TEMPLATE: dict[str, Any] = {
    "name": "Dr. Smith",
    "specialty": "Cardiology",
    "contact_info": "555-0100",
}

# Combined default template
DEFAULT_DATA_TEMPLATE: dict[str, dict[str, Any]] = {
    "doctors": DOCTOR_DATA_TEMPLATE,
    "patients": PATIENT_DATA_TEMPLATE,
}

__all__ = [
    "DEFAULT_DATA_TEMPLATE",
    "DOCTOR_DATA_TEMPLATE",
    "PATIENT_DATA_TEMPLATE",
]
