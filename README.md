```markdown
# beltourbot

Belarus Tourism Telegram Bot is a multi?language travel assistant on Telegram, built with Python (Aiogram, FastAPI), PostgreSQL, Redis and Celery. It offers curated route exploration, interactive quizzes, gamification with badges and scratch maps, geolocation-based recommendations, premium audio guides and offline access via local ERIP payments. A React-based admin dashboard provides content, user and revenue management. Containerized with Docker Compose, monitored via Prometheus/Grafana, and CI/CD-ready.

## Table of Contents
- [Overview](#overview)
- [Features](#features)
  - [User Features](#user-features)
  - [Admin Dashboard Features](#admin-dashboard-features)
- [Architecture](#architecture)
- [Flow](#flow)
- [Installation](#installation)
  - [Prerequisites](#prerequisites)
  - [Clone & Setup](#clone--setup)
  - [Running with Docker Compose](#running-with-docker-compose)
- [Configuration](#configuration)
- [Usage](#usage)
  - [Bot Commands & Buttons](#bot-commands--buttons)
  - [Health Check](#health-check)
- [Components](#components)
- [Dependencies](#dependencies)
- [Contributing](#contributing)
- [License](#license)

## Overview
beltourbot helps travelers discover Belarus:
- Multi-language onboarding (RU, BY, EN, ZH)  
- Explore routes by category, difficulty, family-friendly, adventure  
- Interactive quizzes & challenges with badges and discounts  
- Gamified travel map and daily cultural facts  
- Premium perks: exclusive routes, audio guides, offline access, ad-free  
- Geolocation-based ?Nearby Routes?  
- React admin UI for content, ad, user and revenue management  

## Features

### User Features
- **Multi-Language Onboarding**: Select or change your language at any time.  
- **Explore Routes**: Filter by category (History, Nature, Cities, Secret Sites), difficulty, family-friendly.  
- **Quests & Challenges**: On-route quizzes, QR-code unlocks, rewards (badges, promo codes).  
- **Premium**: Unlock secret tours, audio guides, offline data, ad-free UI, 1-day trial.  
- **My Travel Map**: Scratch map of visited regions, earned badges (?Explorer of Castles?).  
- **Daily Travel Fact**: `/dailyfact` or automatic push with cultural trivia.  
- **Travel Checklist**: Predefined packing lists by route type.  
- **Nearby Routes**: Share location, get suggestions within 20?50 km.  
- **Quick Profile**: `/profile` shows username, completed routes, badges, premium status.  
- **Contact / Feedback**: Send feedback or report issues, rate routes.  
- **Share Route**: Deep-link shareable route cards.

### Admin Dashboard Features
- **Dashboard**: Active users, popular routes, revenue summaries, notifications.  
- **Route Management**: Add/edit/delete routes with multilingual fields, map plotting, images, audio; bulk CSV uploads.  
- **Quests & Challenges**: Create quizzes, hints, rewards; generate & track QR codes.  
- **Ads & Partnerships**: Manage sponsored pins, promo codes, partner commission.  
- **User & Revenue Insights**: Filter by tier, favorite routes, quiz completions; export reports.  
- **Content Moderation**: Approve/reject reviews and photos; auto-translation suggestions.  
- **Notifications**: Broadcast to all or segmented users.  
- **Roles & Permissions**: Super Admin, Content Editor, Partnership Manager, Finance.  
- **Versioning & Rollback**: Track edits and revert.  
- **Integrations**: Redis cache, Celery tasks, Prometheus/Grafana monitoring, CI/CD.  

## Architecture
- **Bot Service** (Aiogram): Handles Telegram updates, inline keyboards, commands.  
- **API Service** (FastAPI): Business logic, data access, admin endpoints.  
- **Database**: PostgreSQL for core data.  
- **Cache & Queue**: Redis for caching and Celery broker.  
- **Async Tasks**: Celery workers for scheduled jobs (daily facts, QR batch, bulk imports).  
- **Admin UI**: React SPA consuming FastAPI.  
- **Monitoring**: Prometheus metrics, Grafana dashboards.  
- **Deployment**: Docker Compose (extensible to Kubernetes), health/readiness probes, rate-limiting middleware.

## Flow
1. **User** interacts in Telegram ?  
2. **Bot Service** Aiogram handler receives update ?  
3. Calls **FastAPI** (or direct DB/Redis) ?  
4. FastAPI applies logic, queries PostgreSQL/Redis ?  
5. Response formatted & returned by Bot Service ?  
6. **Celery** processes background jobs (pushes, QR, imports) ?  
7. **Admin** uses React UI ? FastAPI endpoints ?  
8. **Prometheus/Grafana** capture metrics across services.

## Installation

### Prerequisites
- Docker & Docker Compose  
- Git  
- (Optional) Python 3.9+ & virtualenv if running locally

### Clone & Setup
```bash
git clone https://github.com/your-org/beltourbot.git
cd beltourbot
cp config.example.ini config.ini
cp logging.example.ini logging.ini
# Edit config.ini: set TELEGRAM_TOKEN, DATABASE_URL, REDIS_URL, ERIP credentials, etc.
```

### Running with Docker Compose
```bash
docker-compose up -d
# Services: api, bot, redis, postgres, celery_worker
```
Access:
- Bot: in Telegram via your bot?s @username
- API docs: http://localhost:8000/docs
- Admin UI: http://localhost:3000 (or configured port)

## Configuration
All runtime settings live in `config.ini`:
```ini
[telegram]
token = YOUR_TELEGRAM_TOKEN

