"""
Unit tests — Observability module
===================================
Tests for the structured logger and research debt register.
"""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from ..observability.logger import AurigaLogger, get_logger
from ..observability.research_debt import ResearchDebt, ResearchDebtRegister


class TestAurigaLogger(unittest.TestCase):

    def test_logger_creation(self):
        logger = AurigaLogger("test.logger")
        self.assertIsNotNone(logger)

    def test_get_logger_returns_same_instance(self):
        l1 = get_logger("test.singleton")
        l2 = get_logger("test.singleton")
        self.assertIs(l1, l2)

    def test_log_to_file(self):
        with TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "test.jsonl"
            logger = AurigaLogger("test.file_logger", log_file=log_path)
            logger.info("Test message")
            logger.ingestion("Ingestion event", dataset_id="test-123")
            logger.validation("Validation event")
            logger.promotion("Promotion event")
            logger.warning("Warning message")
            self.assertTrue(log_path.exists())

    def test_research_debt_log(self):
        with TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "debt.jsonl"
            logger = AurigaLogger("test.debt_logger", log_file=log_path)
            logger.research_debt("RD-DATA-001", "Test uncertainty assumption")
            self.assertTrue(log_path.exists())


class TestResearchDebt(unittest.TestCase):

    def test_create_debt(self):
        debt = ResearchDebt(
            debt_id="RD-DATA-099",
            title="Test debt",
            description="This is a test debt item.",
            severity="low",
            subsystem="testing",
        )
        self.assertEqual(debt.debt_id, "RD-DATA-099")
        self.assertFalse(debt.resolved)

    def test_invalid_severity_raises(self):
        with self.assertRaises(ValueError):
            ResearchDebt(
                debt_id="RD-X-001",
                title="Bad debt",
                description="Invalid severity.",
                severity="catastrophic",
            )


class TestResearchDebtRegister(unittest.TestCase):

    def test_built_in_debts_present(self):
        register = ResearchDebtRegister()
        items = register.all_items()
        ids = {d.debt_id for d in items}
        self.assertIn("RD-DATA-001", ids)
        self.assertIn("RD-DATA-002", ids)
        self.assertIn("RD-DATA-003", ids)
        self.assertIn("RD-DATA-004", ids)

    def test_add_custom_debt(self):
        register = ResearchDebtRegister()
        register.add(ResearchDebt(
            debt_id="RD-DATA-099",
            title="Custom",
            description="Custom debt.",
            subsystem="testing",
        ))
        ids = {d.debt_id for d in register.all_items()}
        self.assertIn("RD-DATA-099", ids)

    def test_resolve_debt(self):
        register = ResearchDebtRegister()
        register.resolve("RD-DATA-001", "Resolved by adding better uncertainty model.")
        resolved = next(d for d in register.all_items() if d.debt_id == "RD-DATA-001")
        self.assertTrue(resolved.resolved)
        self.assertIsNotNone(resolved.resolution_notes)

    def test_resolve_nonexistent_raises(self):
        register = ResearchDebtRegister()
        with self.assertRaises(KeyError):
            register.resolve("RD-DATA-NONEXISTENT", "notes")

    def test_unresolved_returns_only_unresolved(self):
        register = ResearchDebtRegister()
        register.resolve("RD-DATA-001", "Done.")
        unresolved = register.unresolved()
        ids = {d.debt_id for d in unresolved}
        self.assertNotIn("RD-DATA-001", ids)

    def test_as_markdown_contains_all_ids(self):
        register = ResearchDebtRegister()
        md = register.as_markdown()
        self.assertIn("RD-DATA-001", md)
        self.assertIn("RD-DATA-002", md)
        self.assertIn("# Research Debt Register", md)

    def test_persistence_round_trip(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "debt_register.jsonl"
            r1 = ResearchDebtRegister(register_path=path)
            r1.add(ResearchDebt(
                debt_id="RD-DATA-090",
                title="Persisted debt",
                description="This should survive round-trip.",
                subsystem="testing",
            ))
            # Load fresh instance from same file.
            r2 = ResearchDebtRegister(register_path=path)
            ids = {d.debt_id for d in r2.all_items()}
            self.assertIn("RD-DATA-090", ids)


if __name__ == "__main__":
    unittest.main()
