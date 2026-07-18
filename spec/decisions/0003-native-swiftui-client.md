# 0003 — Native SwiftUI client

- Status: Accepted
- Date: 2026-07-18
- Deciders: Engineering / Product

## Context

Daily Sketch is an iOS-first creative product that needs camera, photo library, notifications, share sheet, and native accessibility behaviours.

## Decision

Ship a native SwiftUI application with:

- minimum deployment target iOS 18.0;
- primary module name `DailySketch`;
- display name Daily Sketch;
- Swift Concurrency;
- OpenAPI-generated API types wrapped by repositories.

Do not replace the client with React Native, Flutter, or a web wrapper without an approved ADR and specification update.

## Consequences

- Version one does not include Android or web clients.
- Bundle identifiers and signing remain owner-supplied placeholders until production release.
- Design uses semantic tokens and SF typography rather than bundling Inter from Stitch web exports.
