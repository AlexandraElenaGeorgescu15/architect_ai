# Phone Swap Request Feature - Complete Handoff Package

## Overview

This package provides a complete implementation of the Phone Swap Request feature, including Angular frontend and .NET/C# backend components. The feature allows users to submit requests to swap their current phone with another available phone.

## 📁 Package Contents

### 🚀 Angular Frontend

- `frontend/src/app/components/phone-swap-request.component.ts` - Angular component for the phone swap request form.
- `frontend/src/app/components/phone-swap-request.component.html` - HTML template for the phone swap request form.
- `frontend/src/app/services/phone-swap-request.service.ts` - Angular service for communicating with the backend API.

### 🎯 .NET/C# Backend

- `backend/Controllers/PhoneSwapRequestController.cs` - .NET API controller for handling phone swap requests.
- `backend/Models/PhoneSwapRequestDto.cs` - .NET DTO for representing phone swap request data.
- `backend/Services/PhoneSwapRequestService.cs` - .NET service containing the business logic for handling phone swap requests.
- `backend/Data/PhoneSwapRequestRepository.cs` - .NET repository for data access related to phone swap requests.

## 🚀 Quick Start

### Prerequisites

- Node.js 18+ LTS
- Angular CLI 17+
- .NET SDK 7.0+
- npm or yarn
- An IDE such as Visual Studio or VS Code

### Running the Application

#### 1. Backend Setup

```bash
# Navigate to the backend directory
cd backend

# Restore dependencies
dotnet restore

# Build the project
dotnet build

# Run the application
dotnet run
```

The backend API will be accessible at `https://localhost:{PORT}/api/PhoneSwapRequest`, where `{PORT}` is the port number configured in your `launchSettings.json` file (typically 5001 for HTTPS and 5000 for HTTP).

#### 2. Frontend Setup

```bash
# Navigate to the frontend directory
cd frontend

# Install dependencies
npm install

# Start the development server
ng serve
```

The Angular application will be accessible at `http://localhost:4200`.

## 🧪 Testing the Feature

1. Navigate to the Phone Swap Request page in the Angular application.
2. Fill out the form with the required information (current phone, desired phone, contact information, etc.).
3. Submit the request.
4. Verify that the request is successfully submitted and processed by the backend API.

## 📚 API Endpoints

### POST `/api/PhoneSwapRequest/request`

- Creates a new phone swap request.
- Accepts a `PhoneSwapRequestDto` object in the request body.
- Returns a success message or an error message if the request fails.

## 🛠️ Technical Stack

- **Frontend**: Angular, TypeScript, Angular Material, RxJS
- **Backend**: .NET, C#, ASP.NET Core Web API, Entity Framework Core (if applicable)