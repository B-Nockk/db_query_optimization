# Healthcare Domain Glossary

## 1. Core Entities

| Term            | Technical Name | Definition                                                                                       |
| :-------------- | :------------- | :----------------------------------------------------------------------------------------------- |
| **Patient**     | `Patient`      | An individual receiving medical care. Records contain PII (Personally Identifiable Information). |
| **Doctor**      | `Doctor`       | A medical professional providing services. Linked to a specific specialty.                       |
| **Schedule**    | `Schedule`     | A "blueprint" of recurring availability (e.g., Every Monday 9-5).                                |
| **Appointment** | `Appointment`  | A specific "instance" of care where a Patient and Doctor are matched at a specific time.         |

## 2. Identifiers & Security

- **UUID (Internal ID)**: The primary key (PK) used for database relationships. Never exposed to users via phone/paper.
- **Short Code (External ID)**: A 10-12 character string (e.g., `PAT-123456`) used by staff and patients for lookup.
- **PHI**: Protected Health Information. Any data in the `medical_history` or `notes` fields.
- **PII**: Personally Identifiable Information (Name, Contact Info, DOB).

## 3. Appointment Lifecycle States

- `SCHEDULED`: Initial state. Slot is reserved.
- `CHECKED_IN`: Patient has arrived and is in the waiting area.
- `IN_PROGRESS`: The "Encounter" is active. Doctor is with the patient.
- `COMPLETED`: The session is over. Notes are finalized.
- `CANCELLED`: Appointment was aborted before it began.
- `NO_SHOW`: Time slot passed without patient arrival.
