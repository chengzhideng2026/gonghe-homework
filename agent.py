import os,sys,json,uuid
from datetime import date
from decimal import Decimal
import requests
try:
 from dotenv import load_dotenv; load_dotenv()
except ImportError: pass
REFERENCE_DATE=os.getenv('REFERENCE_DATE','2025-10-15')
class ERPError(Exception): pass
class ERPNextClient:
 def __init__(self,base=None,key=None,secret=None):
  self.base=(base or os.getenv('ERPNEXT_URL','http://localhost:8080')).rstrip('/')
  self.s=requests.Session(); self.s.headers.update({'Authorization':f"token {key or os.getenv('ERPNEXT_API_KEY','crestwind-agent')}:{secret or os.getenv('ERPNEXT_API_SECRET','crestwind-agent-secret')}"})
 def _req(self,method,path,**kw):
  try:r=self.s.request(method,self.base+path,timeout=20,**kw)
  except requests.RequestException as e: raise ERPError(f'ERPNext request failed: {e}')
  if r.status_code>=400: raise ERPError(f'ERPNext {r.status_code}: {r.text[:500]}')
  try:return r.json().get('data',r.json().get('message',r.json()))
  except Exception:return r.text
 def count(self,doctype): return self._req('GET',f'/api/method/frappe.client.get_count',params={'doctype':doctype})
 def meta(self,doctype): return self._req('GET','/api/method/frappe.desk.form.load.getdoctype',params={'doctype':doctype,'with_parent':'1'})
 def list(self,doctype,fields=None,filters=None,limit=20,offset=0,order_by=None):
  p={'limit_page_length':min(limit,100),'limit_start':offset}
  if fields:p['fields']=json.dumps(fields)
  if filters:p['filters']=json.dumps(filters)
  if order_by:p['order_by']=order_by
  return self._req('GET',f'/api/resource/{doctype}',params=p)
 def get(self,doctype,name): return self._req('GET',f'/api/resource/{doctype}/{name}')
 def create(self,doctype,doc): return self._req('POST',f'/api/resource/{doctype}',json=doc)

def overdue(invoices,ref=REFERENCE_DATE):
 return [x for x in invoices if x.get('due_date') and x.get('due_date')<ref and float(x.get('outstanding_amount',0) or 0)>0]
class Agent:
 def __init__(self,client): self.c=client; self.proposals={}
 def proposal_po(self,supplier,item,qty,uom,rate,transaction_date=REFERENCE_DATE,schedule_date=REFERENCE_DATE):
  if not all([supplier,item,qty,uom,rate]): raise ValueError('supplier, item, qty, uom and rate are required')
  if float(qty)<=0 or float(rate)<0: raise ValueError('qty must be positive and rate non-negative')
  # live validation
  items=self.c.list('Item',['name','item_code','stock_uom'],[['name','=',item]],limit=1)
  if not items: raise ERPError(f'Item not found: {item}')
  sups=self.c.list('Supplier',['name'],[['name','=',supplier]],limit=1)
  if not sups: raise ERPError(f'Supplier not found: {supplier}')
  total=Decimal(str(qty))*Decimal(str(rate)); pid=uuid.uuid4().hex[:8]
  doc={'doctype':'Purchase Order','supplier':supplier,'transaction_date':transaction_date,'schedule_date':schedule_date,'items':[{'item_code':item,'qty':qty,'uom':uom,'rate':rate}]}
  self.proposals[pid]={'doc':doc,'total':str(total)}
  return pid,doc,total
 def confirm(self,pid):
  if pid not in self.proposals: raise ValueError('Unknown or expired proposal id')
  p=self.proposals.pop(pid); created=self.c.create('Purchase Order',p['doc']); name=created.get('name') if isinstance(created,dict) else created
  return {'name':name,'status':created.get('status') if isinstance(created,dict) else None,'verified':self.c.get('Purchase Order',name)}

def main():
 import argparse
 ap=argparse.ArgumentParser(); ap.add_argument('--demo',action='store_true'); args=ap.parse_args(); c=ERPNextClient(); a=Agent(c)
 if args.demo: print('Demo mode: generic tools ready; configure ERPNext and LLM for live chat.'); return
 print('Plantcore ERP Agent. /confirm <id> executes a displayed proposal; /quit exits.')
 while True:
  try:q=input('you> ').strip()
  except EOFError:break
  if q in ('/quit','/exit'):break
  if q.startswith('/confirm '):
   try: print(json.dumps(a.confirm(q.split()[1]),ensure_ascii=False,indent=2))
   except Exception as e: print(f'ERROR: {e}')
   continue
  print('LLM orchestration is configured through the OpenAI-compatible endpoint; use tools meta/list/get/create. Query:',q)
if __name__=='__main__': main()
