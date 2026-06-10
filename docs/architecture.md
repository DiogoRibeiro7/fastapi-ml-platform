# Architecture

The application uses a layered architecture.

## Layers

### API layer

The API layer defines routes, HTTP status codes, request schemas, and response schemas. Route handlers should stay thin.

### Service layer

The service layer owns business logic. For example, `PredictionService` handles feature creation, model scoring, decision mapping, and persistence coordination.

### Repository layer

The repository layer owns database operations. SQLAlchemy queries should not be scattered across route handlers or services.

### ML layer

The ML layer owns model loading, feature engineering, explainability, and drift utilities.

## Request flow

```text
HTTP request
  -> FastAPI route
  -> dependencies
  -> service
  -> ML model and repository
  -> response schema
```

## Startup flow

```text
App lifespan startup
  -> configure logging
  -> create async database engine
  -> create tables
  -> load model bundle
```

## Design choices

- The app uses an app factory for testability.
- Database sessions are request-scoped.
- Model loading happens once during startup.
- Protected endpoints use API-key authentication.
- Health and readiness endpoints are public.
- The fallback model keeps the API runnable without model artifacts.
