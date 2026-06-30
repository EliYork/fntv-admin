from __future__ import annotations

from pydantic import BaseModel, Field


class AuthPolicyUpdate(BaseModel):
    local_auth_required: bool
    remote_access_policy: str = Field(pattern="^(login|deny)$")


class SnapshotSettingUpdate(BaseModel):
    snapshot_enabled: bool
