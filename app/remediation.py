"""Safe Kubernetes recommendation and guarded remediation API.

Default mode is dry-run: it only returns kubectl commands and never executes them.
Actual changes require an explicit opt-in flag and an allowlisted action.
"""
from __future__ import annotations

import os
import subprocess
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/remediation", tags=["remediation"])

ALLOW_EXECUTION = os.getenv("AIOPS_ALLOW_K8S_EXECUTION", "false").lower() == "true"
KUBECTL = os.getenv("KUBECTL_PATH", "kubectl")
NAMESPACE_ALLOWLIST = {
    item.strip()
    for item in os.getenv("AIOPS_ALLOWED_NAMESPACES", "default").split(",")
    if item.strip()
}
ALLOWED_DEPLOYMENTS = {
    item.strip()
    for item in os.getenv("AIOPS_ALLOWED_DEPLOYMENTS", "aiops-app").split(",")
    if item.strip()
}
COMMAND_TIMEOUT_SECONDS = 15


class RemediationRequest(BaseModel):
    action: str = Field(..., description="One of: restart_deployment, scale_deployment")
    deployment: str = Field(default="aiops-app", pattern=r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$")
    namespace: str = Field(default="default", pattern=r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$")
    replicas: int | None = Field(default=None, ge=1, le=10)
    dry_run: bool = True


def build_command(req: RemediationRequest) -> list[str]:
    if req.namespace not in NAMESPACE_ALLOWLIST:
        raise HTTPException(status_code=403, detail="Namespace is not allowlisted.")
    if req.deployment not in ALLOWED_DEPLOYMENTS:
        raise HTTPException(status_code=403, detail="Deployment is not allowlisted.")

    if req.action == "restart_deployment":
        return [
            KUBECTL, "rollout", "restart",
            f"deployment/{req.deployment}",
            "-n", req.namespace,
        ]

    if req.action == "scale_deployment":
        if req.replicas is None:
            raise HTTPException(status_code=422, detail="replicas is required for scale_deployment.")
        return [
            KUBECTL, "scale",
            f"deployment/{req.deployment}",
            f"--replicas={req.replicas}",
            "-n", req.namespace,
        ]

    raise HTTPException(status_code=422, detail="Unsupported action.")


def execute_command(command: list[str]) -> dict[str, Any]:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT_SECONDS,
            check=False,
            shell=False,
        )
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="kubectl was not found. Install/configure kubectl first.")
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="kubectl command timed out.")

    return {
        "returncode": result.returncode,
        "stdout": result.stdout[-4000:],
        "stderr": result.stderr[-4000:],
        "success": result.returncode == 0,
    }


@router.get("/status")
def remediation_status():
    return {
        "execution_enabled": ALLOW_EXECUTION,
        "default_mode": "dry_run",
        "allowed_namespaces": sorted(NAMESPACE_ALLOWLIST),
        "allowed_deployments": sorted(ALLOWED_DEPLOYMENTS),
        "supported_actions": ["restart_deployment", "scale_deployment"],
        "warning": "Kubernetes changes can disrupt workloads. Keep execution disabled until tested."
    }


@router.post("/plan")
def plan_remediation(req: RemediationRequest):
    command = build_command(req)
    return {
        "mode": "dry_run" if req.dry_run or not ALLOW_EXECUTION else "execute",
        "action": req.action,
        "deployment": req.deployment,
        "namespace": req.namespace,
        "replicas": req.replicas,
        "command_preview": command,
        "executed": False,
        "message": "No Kubernetes changes were made. Review this plan before enabling execution."
    }


@router.post("/execute")
def execute_remediation(req: RemediationRequest):
    if req.dry_run:
        command = build_command(req)
        return {
            "mode": "dry_run",
            "command_preview": command,
            "executed": False,
            "message": "dry_run=true: command was not executed."
        }
    if not ALLOW_EXECUTION:
        raise HTTPException(
            status_code=403,
            detail="Execution is disabled. Set AIOPS_ALLOW_K8S_EXECUTION=true only after reviewing and testing."
        )
    command = build_command(req)
    result = execute_command(command)
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result)
    return {
        "mode": "execute",
        "executed": True,
        "action": req.action,
        "deployment": req.deployment,
        "namespace": req.namespace,
        "result": result,
    }
