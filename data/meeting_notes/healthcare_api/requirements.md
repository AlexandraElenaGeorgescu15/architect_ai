# Healthcare Patient Portal API

## Project Context
Modernizing a legacy patient portal system for a regional hospital network. The new system must integrate with existing EHR (Electronic Health Records) systems while providing a modern API for web and mobile applications.

## Compliance Requirements
- HIPAA compliant data handling
- HL7 FHIR standard for healthcare data exchange
- Audit logging for all PHI access
- Role-based access control (RBAC)
- Data encryption at rest and in transit

## Core API Endpoints

### Patient Management
- GET/POST /api/patients - Patient demographics
- GET /api/patients/{id}/records - Medical records
- GET /api/patients/{id}/medications - Active prescriptions
- GET /api/patients/{id}/allergies - Allergy information

### Appointments
- GET/POST /api/appointments - Appointment scheduling
- GET /api/providers/{id}/availability - Provider schedules
- POST /api/appointments/{id}/cancel - Cancellation
- POST /api/appointments/{id}/reschedule - Rescheduling

### Medical Records
- GET /api/records/{id} - Retrieve specific record
- GET /api/records/search - Search records
- POST /api/records/{id}/share - Share with provider
- GET /api/records/{id}/history - Access history audit

### Messaging
- POST /api/messages - Secure messaging to providers
- GET /api/messages/inbox - Patient inbox
- GET /api/messages/thread/{id} - Message thread

### Billing
- GET /api/billing/statements - Billing statements
- POST /api/billing/payment - Process payment
- GET /api/billing/insurance - Insurance information

## Integration Points
- Epic EHR system (HL7 v2 messages)
- Lab systems (HL7 ORU messages)
- Pharmacy systems (NCPDP SCRIPT)
- Insurance verification (X12 270/271)

## Security Architecture
- OAuth 2.0 + OpenID Connect for authentication
- JWT tokens with short expiration (15 min)
- Refresh token rotation
- API rate limiting per user/IP
- WAF rules for common attacks

## Tech Stack
- Backend: Python FastAPI
- Database: PostgreSQL with encryption
- Cache: Redis for session management
- Queue: RabbitMQ for async processing
- Monitoring: Datadog APM + custom HIPAA dashboards
