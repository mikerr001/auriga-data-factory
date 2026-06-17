"""Approval module — dataset promotion workflow with immutability enforcement."""
from .workflow import ApprovalWorkflow, ApprovalError

__all__ = ["ApprovalWorkflow", "ApprovalError"]
