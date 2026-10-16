import unittest
from agent import overdue
class TestRules(unittest.TestCase):
 def test_pinned_date(self):
  xs=[{'name':'a','due_date':'2025-10-14','outstanding_amount':1},{'name':'b','due_date':'2025-10-15','outstanding_amount':1},{'name':'c','due_date':'2025-09-01','outstanding_amount':0}]
  self.assertEqual([x['name'] for x in overdue(xs)],['a'])
if __name__=='__main__':unittest.main()
