# ☕ LOKAL

> **Discover local coffee shops. Support local businesses. Let AI help you choose what to try next.**

---

## Overview

LOKAL is an AI-powered mobile application that helps users discover independent coffee shops nearby. By combining location-based search with AI-generated review summaries, LOKAL makes it easier to find great cafés and decide what to order.

The long-term vision is to build a platform that not only helps coffee lovers discover hidden gems, but also gives local coffee shops greater visibility within their communities.

Initially, AI recommendations will be generated from publicly available Google reviews. As the platform grows and users contribute their own reviews, the recommendation engine will gradually rely more on community-generated content.

---

## Why LOKAL?

Many excellent local coffee shops are overlooked because they lack the visibility of larger chains.

LOKAL aims to support local businesses by making discovery easier while helping users quickly understand what makes each café unique through concise AI-generated insights.

---

## Core Features

### Implemented Features

* 📍 Discover nearby local coffee shops
* 🗺️ Interactive map-based browsing
* 🤖 AI-generated review summaries
* ☕ "Must Try" coffee or menu recommendations
* ⭐ First-party user reviews and ratings
* ❤️ Favorite coffee shops
* 🔍 Advanced search and filtering
* 👤 User authentication and session management
* ✨ Personalized coffee shop recommendations
* 🏪 Coffee shop owner claiming and dashboard
* 👥 Community feed and social sharing

### Planned Features

* 📸 Coffee shop menus and photo gallery (future exploration)

---

## Technology Stack

### Mobile

* React Native
* Expo

### Backend

* FastAPI
* Python

### Database & Authentication

* Supabase (PostgreSQL)

### AI

* AI-powered review summarization and recommendation engine

### Development Tools

* Git
* GitHub
* Antigravity CLI
* CodeRabbit
* GitHub Actions (planned)

---

## High-Level Architecture

```text
React Native (Expo)
        │
        ▼
     FastAPI
        │
        ├── Supabase (PostgreSQL & Authentication)
        └── AI Services
```

---

## Development Workflow

LOKAL is built using the **Zero Cost AI Workflow**, an AI-assisted software development process designed to maximize engineering quality while minimizing or no development costs.

The workflow combines:

* Feature planning through GitHub Issues
* Architecture-first development
* AI-assisted implementation with Antigravity CLI
* Automated testing
* AI code reviews with CodeRabbit
* Human review before merging

---

## Project Documentation

* [System architecture](docs/architecture.md)
* [Engineering workflow](docs/workflow.md)
* [Current project state](docs/CURRENT_STATE.md)
* [Approved UI design specification](docs/ui-design-spec.md)
* [Reusable engineering prompts](docs/prompts/)

---

## Project Status

🚧 **Phase 3 — MVP Polish & Validation**

The core MVP capabilities are implemented. Current work focuses on establishing a realistic, development-safe validation dataset, testing the discovery-to-AI-summary experience end-to-end, and refining the UI/UX using the approved design direction. See [the current project state](docs/CURRENT_STATE.md) for implementation details and [the LOKAL UI design specification](docs/ui-design-spec.md) for the approved visual rules.

---

## Project Goals

This project is being built to:

* Learn modern mobile application development with React Native and Expo.
* Build scalable backend services with FastAPI.
* Explore AI-assisted software engineering workflows.
* Apply professional development practices as a solo developer.
* Support local coffee shops through technology.

---

## License

This project is currently not licensed.
