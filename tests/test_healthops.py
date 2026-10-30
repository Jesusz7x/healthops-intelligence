"""In-process API integration tests for route logic."""
import io, json, os, sys, tempfile, unittest
from pathlib import Path
from email.message import Message
from http.server import BaseHTTPRequestHandler

_temp=tempfile.TemporaryDirectory(prefix='healthops-test-')
os.environ['HEALTHOPS_DB']=str(Path(_temp.name)/'healthops.sqlite3')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'api'))
import store, server

class HealthOpsApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): store.initialize()
    def setUp(self): self.cookie=''
    def req(self,path,method='GET',data=None,raw=None):
        body=(raw.encode() if raw is not None else json.dumps(data).encode() if data is not None else b'')
        h=object.__new__(server.Handler)
        h.command=method; h.path=path; h.request_version='HTTP/1.1'; h.requestline=f'{method} {path} HTTP/1.1'; h.client_address=('127.0.0.1',12345)
        h.headers=Message(); h.headers['Content-Length']=str(len(body))
        h.headers['Content-Type']='text/csv' if raw is not None else 'application/json'
        if self.cookie: h.headers['Cookie']=self.cookie
        h.rfile=io.BytesIO(body); h.wfile=io.BytesIO()
        h.dispatch_request()
        output=h.wfile.getvalue(); head,payload=output.split(b'\r\n\r\n',1)
        lines=head.decode().split('\r\n'); status=int(lines[0].split()[1]); headers=Message()
        for line in lines[1:]:
            if ':' in line:
                k,v=line.split(':',1); headers[k.strip()]=v.strip()
        if headers.get('Set-Cookie','').startswith(server.COOKIE+'='):
            cookie=headers['Set-Cookie'].split(';',1)[0]
            if cookie.endswith('='): self.cookie=''
            else: self.cookie=cookie
        content=json.loads(payload) if 'application/json' in headers.get('Content-Type','') else payload.decode(errors='replace')
        return status,content,headers
    def login(self,email='admin@healthops.local',password='DemoHealthOps!2026'):
        return self.req('/api/auth/login','POST',{'email':email,'password':password})
    def test_handler_keeps_the_standard_base_http_lifecycle(self):
        self.assertIs(server.Handler.handle,BaseHTTPRequestHandler.handle)

    def test_health_and_static_frontend_are_public(self):
        self.assertEqual(self.req('/api/health')[1]['status'],'ok')
        self.assertEqual(self.req('/health')[1]['synthetic_data_only'],True)
        code,body,_=self.req('/')
        self.assertEqual(code,200); self.assertIn('HealthOps Intelligence',body); self.assertIn('visitor@healthops.local',body); self.assertIn('not certified clinical software',body.lower())
        css_code,css,_=self.req('/styles.css')
        js_code,js,_=self.req('/app.js')
        self.assertEqual(css_code,200); self.assertIn(':root',css)
        self.assertEqual(js_code,200); self.assertIn('function',js)
    def test_password_hash_and_login_cookie(self):
        code,data,headers=self.login(); self.assertEqual(code,200); self.assertEqual(data['user']['role'],'admin')
        self.assertIn('HttpOnly',headers['Set-Cookie']); self.assertIn('SameSite=Strict',headers['Set-Cookie'])
        self.assertTrue(store.verify_password('DemoHealthOps!2026',store.password_hash('DemoHealthOps!2026')))
        self.assertFalse(store.verify_password('wrong',store.password_hash('DemoHealthOps!2026')))
    def test_unauthenticated_routes_are_rejected(self): self.assertEqual(self.req('/api/patients')[0],401)
    def test_patient_create_edit_and_validation(self):
        self.login(); code,data,_=self.req('/api/patients','POST',{'code':'T-PAT-1','full_name':'Fictional Person','email':'person@example.invalid','age':32})
        self.assertEqual(code,201); pid=data['item']['id']
        self.assertEqual(self.req(f'/api/patients/{pid}','PATCH',{'age':33})[1]['item']['age'],33)
        self.assertEqual(self.req('/api/patients','POST',{'code':'BAD-AGE','full_name':'Demo','email':'x@example.invalid','age':999})[0],400)
        self.assertEqual(self.req('/api/patients','POST',{'code':'BAD-EMAIL','full_name':'Demo','email':'person@example.com','age':20})[0],400)
        self.assertEqual(self.req('/api/patients','POST',{'code':'BAD-EMAIL-SHAPE','full_name':'Demo','email':'person@.invalid','age':20})[0],400)
    def test_readonly_role_cannot_write(self):
        self.login('viewer@healthops.local'); code,_,_=self.req('/api/patients','POST',{'code':'NOPE','full_name':'Not allowed','email':'no@example.invalid','age':20})
        self.assertEqual(code,403)
    def test_appointments_validate_references_and_datetime(self):
        self.login()
        with store.connect() as db: ids=db.execute('SELECT (SELECT id FROM patients LIMIT 1),(SELECT id FROM staff LIMIT 1)').fetchone()
        code,_,_=self.req('/api/appointments','POST',{'patient_id':ids[0],'staff_id':ids[1],'starts_at':'2026-11-01T09:30:00Z','department':'Primary Care'})
        self.assertEqual(code,201)
        appt_id=self.req('/api/appointments')[1]['items'][0]['id']
        self.assertEqual(self.req('/api/appointments','POST',{'patient_id':ids[0],'staff_id':ids[1],'starts_at':'2026-11-01T09:30:00Z','department':'Primary Care'})[0],409)
        self.assertEqual(self.req(f'/api/appointments/{appt_id}','PATCH',{'status':'completed'})[1]['status'],'completed')
        self.assertEqual(self.req(f'/api/appointments/{appt_id}','PATCH',{'status':'cancelled'})[0],409)
        self.assertEqual(self.req('/api/appointments','POST',{'patient_id':99999,'staff_id':ids[1],'starts_at':'bad','department':'Care'})[0],400)
        self.assertEqual(self.req('/api/appointments','POST',{'patient_id':ids[0],'staff_id':ids[1],'starts_at':'2026-11-01T09:30:00','department':'Care'})[0],400)
    def test_inventory_movement_cannot_overdraw(self):
        self.login('stock@healthops.local')
        with store.connect() as db: iid=db.execute('SELECT id,quantity FROM inventory LIMIT 1').fetchone()
        before=iid[1]; code,_,_=self.req(f'/api/inventory/{iid[0]}/movements','POST',{'delta':-(before+1),'reason':'invalid demo adjustment'})
        self.assertEqual(code,409)
        code,data,_=self.req(f'/api/inventory/{iid[0]}/movements','POST',{'delta':3,'reason':'fictional receipt'})
        self.assertEqual(code,200); self.assertEqual(data['quantity'],before+3)
    def test_import_export_csv_and_error_rollback(self):
        self.login()
        csv='code,full_name,email,age\nCSV-TEST-1,"=SUM(1,1)",formula@example.invalid,30\n'
        code,data,_=self.req('/api/import/patients','POST',raw=csv); self.assertEqual(code,201); self.assertEqual(data['imported'],1)
        code,body,_=self.req('/api/export/patients.csv'); self.assertEqual(code,200); self.assertIn("'=SUM",body)
        with store.connect() as db: count=db.execute('SELECT COUNT(*) FROM patients').fetchone()[0]
        code,_,_=self.req('/api/import/patients','POST',raw='code,full_name,email,age\nBROKEN,Invalid,real@example.com,21\n')
        self.assertEqual(code,400)
        with store.connect() as db: self.assertEqual(db.execute('SELECT COUNT(*) FROM patients').fetchone()[0],count)
    def test_analytics_settings_staff_audit(self):
        self.login(); report=self.req('/api/reports')[1]
        self.assertEqual(len(report['demand_baseline_7d']),7); self.assertIn('limitations',report); self.assertGreaterEqual(len(report['anomalies']),1)
        self.assertEqual(self.req('/api/settings','PATCH',{'facility_name':'Fictional Test Center','low_stock_threshold':0.8})[0],200)
        report=self.req('/api/reports')[1]
        self.assertEqual(report['critical_stock_ratio'],0.8)
        self.assertIn('MED-002',{item['sku'] for item in report['critical_stock']})
        self.assertEqual(self.req('/api/staff','POST',{'code':'T-ST-1','full_name':'Sample Staff','role':'Nurse','department':'Test'})[0],201)
        self.assertTrue(self.req('/api/audit')[1]['items'])
        users=self.req('/api/users')[1]['items']; viewer=next(u for u in users if u['role']=='viewer')
        self.assertEqual(self.req(f"/api/users/{viewer['id']}",'PATCH',{'role':'inventory'})[0],200)
        admin=next(u for u in users if u['role']=='admin')
        self.assertEqual(self.req(f"/api/users/{admin['id']}",'PATCH',{'role':'viewer'})[0],409)
    def test_viewer_cannot_read_audit(self):
        self.login('viewer@healthops.local'); self.assertEqual(self.req('/api/audit')[0],403)

    def test_quality_report_flags_synthetic_duplicate_names(self):
        self.login()
        code,_,_=self.req('/api/patients','POST',{'code':'DUP-NAME-1','full_name':'Repeated Demo Name','email':'one@example.invalid','age':25})
        self.assertEqual(code,201)
        code,_,_=self.req('/api/patients','POST',{'code':'DUP-NAME-2','full_name':' repeated   demo name ','email':'two@example.invalid','age':28})
        self.assertEqual(code,201)
        report=self.req('/api/data-quality')[1]
        self.assertIn('possible_duplicate_name',{i['kind'] for i in report['issues']})
    def test_public_read_only_mode_downgrades_demo_admin(self):
        original=server.READ_ONLY_MODE; original_secure=server.SECURE_COOKIES
        try:
            server.READ_ONLY_MODE=True
            server.SECURE_COOKIES=True
            code,data,headers=self.login(store.PUBLIC_VISITOR_EMAIL,store.PUBLIC_VISITOR_PASSWORD)
            self.assertEqual(code,200); self.assertEqual(data['user']['role'],'viewer')
            self.assertTrue(data['read_only_mode'])
            self.assertIn('Secure',headers['Set-Cookie'])
            self.assertEqual(self.req('/api/audit')[0],200)
            self.assertEqual(self.login('admin@healthops.local','DemoHealthOps!2026')[0],401)
            self.assertEqual(self.req('/api/patients','POST',{'code':'PUBLIC-NO','full_name':'Read Only','email':'ro@example.invalid','age':20})[0],403)
        finally: server.READ_ONLY_MODE=original; server.SECURE_COOKIES=original_secure

    def test_read_only_database_seeds_visitor_without_administrator_accounts(self):
        with tempfile.TemporaryDirectory(prefix='healthops-public-seed-') as temp:
            path=Path(temp)/'public.sqlite3'
            store.initialize(path,public_read_only=True)
            with store.connect(path) as db:
                users=[dict(row) for row in db.execute('SELECT email,role FROM users')]
                self.assertEqual(users,[{'email':store.PUBLIC_VISITOR_EMAIL,'role':'viewer'}])
                self.assertEqual(db.execute('SELECT COUNT(*) FROM patients').fetchone()[0],5)
    def test_missing_json_content_type_is_rejected(self):
        h=object.__new__(server.Handler); h.command='POST'; h.path='/api/auth/logout'; h.request_version='HTTP/1.1'; h.requestline='POST /api/auth/logout HTTP/1.1'; h.client_address=('127.0.0.1',1); h.headers=Message(); h.headers['Content-Length']='2'; h.rfile=io.BytesIO(b'{}'); h.wfile=io.BytesIO(); h.dispatch_request()
        head,payload=h.wfile.getvalue().split(b'\r\n\r\n',1)
        self.assertIn(b' 415 ',head); self.assertIn(b'Content-Type must be application/json',payload)

    def test_disconnected_client_does_not_trigger_a_second_error_response(self):
        class BrokenWriter:
            attempts=0
            def write(self, data):
                self.attempts+=1
                raise BrokenPipeError('synthetic disconnected client')
        h=object.__new__(server.Handler); h.command='GET'; h.path='/api/health'; h.request_version='HTTP/1.1'; h.requestline='GET /api/health HTTP/1.1'; h.wfile=BrokenWriter(); h.close_connection=False
        h.send_json(200,{'status':'ok'})
        self.assertTrue(h.close_connection)
        self.assertTrue(h._response_started)
        h._send_error(500,{'error':{'message':'safe'}})
        self.assertEqual(h.wfile.attempts,1)

if __name__=='__main__': unittest.main(verbosity=2)
