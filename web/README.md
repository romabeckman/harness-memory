# Harness Memory Web Console

Harness Memory Web is an administrative console for managing organizations (tenants), projects, service accounts, and access tokens. Operators can issue scoped tokens, review active credentials, and revoke tokens. A new token's secret is shown once, so copy it and store it securely when it is issued.

The Web app uses the Harness Memory REST API. API requests run on the server; the administrative token must remain private and must never use a `NEXT_PUBLIC_` variable.

## Run with Docker Compose

From the repository root, set `API_ADMIN_TOKEN` in the root `.env` file. Use the same secret for the API and Web console. Then start the Web service and its dependencies:

```sh
docker compose up --build web
```

Open [http://localhost:3000](http://localhost:3000) and sign in with `API_ADMIN_TOKEN`. The Web service runs in development mode and refreshes when files under `web/` change.

Stop the services with:

```sh
docker compose down
```

## Run locally

Requirements: Node.js 20 or later and a running Harness Memory REST API. Create `web/.env.local` with the API URL and the same administrative token used by the API:

```dotenv
HARNESS_API_URL=http://localhost:8080
API_ADMIN_TOKEN=replace-with-a-long-random-secret
```

From `web/`, install dependencies and start the development server:

```sh
npm ci
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). Keep `.env.local` private. Do not expose `API_ADMIN_TOKEN` through browser-side configuration.

## Tests

Run Web unit tests from `web/`:

```sh
npm run test
```

Run end-to-end tests with Playwright:

```sh
npm run test:e2e
```
