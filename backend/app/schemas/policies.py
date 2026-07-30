"""Policy document schemas."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.policy import PolicyDocument, PolicyKind, PolicyStatus


class PolicyKindSchema(str, Enum):
    terms = "terms"
    privacy = "privacy"
    community_guidelines = "community_guidelines"


class PolicyDocumentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    kind: PolicyKindSchema
    version: str
    title: str
    body_markdown: str
    content_hash: str
    minimum_age: int = Field(ge=1, le=120)
    is_significant_change: bool
    change_summary: str | None
    published_at: datetime | None

    @classmethod
    def from_orm(cls, document: PolicyDocument) -> PolicyDocumentResponse:
        return cls(
            id=document.id,
            kind=PolicyKindSchema(document.kind.value),
            version=document.version,
            title=document.title,
            body_markdown=document.body_markdown,
            content_hash=document.content_hash,
            minimum_age=document.minimum_age,
            is_significant_change=document.is_significant_change,
            change_summary=document.change_summary,
            published_at=document.published_at,
        )


class CurrentPoliciesResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    documents: list[PolicyDocumentResponse]


class AcceptPolicyItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: PolicyKindSchema
    version: str


class AcceptPoliciesRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    documents: list[AcceptPolicyItem] = Field(min_length=1)
    app_version: str | None = Field(default=None, max_length=64)
    platform: str | None = Field(default=None, max_length=32)
    locale: str | None = Field(default=None, max_length=32)


class AcceptedPolicyItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: PolicyKindSchema
    version: str
    accepted_at: datetime


class AcceptPoliciesResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    accepted: list[AcceptedPolicyItem]


class PolicyAcceptanceSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: PolicyKindSchema
    version: str
    accepted_at: datetime


class ConsentState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    consent_required: bool
    outstanding_kinds: list[PolicyKindSchema]
    accepted: list[PolicyAcceptanceSummary]
    current_documents: list[PolicyDocumentResponse]
    age_required: bool
    minimum_age: int


class SetDateOfBirthRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date_of_birth: str = Field(description="ISO date YYYY-MM-DD")


def policy_kind_from_schema(kind: PolicyKindSchema) -> PolicyKind:
    return PolicyKind(kind.value)


def policy_status_label(status: PolicyStatus) -> str:
    return status.value