[database]
url = postgresql+asyncpg://user:pass@db:5432/beltourdb

[redis]
url = redis://redis:6379/0

[celery]
broker_url = redis://redis:6379/1
result_backend = redis://redis:6379/2

[payments]
erip_key = YOUR_ERIP_KEY
erip_secret = YOUR_ERIP_SECRET
```

## Usage

### Bot Commands & Buttons
- `/start` ? Begin onboarding & select language  
- `/change_language` ? Switch UI language  
- `/dailyfact` ? Receive today?s travel fact  
- `/explore` ? Browse available routes  
- `/profile` ? View your travel stats & badges  
- Share your location for ?Nearby Routes?  
- Tap buttons: **? Quests**, **? Premium**, **? Daily Fact**, etc.

### Health Check
```bash
curl http://localhost:8000/health
# {"status":"ok","uptime":"72h"}
```

## Components
- **main.py** ? Entrypoint: loads config & logging, initializes FastAPI, Aiogram bot, DB, cache, starts services.  
- **bot.py** ? Telegram handlers (commands, callbacks, user flows).  
- **database.py** ? Async SQLAlchemy + asyncpg setup.  
- **models.py** ? ORM models: Users, Routes, RoutePoints, Quizzes, Ads, Subscriptions, Badges.  
- **schemas.py** ? Pydantic schemas for request/response validation.  
- **crud.py** ? Database CRUD operations.  
- **admin_api.py** ? FastAPI routers for admin endpoints (routes, quizzes, analytics).  
- **celery_worker.py** ? Celery app & task definitions (daily facts, QR generation, bulk jobs).  
- **config.ini** ? Application configuration template.  
- **logging.ini** ? Logging configuration for console & file.  
- **docker-compose.yaml** ? Service definitions: api, bot, redis, postgres, celery.  
- **routes_bulk.csv** ? CSV template for bulk route uploads.  
- **messages.pot** ? gettext template for i18n extraction (RU, EN, BY, ZH).  
- **ads_config.xml** ? Sponsored ads & promo codes config.  
- **healthcheckendpoint.py** ? FastAPI liveness/readiness endpoints.  
- **ratelimitermiddleware.py** ? Request throttling middleware.  
- **languageswitcherhandler.py** ? Inline keyboard & handler for language switching.  
- **locationhandler.py** ? Processes user location & suggests nearby routes.  
- **deeplinkservice.py** ? Generate/parse Telegram deep links for sharing.  
- **paymentwebhookhandler.py** ? Handle ERIP/local payment webhooks.  
- **adminsidebar.js** ? React component for admin dashboard navigation.  
- **healthcheck.py** ? Health check utilities.  
- **ratelimiter.py** ? Core rate limiting logic.

## Dependencies
- Python 3.9+  
- FastAPI  
- Aiogram  
- SQLAlchemy & asyncpg  
- Pydantic  
- Celery  
- Redis & aioredis  
- Uvicorn  
- React (Admin UI)  
- Docker & Docker Compose  
- PostgreSQL  
- Prometheus & Grafana

## Contributing
1. Fork the repository  
2. Create a feature branch (`git checkout -b feature/xyz`)  
3. Commit your changes (`git commit -m "feat: add xyz"`)  
4. Push to your fork (`git push origin feature/xyz`)  
5. Open a Pull Request  

Please follow the [Code of Conduct](CODE_OF_CONDUCT.md) and style guidelines.

## License
This project is released under the MIT License. See [LICENSE](LICENSE) for details.
```