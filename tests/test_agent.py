import unittest

from agent import Agent, ERPError


class FakeERP:
    def __init__(self, fail_create=False):
        self.created = []
        self.fail_create = fail_create

    def list(self, doctype, fields=None, filters=None, limit=20, offset=0, order_by=None):
        if doctype == "Item":
            return [{"name": "RM-COIL-CU-2.0", "item_code": "RM-COIL-CU-2.0", "stock_uom": "Meter", "disabled": 0}]
        if doctype == "Supplier":
            return [{"name": "Tongling Magnet Wire Co."}]
        return []

    def create(self, doctype, doc):
        if self.fail_create:
            raise TimeoutError("simulated timeout")
        self.created.append(doc)
        return {"name": "PUR-ORD-TEST-00001", "status": "Draft"}

    def get(self, doctype, name):
        return {"name": name, "status": "Draft", "items": self.created[-1]["items"]}


class TestPurchaseOrderFlow(unittest.TestCase):
    def test_preview_does_not_write_until_confirm(self):
        fake = FakeERP()
        agent = Agent(fake)
        preview = agent.proposal_po("Tongling Magnet Wire Co.", "RM-COIL-CU-2.0", 100, "Meter", 29)
        self.assertEqual(preview["estimated_total"], "2900")
        self.assertEqual(fake.created, [])
        result = agent.confirm(preview["proposal_id"])
        self.assertEqual(result["name"], "PUR-ORD-TEST-00001")
        self.assertEqual(len(fake.created), 1)

    def test_uom_and_date_are_validated(self):
        agent = Agent(FakeERP())
        with self.assertRaises(ValueError):
            agent.proposal_po("Tongling Magnet Wire Co.", "RM-COIL-CU-2.0", 100, "Nos", 29)
        with self.assertRaises(ValueError):
            agent.proposal_po("Tongling Magnet Wire Co.", "RM-COIL-CU-2.0", 100, "Meter", 29, schedule_date="2025-10-14")

    def test_failed_create_cannot_be_blindly_retried(self):
        agent = Agent(FakeERP(fail_create=True))
        preview = agent.proposal_po("Tongling Magnet Wire Co.", "RM-COIL-CU-2.0", 100, "Meter", 29)
        with self.assertRaises(ERPError):
            agent.confirm(preview["proposal_id"])
        with self.assertRaises(ERPError):
            agent.confirm(preview["proposal_id"])


if __name__ == "__main__":
    unittest.main()
