---
id: ENT-STD-SEC-001
title: Security Baseline
type: Standard
status: Approved
domain: Security
classification: internal
tags: [hardening, secrets, logging, encryption]
version: "2"
part_of_family: Security Baseline
owner: Security Architecture
summary: Minimum security controls every application must meet before production.
effective_date: 2026-02-01
last_reviewed: 2026-02-01
review_cycle_months: 12
relationships:
  supersedes: [ENT-STD-SEC-000]
  depends_on: [ENT-STD-DAT-001]
---

# Security Baseline

> Sample content. Replace this knowledge base with your organization's own standards.

## Requirements

1. **Encryption in transit.** All external and internal traffic uses TLS 1.2 or later.
2. **Encryption at rest.** Data classified `confidential` (see ENT-STD-DAT-001) is
   encrypted at rest with keys held in the managed key service.
3. **Secrets.** Secrets live in the approved secrets manager. They never appear in source
   control, container images or logs.
4. **Authentication.** User-facing applications authenticate through the enterprise
   identity provider using OpenID Connect.
5. **Security logging.** Authentication events, authorization failures and administrative
   actions are logged in the format defined by ENT-PAT-001.
