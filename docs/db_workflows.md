# System Workflows (Mermaid)

## 1. Patient Registration Workflow

How a guest becomes a patient in the system.

```mermaid
sequenceDiagram
    participant Guest
    participant API
    participant DB

    Guest->>API: Submit Name, DOB, Contact
    API->>DB: Check for duplicate PII
    alt Is Duplicate
        DB-->>API: Conflict Error
        API-->>Guest: Prompt for Login
    else Is New
        API->>API: Generate UUID & Short Code
        API->>DB: Create Patient Record
        DB-->>API: Success
        API-->>Guest: Return patient_code
    end
```

---

## 2. Appointment Booking & Conflict Resolution

### Ensures two patients don't get the same slot for the same doctor.

```mermaid
sequenceDiagram
    participant User
    participant AuthMiddleware
    participant DB

    User->>AuthMiddleware: Request Patient Medical History
    AuthMiddleware->>DB: Get User Roles (M:N)
    DB-->>AuthMiddleware: Roles: [Doctor, Admin]
    AuthMiddleware->>DB: Get Role Permissions (JSON)
    DB-->>AuthMiddleware: Permission: {"can_view_phi": true}

    alt Authorized
        AuthMiddleware-->>User: Return PHI Data
    else Unauthorized
        AuthMiddleware-->>User: 403 Forbidden
    end

```

---

# 3. RBAC Permission Flow

### How the system verifies if a user can see medical history.

```mermaid
sequenceDiagram
    participant User
    participant AuthMiddleware
    participant DB

    User->>AuthMiddleware: Request Patient Medical History
    AuthMiddleware->>DB: Get User Roles (M:N)
    DB-->>AuthMiddleware: Roles: [Doctor, Admin]
    AuthMiddleware->>DB: Get Role Permissions (JSON)
    DB-->>AuthMiddleware: Permission: {"can_view_phi": true}

    alt Authorized
        AuthMiddleware-->>User: Return PHI Data
    else Unauthorized
        AuthMiddleware-->>User: 403 Forbidden
    end

```
