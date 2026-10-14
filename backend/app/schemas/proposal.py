"""Proposal and audit request/response schemas."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.enums import Classification, ProposalStatus
from app.models.proposal import BudgetItem


# --- inbound ---


class BudgetItemIn(BaseModel):
    item: str = Field(..., min_length=1, max_length=200)
    amount: float = Field(..., ge=0)


class ProposalCreate(BaseModel):
    subject: str = Field(..., min_length=3, max_length=200)
    purpose: str = Field(..., min_length=3, max_length=5000)
    department: str | None = Field(None, min_length=1, max_length=64)
    resources: list[str] = Field(default_factory=list)
    budget: list[BudgetItemIn] = Field(default_factory=list)
    policies: list[str] = Field(default_factory=list)
    identifiers: dict[str, str] = Field(default_factory=dict)
    responsible_officers: list[str] = Field(default_factory=list)
    start_date: date | None = None
    end_date: date | None = None
    classification: Classification = Classification.INTERNAL
    allowed_user_ids: list[str] = Field(default_factory=list)
    allowed_departments: list[str] = Field(default_factory=list)

    @field_validator("subject")
    @classmethod
    def _subject_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("subject cannot be blank")
        return value.strip()

    @field_validator("purpose")
    @classmethod
    def _purpose_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("purpose cannot be blank")
        return value.strip()

    @model_validator(mode="after")
    def _dates_ordered(self) -> "ProposalCreate":
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class ProposalUpdate(BaseModel):
    subject: str | None = Field(None, min_length=3, max_length=200)
    purpose: str | None = Field(None, min_length=3, max_length=5000)
    resources: list[str] | None = None
    budget: list[BudgetItemIn] | None = None
    policies: list[str] | None = None
    identifiers: dict[str, str] | None = None
    responsible_officers: list[str] | None = None
    start_date: date | None = None
    end_date: date | None = None
    reason: str = Field("", max_length=1000)

    @model_validator(mode="after")
    def _at_least_one_change(self) -> "ProposalUpdate":
        provided = [
            self.subject,
            self.purpose,
            self.resources,
            self.budget,
            self.policies,
            self.identifiers,
            self.responsible_officers,
            self.start_date,
            self.end_date,
        ]
        if all(value is None for value in provided):
            raise ValueError("provide at least one field to modify")
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class ReviewRequest(BaseModel):
    comment: str = Field("", max_length=2000)


class ReturnRequest(BaseModel):
    reason: str = Field(..., min_length=3, max_length=2000)


class DecideRequest(BaseModel):
    outcome: Literal["approved", "rejected"]
    reason: str = Field(..., min_length=3, max_length=2000)


# --- outbound ---


class DecisionOut(BaseModel):
    outcome: str
    version: int
    reason: str
    decided_by: str
    decided_at: datetime
    snapshot_hash: str


class ProposalOut(BaseModel):
    id: str
    subject: str
    purpose: str
    department: str
    status: ProposalStatus
    version: int
    resources: list[str] = Field(default_factory=list)
    budget: list[BudgetItem] = Field(default_factory=list)
    policies: list[str] = Field(default_factory=list)
    identifiers: dict[str, str] = Field(default_factory=dict)
    responsible_officers: list[str] = Field(default_factory=list)
    start_date: date | None = None
    end_date: date | None = None
    decisions: list[DecisionOut] = Field(default_factory=list)
    classification: Classification
    owner_id: str
    owner_department: str
    allowed_user_ids: list[str] = Field(default_factory=list)
    allowed_departments: list[str] = Field(default_factory=list)
    created_by: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_proposal(cls, proposal) -> "ProposalOut":  # noqa: ANN001
        return cls(
            id=proposal.id,
            subject=proposal.subject,
            purpose=proposal.purpose,
            department=proposal.department,
            status=proposal.status,
            version=proposal.version,
            resources=list(proposal.resources),
            budget=list(proposal.budget),
            policies=list(proposal.policies),
            identifiers=dict(proposal.identifiers),
            responsible_officers=list(proposal.responsible_officers),
            start_date=proposal.start_date,
            end_date=proposal.end_date,
            decisions=[
                DecisionOut(
                    outcome=d.outcome,
                    version=d.version,
                    reason=d.reason,
                    decided_by=d.decided_by,
                    decided_at=d.decided_at,
                    snapshot_hash=d.snapshot_hash,
                )
                for d in proposal.decisions
            ],
            classification=proposal.classification,
            owner_id=proposal.owner_id,
            owner_department=proposal.owner_department,
            allowed_user_ids=sorted(proposal.allowed_user_ids),
            allowed_departments=sorted(proposal.allowed_departments),
            created_by=proposal.created_by,
            created_at=proposal.created_at,
            updated_at=proposal.updated_at,
        )


class VersionOut(BaseModel):
    version: int
    content_hash: str
    changes: list[str]
    action: str
    actor_username: str
    reason: str
    created_at: datetime


class CommentOut(BaseModel):
    id: str
    kind: str
    author_username: str
    body: str
    version: int
    created_at: datetime


class TimelineEntryOut(BaseModel):
    at: datetime
    kind: Literal["audit", "comment"]
    source: str
    actor_username: str
    version: int | None
    message: str


class AuditEventOut(BaseModel):
    id: str
    seq: int
    actor_id: str
    actor_username: str
    action: str
    entity_type: str
    entity_id: str
    proposal_version: int | None
    content_hash: str | None
    outcome: str | None
    summary: str
    prev_hash: str | None
    event_hash: str
    created_at: datetime


class AuditVerifyOut(BaseModel):
    verified: bool
    checked: int
    first_bad_seq: int | None = None