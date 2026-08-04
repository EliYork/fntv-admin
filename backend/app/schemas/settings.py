from __future__ import annotations

from pydantic import BaseModel, Field


class AuthPolicyUpdate(BaseModel):
    local_auth_required: bool
    remote_access_policy: str = Field(pattern="^(login|deny)$")


class SnapshotSettingUpdate(BaseModel):
    snapshot_enabled: bool
    snapshot_refresh_interval_seconds: int | None = Field(default=None, ge=0, le=7 * 24 * 3600)
