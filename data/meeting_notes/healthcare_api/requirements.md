# Healthcare Patient Portal API Requirements

**Date:** 2026-01-16
**Project:** Healthcare API (HIPAA Compliant)

## API Endpoints

### Patient Management
- `POST /patients` - Create new patient record (admin only)
- `GET /patients/{id}` - Retrieve patient details
- `PUT /patients/{id}` - Update patient information
- `DELETE /patients/{id}` - Soft delete (archive) patient

### Appointment Scheduling
- `GET /patients/{id}/appointments` - List patient appointments
- `POST /appointments` - Schedule new appointment
- `PUT /appointments/{id}` - Reschedule appointment
- `DELETE /appointments/{id}` - Cancel appointment

### Medical Records
- `GET /patients/{id}/records` - Retrieve medical records
- `POST /patients/{id}/records` - Add new medical record entry
- `GET /patients/{id}/records/{record_id}` - Get specific record

## Security & HIPAA Compliance

### Authentication
- OAuth 2.0 with JWT tokens
- Multi-factor authentication required
- Session timeout after 15 minutes of inactivity

### Authorization
- Role-Based Access Control (RBAC)
- Patient role: Own data only
- Doctor role: Assigned patients
- Admin role: Full access with audit logging

### Data Protection
- All PII encrypted at rest (AES-256)
- All data in transit via TLS 1.2+
- Database field-level encryption for sensitive data
- Data masking in non-production environments

### Audit & Logging
- Comprehensive access logging
- Immutable audit trail
- Log retention: 7 years minimum
- Tamper-evident logging

### Consent Management
- Explicit patient consent for data sharing
- Consent versioning and tracking
- Consent withdrawal workflow

## Database Schema

### Patients
- id (UUID, PK)
- mrn (Medical Record Number, unique)
- first_name (encrypted)
- last_name (encrypted)
- date_of_birth (encrypted)
- ssn (encrypted)
- contact_phone (encrypted)
- contact_email (encrypted)
- created_at
- updated_at
- deleted_at (soft delete)

### Appointments
- id (UUID, PK)
- patient_id (FK)
- provider_id (FK)
- scheduled_at
- duration_minutes
- status (scheduled/completed/cancelled)
- notes (encrypted)

### MedicalRecords
- id (UUID, PK)
- patient_id (FK)
- provider_id (FK)
- record_type (lab/prescription/visit_note)
- content (encrypted JSON)
- created_at

### AuditLog
- id (UUID, PK)
- user_id
- action
- resource_type
- resource_id
- ip_address
- user_agent
- timestamp
- details (JSON)

## Technology Stack
- **Backend:** Java Spring Boot
- **Database:** MySQL with encryption
- **Cloud:** AWS (EC2, RDS, KMS, CloudWatch)
- **API Gateway:** AWS API Gateway
- **Secrets:** AWS Secrets Manager

## Non-Functional Requirements
- 99.99% uptime SLA
- Handle 1000+ requests/second
- RPO: 1 hour, RTO: 4 hours
- Data retention: 7 years minimum
