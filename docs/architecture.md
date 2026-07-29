# System Architecture

This document describes the high-level architecture of LOKAL and defines the responsibilities of each major component. It serves as the technical blueprint for all future development.

---

# Design Principles

LOKAL follows these architectural principles:

* Keep the mobile application focused on user experience.
* Keep business logic inside the backend.
* Keep AI integrations isolated behind the backend.
* Treat Supabase as managed infrastructure rather than the application's backend.
* Design for maintainability, scalability, and clear separation of responsibilities.

---

# High-Level Architecture

```text
                    React Native (Expo)
                             │
                             │ HTTPS
                             ▼
                      FastAPI Backend
                  (Business Logic & API)
                      │            │
                      │            │
                      ▼            ▼
        Supabase PostgreSQL     AI Services
      (Database & Auth)      (Review Summaries)
```

---

# Component Responsibilities

## Mobile Application (React Native + Expo)

Responsible for:

* User interface
* Navigation
* Interactive maps
* Coffee shop discovery
* Displaying AI-generated recommendations
* User authentication flow
* Managing local application state

The mobile application should remain lightweight and should never contain business logic or AI integrations directly.

---

## Backend (FastAPI)

Responsible for:

* REST API endpoints
* Business logic
* Authentication and authorization
* AI orchestration
* External API integrations
* Validation
* Data processing

FastAPI acts as the central coordinator of the application.

All communication between the mobile application and external services should flow through the backend whenever practical.

---

## Database (Supabase)

Supabase provides the managed PostgreSQL database and authentication services.

Responsibilities include:

* User accounts
* Coffee shop data
* User reviews
* Favorites
* Application data
* Secure authentication

Future services may include:

* File Storage
* Row Level Security (RLS)
* Realtime features

---

## AI Layer

The AI layer is responsible for transforming raw review data into meaningful insights.

Examples include:

* Review summarization
* "Must Try" menu recommendations
* Sentiment analysis
* Future personalized recommendations

AI providers are considered replaceable implementation details.

The rest of the system should remain independent of any specific AI vendor.

---

# Data Flow

A typical request follows this path:

```text
User
  │
  ▼
Mobile App
  │
  ▼
FastAPI
  │
  ├── Database Query
  │
  ├── AI Processing
  │
  ▼
Response
  │
  ▼
Mobile App
```

The mobile application should not communicate directly with AI providers.

---

# Project Structure

```text
lokal/

├── mobile/
│   └── React Native (Expo)
│
├── backend/
│   └── FastAPI
│
├── docs/
│   ├── architecture.md
│   ├── workflow.md
│   └── CURRENT_STATE.md
│
├── .github/
│   └── workflows/
│
├── README.md
├── AGENTS.md
└── .env.example
```

---

# Future Architecture

As the project evolves, additional services may be introduced, including:

* Push notifications
* Analytics
* Background jobs
* Image storage
* Recommendation engine improvements
* Administrative dashboard

These additions should preserve the existing separation of concerns whenever possible.

---

# Architectural Rules

The following rules should guide all implementation decisions:

1. Business logic belongs in the FastAPI backend.
2. The mobile application should focus on presentation and user interaction.
3. AI providers must only be accessed through the backend.
4. Secrets and API keys must never be exposed to the mobile application.
5. Components should communicate through clearly defined interfaces.
6. New features should integrate into the existing architecture rather than bypass it.
7. Prefer simple, maintainable solutions over unnecessary complexity.

---

# Guiding Principle

The architecture exists to make future development predictable.

Every new feature should have an obvious place within the system. If a feature does not naturally fit the architecture, the architecture should be reviewed before implementation proceeds.
