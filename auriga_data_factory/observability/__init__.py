"""Observability module — structured logging with research debt tracking."""
from .logger import AurigaLogger, get_logger
from .research_debt import ResearchDebtRegister, ResearchDebt

__all__ = ["AurigaLogger", "get_logger", "ResearchDebtRegister", "ResearchDebt"]
