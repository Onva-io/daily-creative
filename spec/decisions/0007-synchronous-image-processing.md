# 0007 — Synchronous Image Processing

- Status: Accepted
- Date: 2026-07-18
- Deciders: Engineering

## Context

Uploaded originals need validation (decode, dimensions, MIME), EXIF stripping, orientation normalisation, and display/thumbnail derivatives before a submission can publish. Version one traffic and infrastructure Option A do not yet justify a separate worker queue.

## Decision

Image processing runs **synchronously** inside the upload-complete request using Pillow: decode and validate, strip EXIF, normalise orientation, write `display` and `thumbnail` derivatives, and record size/dimensions on the upload row. Bounded input size (`MAX_UPLOAD_BYTES`) keeps CPU/memory cost predictable.

## Consequences

- Upload-complete latency includes processing time; keep derivatives and max dimensions conservative.
- Failures return typed errors (`invalid_image`, `image_too_large`, `object_missing`, …) so clients can retry or replace the photo.
- Introducing async workers/queues later requires measured need and a new ADR.
