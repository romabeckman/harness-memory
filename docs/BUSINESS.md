# Harness Memory — Product Objective

## Overview

**Harness Memory** is a corporate engineering memory platform designed to give AI agents and engineering tools a shared understanding of how software systems relate across repositories.

In complex organizations, knowledge about services, APIs, events, ownership, dependencies, and implementation details is distributed across source code, documentation, contracts, infrastructure, and individual repositories. Most development agents operate with strong local context but limited organizational awareness.

Harness Memory addresses this gap by creating a persistent, queryable layer of knowledge that connects information across projects.

## Product Objective

The objective of Harness Memory is to make organizational software knowledge **discoverable, explainable, and reusable**.

Instead of storing only isolated facts, the product maintains relationships between engineering entities such as:

* Repositories
* Projects
* Services
* APIs
* Events
* Teams
* Dependencies

Each relationship can include supporting **evidence, provenance, lifecycle status, and revision history**, allowing consumers to understand not only *what is known*, but also *why it is believed to be true and how it has changed over time*.

## Business Value

Harness Memory enables engineering organizations to reduce the cost of rediscovering architectural knowledge and improve the quality of automated engineering decisions.

It is intended to help answer questions such as:

* Which services consume this API?
* What projects may be affected by this contract change?
* Who owns this dependency?
* What evidence supports this relationship?
* Has this information changed or become outdated?

This context can support impact analysis, dependency discovery, onboarding, architectural understanding, and AI-assisted software development.

## Product Boundaries

The MVP focuses on two core capabilities:

**MCP Interface**
A standardized interface through which AI agents and engineering tools can read and contribute corporate knowledge.

**Persistent Corporate Memory**
A database-backed knowledge layer that stores entities, relationships, evidence, provenance, status, and historical revisions.

MCP operations are intentionally separated into **read** and **write** capabilities so that retrieving knowledge is distinct from proposing or changing it.

## Product Principle

A core principle of Harness Memory is:

> **Discovered information should not automatically become trusted corporate knowledge.**

A relationship may begin as a candidate, gain supporting evidence, become confirmed, and later become stale, disputed, or superseded.

By preserving this lifecycle and its history, Harness Memory aims to become a reliable organizational context layer for both humans and AI systems.
