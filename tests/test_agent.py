import unittest

from agent import Agent, ERPError


class FakeERP:
    """Small deterministic ERP client double for proposal-flow tests."""

    def __init__(self, items=None, suppliers=None, fail_create=False):
        self.items = items if items is not None else [{"name": "RM-COIL-CU-2.0", "stock_uom": "Meter", "disabled": 0}]
        self.suppliers = suppliers if suppliers is not None else [{"name": "Tongling Magnet Wire Co."}]
        self.created = []
        self.reads = []
        self.fail_create = fail_create

    def list(self, doctype, fields=None, filters=None, limit=20, offset=0, order_by=None):
        if doctype == "Item":
            return self.items
        if doctype == "Supplier":
            return self.suppliers
        return []

    def create(self, doctype, doc):
        if self.fail_create:
            raise TimeoutError("simulated timeout")
        self.created.append((doctype, doc))
        return {"name": "PUR-TEST-0001"}

    def get(self, doctype, name):
        self.reads.append((doctype, name))
        return {"name": name, "status": "Draft", "items": [{"item_code": "RM-COIL-CU-2.0", "qty": 100}]}


class TestPurchaseOrderFlow(unittest.TestCase):
    def test_preview_does_not_write_until_confirm(self):
        erp = FakeERP()
        agent = Agent(erp)
        proposal = agent.proposal_po(
            "Tongling Magnet Wire Co.", "RM-COIL-CU-2.0", 100, "Meter", 29,
        )
        self.assertEqual(proposal["estimated_total"], "2900")
        self.assertTrue(proposal["requires_confirmation"])
        self.assertEqual(erp.created, [])

        result = agent.confirm(proposal["proposal_id"])
        self.assertEqual(result["name"], "PUR-TEST-0001")
        self.assertEqual(result["status"], "Draft")
        self.assertEqual(len(erp.created), 1)
        self.assertEqual(erp.reads, [("Purchase Order", "PUR-TEST-0001")])

    def test_unknown_proposal_is_rejected_without_write(self):
        erp = FakeERP()
        with self.assertRaises(ValueError):
            Agent(erp).confirm("does-not-exist")
        self.assertEqual(erp.created, [])

    def test_missing_item_and_supplier_are_reported(self):
        with self.assertRaisesRegex(ERPError, "Item not found"):
            Agent(FakeERP(items=[])).proposal_po("Tongling Magnet Wire Co.", "MISSING", 1, "Meter", 1)
        with self.assertRaisesRegex(ERPError, "Supplier not found"):
            Agent(FakeERP(suppliers=[])).proposal_po("MISSING", "RM-COIL-CU-2.0", 1, "Meter", 1)

    def test_uom_and_schedule_date_are_validated(self):
        agent = Agent(FakeERP())
        with self.assertRaisesRegex(ValueError, "UOM mismatch"):
            agent.proposal_po("Tongling Magnet Wire Co.", "RM-COIL-CU-2.0", 1, "kg", 1)
        with self.assertRaisesRegex(ValueError, "cannot be before"):
            agent.proposal_po(
                "Tongling Magnet Wire Co.", "RM-COIL-CU-2.0", 1, "Meter", 1,
                transaction_date="2025-10-15", schedule_date="2025-10-14",
            )

    def test_failed_create_cannot_be_blindly_retried(self):
        agent = Agent(FakeERP(fail_create=True))
        proposal = agent.proposal_po("Tongling Magnet Wire Co.", "RM-COIL-CU-2.0", 1, "Meter", 29)
        with self.assertRaises(ERPError):
            agent.confirm(proposal["proposal_id"])
        with self.assertRaises(ERPError):
            agent.confirm(proposal["proposal_id"])

    def test_mutating_preview_does_not_mutate_write_snapshot(self):
        erp = FakeERP()
        agent = Agent(erp)
        proposal = agent.proposal_po("Tongling Magnet Wire Co.", "RM-COIL-CU-2.0", 1, "Meter", 29)
        proposal["doc"]["items"][0]["rate"] = 1
        agent.confirm(proposal["proposal_id"])
        self.assertEqual(erp.created[0][1]["items"][0]["rate"], 29.0)


if __name__ == "__main__":
    unittest.main()
