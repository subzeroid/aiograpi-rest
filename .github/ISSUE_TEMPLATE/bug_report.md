---
name: Bug report
about: Report a reproducible aiograpi-rest bug
title: "[BUG] "
labels: bug

---

**Describe the bug**
A clear description of what failed.

**Endpoint**
Example: `POST /auth/login`, `GET /user/about`, `POST /story/upload`.

**To reproduce**
Provide the smallest curl command, HTTP request, or client snippet that shows
the problem. Remove secrets before posting.

**Expected behavior**
What response or behavior did you expect?

**Actual behavior**
Include the HTTP status code and response body.

**Environment**
- aiograpi-rest version:
- Run mode: Docker image / Docker Compose / local Python
- Python version, if running locally:
- Docker image tag, if using Docker:
- aiograpi version, from `GET /deps`:

**Traceback or logs**
Paste the relevant server traceback, container logs, or GitHub Actions log.

**Additional context**
Screenshots, OpenAPI screenshots, or notes about proxies/challenges can help.
