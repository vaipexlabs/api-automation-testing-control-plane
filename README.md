# Vaipex API Automation Testing Control Plane

An open reference implementation for comprehensive, repeatable, and evidence-backed API quality validation through one consistent engineering experience.

Developed by **Vaipex Labs** for the developer, quality engineering, test automation, and platform engineering communities.

[![API quality control plane](https://github.com/vaipexlabs/api-automation-testing-control-plane/actions/workflows/api-quality.yml/badge.svg)](https://github.com/vaipexlabs/api-automation-testing-control-plane/actions/workflows/api-quality.yml)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Pytest](https://img.shields.io/badge/Test-Pytest-0A9EDC?logo=pytest&logoColor=white)
![FastAPI](https://img.shields.io/badge/API-FastAPI-009688?logo=fastapi&logoColor=white)
![HTTPX](https://img.shields.io/badge/Client-HTTPX-6D42E8)
![License](https://img.shields.io/badge/License-Apache%202.0-blue)

[Two-Minute Demo](#two-minute-demo) · [Capabilities](#capabilities) · [HTTP Coverage](#http-method-coverage) · [How It Works](#how-it-works) · [Test Suites](#test-suites) · [Quality Evidence](#quality-evidence) · [Local API](#run-the-api-locally) · [CI](#continuous-enforcement)

## Why This Project Exists

API automation is more than sending requests and asserting status codes. A credible release signal must validate behavior, contracts, authorization, failure handling, idempotency, concurrency, and the evidence behind the final decision.

This repository packages those concerns as one reusable control plane. The same supported command runs locally and in GitHub Actions, exercises a deterministic reference API, retains human- and machine-readable evidence, and returns an explainable `PASS` or `HOLD` decision.

## Two-Minute Demo

Prerequisites: macOS or Linux, Git, and Python 3.12.

```bash
git clone https://github.com/vaipexlabs/api-automation-testing-control-plane.git
cd api-automation-testing-control-plane
./scripts/setup.sh
./scripts/two-minute-demo.sh
```

After the one-time setup, the demo completes in under two minutes. It validates the locked toolchain, applies static checks, runs every API quality layer, generates evidence, evaluates the versioned policy, and prints the release decision.

A successful run ends with:

```text
PASS: the API satisfied the versioned Vaipex quality policy.
```

Open `reports/api-automation.html` for the test report and `reports/quality-decision.json` for the machine-readable decision.

## Capabilities

- Deterministic FastAPI order service with seeded data and controlled failures
- Reusable asynchronous HTTPX client and environment configuration
- Every application-relevant HTTP verb, including explicit `TRACE` and `CONNECT` rejection
- Request, response, header, error, and OpenAPI contract validation
- Positive, malformed, negative, minimum, maximum, and out-of-range scenarios
- Authentication, role authorization, and ownership-boundary enforcement
- Pagination, filtering, sorting, `ETag`, and conditional caching semantics
- Idempotent `PUT`, idempotency-key replay, and concurrent request validation
- Rate-limit, dependency failure, timeout, retry, and retry-exhaustion tests
- HTML, JUnit XML, coverage JSON, and release-decision JSON evidence
- Versioned quality policy with an explicit `PASS` or `HOLD` outcome
- GitHub Actions enforcement with retained evidence artifacts

## HTTP Method Coverage

| Method | Behavior under test |
| --- | --- |
| `GET` | Collections, resources, paging, filters, sorting, cache validation |
| `POST` | Creation, validation, ownership, and idempotency keys |
| `PUT` | Complete replacement and safe repeated execution |
| `PATCH` | Partial mutation without losing untouched fields |
| `DELETE` | Resource removal and defined repeat-delete behavior |
| `HEAD` | Representation metadata without a response body |
| `OPTIONS` | Supported methods and CORS method policy |
| `TRACE` | Explicit application-policy rejection |
| `CONNECT` | Explicit proxy-tunnelling rejection |

## How It Works

API intent moves through reusable execution, layered validation, governed controls, correlated evidence, and one transparent quality decision.

![Vaipex API automation testing flow](docs/images/vaipex-api-automation-flow.svg)

Developers and GitHub Actions invoke the same Python control layer. Reusable HTTPX clients exercise the FastAPI service while functional, contract, security, and resilience suites generate evidence for the release gate.

![Vaipex API automation testing architecture](docs/images/vaipex-api-automation-architecture.svg)

## Test Suites

| Suite | Purpose | Command |
| --- | --- | --- |
| Functional | Complete resource lifecycle and HTTP semantics | `.venv/bin/pytest -q -m functional` |
| Contract | OpenAPI, schemas, boundaries, query controls, and caching | `.venv/bin/pytest -q -m contract` |
| Security | Authentication, authorization, ownership, and method rejection | `.venv/bin/pytest -q -m security` |
| Resilience | Failure modes, retries, idempotency, and concurrency | `.venv/bin/pytest -q -m resilience` |
| Complete | All unit and API quality checks | `./scripts/test.sh` |

Tests run against the application in process through HTTPX's ASGI transport. This keeps execution fast and deterministic while still exercising routing, serialization, middleware, authentication, and HTTP response behavior.

## Quality Evidence

Run the governed gate directly:

```bash
./scripts/quality-gate.sh
```

The gate reads [`policies/quality-gate.json`](policies/quality-gate.json) and publishes:

| Evidence | File | Consumer |
| --- | --- | --- |
| Interactive test report | `reports/api-automation.html` | Engineers and reviewers |
| JUnit test results | `reports/junit.xml` | CI and test-reporting systems |
| Coverage result | `reports/coverage.json` | Quality policy and analysis tools |
| Release decision | `reports/quality-decision.json` | Automation and governance workflows |

The current policy requires zero test failures, zero execution errors, and at least 85% coverage. Any violation produces `HOLD` with the reasons recorded in the decision file.

## Run the API Locally

Start the real HTTP server:

```bash
./scripts/start-api.sh
```

Open the interactive API documentation at [http://127.0.0.1:8080/docs](http://127.0.0.1:8080/docs). Use `Control-C` to stop it, or choose another port with `PORT=8081 ./scripts/start-api.sh`.

The following non-secret demo identities make authorization scenarios repeatable:

| Bearer token | Identity | Permission |
| --- | --- | --- |
| `demo-admin-token` | `admin-001` | All resources and test reset |
| `demo-operator-token` | `user-001` | Read and write owned resources |
| `demo-other-token` | `user-002` | Second ownership boundary |
| `demo-viewer-token` | `user-003` | Read-only access to owned resources |

Example:

```bash
curl -s http://127.0.0.1:8080/v1/orders \
  -H 'Authorization: Bearer demo-operator-token'
```

Use `X-Vaipex-Failure: dependency`, `rate-limit`, or `timeout` to trigger a deterministic failure. An administrator can restore the three seeded orders with `POST /v1/admin/reset`.

## Continuous Enforcement

The [GitHub Actions workflow](.github/workflows/api-quality.yml) runs the exact two-minute demo on pull requests, pushes to `main`, and manual dispatches. It uploads the complete `reports/` directory for 14 days even when a quality check fails, preserving the evidence needed to diagnose a `HOLD` decision.

## Repository Structure

```text
.github/workflows/   Continuous API quality enforcement
docs/images/         Vaipex flow and architecture illustrations
policies/            Versioned release thresholds
scripts/             Setup, validation, quality gate, API, and demo commands
src/                 Reference API and reusable automation control plane
tests/contract/      Schema, boundary, query, and caching validation
tests/functional/    Resource workflows and HTTP method semantics
tests/security/      Identity, permission, ownership, and method controls
tests/resilience/    Failure, retry, idempotency, and concurrency scenarios
```

## Project Boundaries

This project demonstrates API automation and quality governance. It does not replace penetration testing, production observability, capacity engineering, or product risk ownership. It supplies a transparent engineering signal for safer API delivery decisions.

## Contributing

Community contributions are welcome. Keep scenarios deterministic, contracts explicit, evidence complete, and quality decisions explainable.

Licensed under the [Apache License 2.0](LICENSE).
