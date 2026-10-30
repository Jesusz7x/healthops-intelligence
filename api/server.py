"""Small, local-first HTTP API. Uses only Python's standard library and SQLite."""
from __future__ import annotations
import csv, io, json, re, secrets, hashlib, os, mimetypes, time, sqlite3
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timezone, timedelta
from pathlib import Path
from store import connect, initialize, now, verify_password, record_audit, ROLES, PUBLIC_VISITOR_EMAIL, PUBLIC_VISITOR_PASSWORD
from analytics import dashboard, reports
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'processing'))
from quality import inspect_rows

MAX_BODY=1_000_000
COOKIE='healthops_session'
LOGIN_ATTEMPTS={}
LOGIN_WINDOW=300
READ_ONLY_MODE=os.environ.get('HEALTHOPS_READ_ONLY')=='1'
SECURE_COOKIES=os.environ.get('HEALTHOPS_SECURE_COOKIES')=='1'
MUTATING_ROLES={'patients':{'admin','operations','clinical'},'appointments':{'admin','operations','clinical'},'staff':{'admin'},'inventory':{'admin','inventory'},'import':{'admin','operations'},'settings':{'admin'}}
def fail(status,message): raise ApiError(status,message)
class ApiError(Exception):
    def __init__(self,status,message): self.status=status; self.message=message

def clean_text(value, field, limit=160, required=True):
    if not isinstance(value,str): fail(400,f'{field} must be text')
    value=value.strip()
    if required and not value: fail(400,f'{field} is required')
    if len(value)>limit: fail(400,f'{field} exceeds {limit} characters')
    if any(ord(c)<32 and c not in '\t' for c in value): fail(400,f'{field} contains control characters')
    return value

def normalize_datetime(value):
    try:
        parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
        if parsed.tzinfo is None: return None
        return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat()
    except (ValueError,AttributeError): return None

class Handler(BaseHTTPRequestHandler):
    server_version='HealthOpsDemo/0.1'
    def send_response(self, code, message=None):
        # Track the first response attempt so the error handler never writes a
        # second HTTP status line after headers/body have begun.
        self._response_started=True
        return super().send_response(code,message)
    def log_message(self, fmt, *args):
        # Keep logs free of request payloads, names, emails, and session cookies.
        print(f'{self.log_date_time_string()} {self.command} {self.path.split("?")[0]} {args[1] if len(args)>1 else ""}')
    def send_json(self, code, payload, headers=None):
        body=json.dumps(payload,ensure_ascii=False).encode()
        try:
            self.send_response(code); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Content-Length',str(len(body))); self.send_header('X-Content-Type-Options','nosniff'); self.send_header('Cache-Control','no-store'); self.send_header('Content-Security-Policy',"default-src 'self'; connect-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; base-uri 'none'; frame-ancestors 'none'")
            for k,v in (headers or {}).items(): self.send_header(k,v)
            self.end_headers(); self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError, OSError):
            # A disconnected client must not trigger a second response attempt.
            self.close_connection=True
    def send_csv(self, name, text):
        data=text.encode('utf-8-sig'); self.send_response(200); self.send_header('Content-Type','text/csv; charset=utf-8'); self.send_header('Content-Disposition',f'attachment; filename="{name}"'); self.send_header('Content-Length',str(len(data))); self.send_header('X-Content-Type-Options','nosniff'); self.end_headers(); self.wfile.write(data)
    def body(self, raw=False):
        n=int(self.headers.get('Content-Length','0'))
        if n>MAX_BODY: fail(413,'Request body exceeds 1 MB')
        data=self.rfile.read(n)
        if raw: return data.decode('utf-8-sig')
        try: return json.loads(data or b'{}')
        except (json.JSONDecodeError,UnicodeDecodeError): fail(400,'Body must be valid UTF-8 JSON')
    @contextmanager
    def db(self):
        conn=connect()
        try:
            with conn: yield conn
        finally: conn.close()
    def session(self, required=True):
        cookie=self.headers.get('Cookie','')
        token=''
        for part in cookie.split(';'):
            k,sep,v=part.strip().partition('=')
            if k==COOKIE and sep: token=v
        if not token:
            if required: fail(401,'Sign in to continue')
            return None
        digest=hashlib.sha256(token.encode()).hexdigest()
        with self.db() as db:
            row=db.execute('SELECT u.id,u.email,u.display_name,u.role,u.active,s.expires_at FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=?',(digest,)).fetchone()
        if not row or not row['active'] or row['expires_at']<=now():
            if required: fail(401,'Session expired; sign in again')
            return None
        user=dict(row)
        if READ_ONLY_MODE: user['role']='viewer'
        return user
    def role(self, category):
        user=self.session();
        if user['role'] not in MUTATING_ROLES[category]: fail(403,'Your role cannot perform this action')
        return user
    def _dispatch_http_request(self):
        self._response_started=False
        self.dispatch_request()
    def do_GET(self): self._dispatch_http_request()
    def do_POST(self): self._dispatch_http_request()
    def do_PUT(self): self._dispatch_http_request()
    def do_PATCH(self): self._dispatch_http_request()
    def do_DELETE(self): self._dispatch_http_request()
    def dispatch_request(self):
        try:
            path=urlparse(self.path).path
            if self.command in ('POST','PUT','PATCH','DELETE'):
                content_type=self.headers.get('Content-Type','').split(';',1)[0].strip().lower()
                expected='text/csv' if path=='/api/import/patients' else 'application/json'
                if content_type!=expected: fail(415,f'Content-Type must be {expected}')
                origin=self.headers.get('Origin')
                forwarded=self.headers.get('X-Forwarded-Proto','').split(',')[0].strip()
                scheme=forwarded or 'http'
                host=self.headers.get('Host','')
                expected_origin=f'{scheme}://{host}' if host else ''
                if origin and origin!=expected_origin: fail(403,'Cross-origin request rejected')
            if path in ('/health','/api/health') and self.command=='GET': return self.send_json(200,{'status':'ok','product':'HealthOps Intelligence','synthetic_data_only':True})
            if self.command=='GET' and not path.startswith('/api/'):
                return self.static_file(path)
            if path=='/api/auth/login' and self.command=='POST': return self.login()
            if path=='/api/auth/logout' and self.command=='POST': return self.logout()
            if path=='/api/auth/me' and self.command=='GET':
                user=self.session(False); return self.send_json(200,{'user':user,'read_only_mode':READ_ONLY_MODE})
            user=self.session()
            if path=='/api/dashboard' and self.command=='GET':
                with self.db() as db: return self.send_json(200,dashboard(db))
            if path=='/api/reports' and self.command=='GET':
                with self.db() as db: return self.send_json(200,reports(db))
            if path=='/api/data-quality' and self.command=='GET':
                with self.db() as db:
                    rows=[dict(r) for r in db.execute('SELECT code,full_name,email,age FROM patients ORDER BY id')]
                    return self.send_json(200,inspect_rows(rows))
            if path=='/api/patients' and self.command=='GET': return self.patients()
            if path=='/api/patients' and self.command=='POST': return self.create_patient()
            m=re.fullmatch(r'/api/patients/(\d+)',path)
            if m and self.command=='PATCH': return self.update_patient(int(m.group(1)))
            m=re.fullmatch(r'/api/appointments/(\d+)',path)
            if m and self.command=='PATCH': return self.update_appointment(int(m.group(1)))
            if path=='/api/appointments' and self.command=='GET': return self.appointments()
            if path=='/api/appointments' and self.command=='POST': return self.create_appointment()
            if path=='/api/staff' and self.command=='GET':
                with self.db() as db: return self.send_json(200,{'items':[dict(r) for r in db.execute('SELECT id,code,full_name,role,department,active,created_at FROM staff ORDER BY id')]})
            if path=='/api/staff' and self.command=='POST': return self.create_staff()
            if path=='/api/users' and self.command=='GET':
                if user['role']!='admin': fail(403,'Administrator role required')
                with self.db() as db: return self.send_json(200,{'items':[dict(r) for r in db.execute('SELECT id,email,display_name,role,active,created_at FROM users ORDER BY id')]})
            m=re.fullmatch(r'/api/users/(\d+)',path)
            if m and self.command=='PATCH': return self.update_user(int(m.group(1)))
            if path=='/api/inventory' and self.command=='GET':
                with self.db() as db: return self.send_json(200,{'items':[dict(r) for r in db.execute('SELECT * FROM inventory ORDER BY name')]})
            if path=='/api/inventory' and self.command=='POST': return self.create_inventory()
            m=re.fullmatch(r'/api/inventory/(\d+)/movements',path)
            if m and self.command=='GET':
                with self.db() as db:
                    return self.send_json(200,{'items':[dict(r) for r in db.execute('SELECT m.id,m.delta,m.reason,m.created_at,u.display_name actor FROM stock_movements m LEFT JOIN users u ON u.id=m.actor_id WHERE m.inventory_id=? ORDER BY m.id DESC LIMIT 100',(int(m.group(1)),))]})
            if m and self.command=='POST': return self.stock_movement(int(m.group(1)))
            if path=='/api/audit' and self.command=='GET':
                if user['role']!='admin' and not (READ_ONLY_MODE and user['role']=='viewer'): fail(403,'Administrator role required')
                with self.db() as db: return self.send_json(200,{'items':[dict(r) for r in db.execute('SELECT a.id,u.display_name actor,a.action,a.entity,a.entity_id,a.detail,a.created_at FROM audit a LEFT JOIN users u ON u.id=a.actor_id ORDER BY a.id DESC LIMIT 200')]})
            if path=='/api/settings' and self.command=='GET':
                with self.db() as db: return self.send_json(200,{'settings':{r['key']:r['value'] for r in db.execute('SELECT key,value FROM settings')}})
            if path=='/api/settings' and self.command=='PATCH': return self.update_settings()
            if path=='/api/import/patients' and self.command=='POST': return self.import_patients()
            if path=='/api/export/patients.csv' and self.command=='GET': return self.export_patients()
            fail(404,'Endpoint not found')
        except ApiError as e: self._send_error(e.status,{'error':{'message':e.message}})
        except sqlite3.IntegrityError as e:
            self._send_error(409,{'error':{'message':'The record conflicts with existing data or a constraint'}})
        except Exception:
            self._send_error(500,{'error':{'message':'Unexpected server error; request was not logged with personal data'}})
    def _send_error(self, code, payload):
        if getattr(self,'_response_started',False):
            self.close_connection=True
            return
        self.send_json(code,payload)
    def static_file(self, path):
        root=(Path(__file__).resolve().parents[1]/'web').resolve()
        rel='index.html' if path=='/' else path.lstrip('/')
        target=(root/rel).resolve()
        if root not in target.parents and target!=root: fail(404,'Not found')
        if not target.is_file(): fail(404,'Not found')
        data=target.read_bytes(); kind=mimetypes.guess_type(str(target))[0] or 'application/octet-stream'
        self.send_response(200); self.send_header('Content-Type',kind); self.send_header('Content-Length',str(len(data))); self.send_header('X-Content-Type-Options','nosniff'); self.send_header('Content-Security-Policy',"default-src 'self'; connect-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; base-uri 'none'; frame-ancestors 'none'"); self.end_headers(); self.wfile.write(data)
    def login(self):
        data=self.body()
        if not isinstance(data,dict): fail(400,'JSON object required')
        email=str(data.get('email','')).strip().lower(); password=data.get('password','')
        if len(email)>254 or not isinstance(password,str) or len(password)>256: fail(400,'Invalid credentials format')
        if READ_ONLY_MODE and email!=PUBLIC_VISITOR_EMAIL: fail(401,'Email or password not recognized')
        peer=self.client_address[0]
        attempts=[stamp for stamp in LOGIN_ATTEMPTS.get(peer,[]) if time.monotonic()-stamp<LOGIN_WINDOW]
        if len(attempts)>=10: fail(429,'Too many sign-in attempts; wait five minutes')
        with self.db() as db:
            row=db.execute('SELECT * FROM users WHERE email=? AND active=1',(email,)).fetchone()
            expected_public_password=not READ_ONLY_MODE or password==PUBLIC_VISITOR_PASSWORD
            if not row or not expected_public_password or not verify_password(password,row['password_hash']):
                LOGIN_ATTEMPTS[peer]=attempts+[time.monotonic()]
                fail(401,'Email or password not recognized')
            LOGIN_ATTEMPTS.pop(peer,None)
            token=secrets.token_urlsafe(32); expires=(datetime.now(timezone.utc)+timedelta(hours=8)).replace(microsecond=0).isoformat()
            db.execute('INSERT INTO sessions(token_hash,user_id,expires_at,created_at) VALUES(?,?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),row['id'],expires,now()))
            record_audit(db,row['id'],'login','session')
            safe={k:row[k] for k in ('id','email','display_name','role')}
        if READ_ONLY_MODE: safe['role']='viewer'
        secure='; Secure' if SECURE_COOKIES else ''
        return self.send_json(200,{'user':safe,'read_only_mode':READ_ONLY_MODE},{'Set-Cookie':f'{COOKIE}={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=28800{secure}'})
    def logout(self):
        user=self.session(False)
        if user:
            token=next((p.strip().split('=',1)[1] for p in self.headers.get('Cookie','').split(';') if p.strip().startswith(COOKIE+'=')),'')
            with self.db() as db:
                db.execute('DELETE FROM sessions WHERE token_hash=?',(hashlib.sha256(token.encode()).hexdigest(),)); record_audit(db,user['id'],'logout','session')
        return self.send_json(200,{'ok':True},{'Set-Cookie':f'{COOKIE}=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0'})
    def patients(self):
        q=parse_qs(urlparse(self.path).query); term=q.get('q',[''])[0][:100]; status=q.get('status',[''])[0]
        sql='SELECT * FROM patients WHERE (full_name LIKE ? OR code LIKE ? OR email LIKE ?)'; args=[f'%{term}%']*3
        if status in ('active','inactive'): sql+=' AND status=?'; args.append(status)
        sql+=' ORDER BY id DESC LIMIT 500'
        with self.db() as db: return self.send_json(200,{'items':[dict(r) for r in db.execute(sql,args)]})
    def create_patient(self):
        user=self.role('patients'); d=self.body()
        if not isinstance(d,dict): fail(400,'JSON object required')
        code=clean_text(d.get('code'),'code',32); name=clean_text(d.get('full_name'),'full_name',120)
        email=clean_text(d.get('email',''),'email',254,False); age=d.get('age')
        if isinstance(age,bool) or not isinstance(age,int) or not 0<=age<=120: fail(400,'age must be an integer from 0 to 120')
        if email and not re.fullmatch(r'[^@\s]+@(?:[A-Za-z0-9-]+\.)+invalid',email,re.I): fail(400,'Use a valid-looking address at the reserved .invalid domain')
        status=d.get('status','active')
        if status not in ('active','inactive'): fail(400,'status must be active or inactive')
        with self.db() as db:
            cur=db.execute('INSERT INTO patients(code,full_name,email,age,status,created_at) VALUES(?,?,?,?,?,?)',(code,name,email,age,status,now())); record_audit(db,user['id'],'create','patient',cur.lastrowid)
            row=dict(db.execute('SELECT * FROM patients WHERE id=?',(cur.lastrowid,)).fetchone())
        return self.send_json(201,{'item':row})
    def update_patient(self,pid):
        user=self.role('patients'); d=self.body()
        if not isinstance(d,dict) or not d: fail(400,'At least one field is required')
        allowed={'full_name','email','age','status'}; updates={k:v for k,v in d.items() if k in allowed}
        if len(updates)!=len(d): fail(400,'Unsupported patient field')
        if 'full_name' in updates: updates['full_name']=clean_text(updates['full_name'],'full_name',120)
        if 'email' in updates:
            updates['email']=clean_text(updates['email'],'email',254,False)
            if updates['email'] and not re.fullmatch(r'[^@\s]+@(?:[A-Za-z0-9-]+\.)+invalid',updates['email'],re.I): fail(400,'Use a valid-looking address at the reserved .invalid domain')
        if 'age' in updates and (isinstance(updates['age'],bool) or not isinstance(updates['age'],int) or not 0<=updates['age']<=120): fail(400,'Invalid age')
        if 'status' in updates and updates['status'] not in ('active','inactive'): fail(400,'Invalid status')
        with self.db() as db:
            if not db.execute('SELECT 1 FROM patients WHERE id=?',(pid,)).fetchone(): fail(404,'Patient not found')
            db.execute('UPDATE patients SET '+','.join(f'{k}=?' for k in updates)+' WHERE id=?',(*updates.values(),pid)); record_audit(db,user['id'],'update','patient',pid)
            return self.send_json(200,{'item':dict(db.execute('SELECT * FROM patients WHERE id=?',(pid,)).fetchone())})
    def appointments(self):
        q=parse_qs(urlparse(self.path).query); status=q.get('status',[''])[0]
        sql='SELECT a.*,p.code patient_code,p.full_name patient_name,s.full_name staff_name FROM appointments a LEFT JOIN patients p ON p.id=a.patient_id LEFT JOIN staff s ON s.id=a.staff_id'; args=[]
        if status in ('scheduled','completed','cancelled','no_show'): sql+=' WHERE a.status=?'; args.append(status)
        sql+=' ORDER BY starts_at DESC LIMIT 500'
        with self.db() as db: return self.send_json(200,{'items':[dict(r) for r in db.execute(sql,args)]})
    def create_appointment(self):
        user=self.role('appointments'); d=self.body()
        if not isinstance(d,dict): fail(400,'JSON object required')
        pid=d.get('patient_id'); sid=d.get('staff_id'); start=d.get('starts_at')
        if not isinstance(pid,int) or not isinstance(sid,int): fail(400,'patient_id and staff_id must be integers')
        if not isinstance(start,str) or not normalize_datetime(start): fail(400,'starts_at must be an ISO-8601 datetime with a timezone')
        start=normalize_datetime(start)
        dept=clean_text(d.get('department'),'department',80)
        with self.db() as db:
            if not db.execute("SELECT 1 FROM patients WHERE id=? AND status='active'",(pid,)).fetchone(): fail(400,'An active patient is required')
            if not db.execute('SELECT 1 FROM staff WHERE id=? AND active=1',(sid,)).fetchone(): fail(400,'An active staff member is required')
            if db.execute("SELECT 1 FROM appointments WHERE staff_id=? AND starts_at=? AND status='scheduled'",(sid,start)).fetchone(): fail(409,'Staff member already has a scheduled appointment at that time')
            cur=db.execute('INSERT INTO appointments(patient_id,staff_id,starts_at,department,status,created_at) VALUES(?,?,?,?,?,?)',(pid,sid,start,dept,'scheduled',now())); record_audit(db,user['id'],'create','appointment',cur.lastrowid)
            return self.send_json(201,{'id':cur.lastrowid,'status':'scheduled'})
    def update_appointment(self,aid):
        user=self.role('appointments'); d=self.body(); status=d.get('status') if isinstance(d,dict) else None
        if status not in ('completed','cancelled','no_show'): fail(400,'status must be completed, cancelled, or no_show')
        with self.db() as db:
            existing=db.execute('SELECT status FROM appointments WHERE id=?',(aid,)).fetchone()
            if not existing: fail(404,'Appointment not found')
            if existing['status']!='scheduled': fail(409,'Only scheduled appointments can change status')
            db.execute('UPDATE appointments SET status=? WHERE id=?',(status,aid)); record_audit(db,user['id'],'update','appointment',aid,json.dumps({'status':status}))
            return self.send_json(200,{'id':aid,'status':status})
    def update_user(self,uid):
        actor=self.role('settings'); d=self.body()
        if not isinstance(d,dict) or not d or set(d)-{'role','active'}: fail(400,'Only role and active can be updated')
        if 'role' in d and d['role'] not in ROLES: fail(400,'Unknown role')
        if 'active' in d and not isinstance(d['active'],bool): fail(400,'active must be boolean')
        with self.db() as db:
            existing=db.execute('SELECT id,role,active FROM users WHERE id=?',(uid,)).fetchone()
            if not existing: fail(404,'User not found')
            if uid==actor['id'] and (d.get('active') is False or d.get('role','admin')!='admin'): fail(409,'You cannot disable or demote your current administrator account')
            removes_admin=existing['role']=='admin' and existing['active'] and (d.get('role','admin')!='admin' or d.get('active',True) is False)
            if removes_admin and db.execute("SELECT COUNT(*) FROM users WHERE role='admin' AND active=1 AND id<>?",(uid,)).fetchone()[0]==0: fail(409,'At least one active administrator must remain')
            db.execute('UPDATE users SET '+','.join(f'{k}=?' for k in d)+' WHERE id=?',(*d.values(),uid)); record_audit(db,actor['id'],'update','user',uid,json.dumps(d))
            return self.send_json(200,{'id':uid,'ok':True})
    def create_staff(self):
        user=self.role('staff'); d=self.body()
        if not isinstance(d,dict): fail(400,'JSON object required')
        code=clean_text(d.get('code'),'code',32); name=clean_text(d.get('full_name'),'full_name',120); role=clean_text(d.get('role'),'role',80); dept=clean_text(d.get('department'),'department',80)
        with self.db() as db:
            cur=db.execute('INSERT INTO staff(code,full_name,role,department,created_at) VALUES(?,?,?,?,?)',(code,name,role,dept,now())); record_audit(db,user['id'],'create','staff',cur.lastrowid)
            return self.send_json(201,{'id':cur.lastrowid})
    def create_inventory(self):
        user=self.role('inventory'); d=self.body()
        if not isinstance(d,dict): fail(400,'JSON object required')
        sku=clean_text(d.get('sku'),'sku',32); name=clean_text(d.get('name'),'name',120); category=clean_text(d.get('category'),'category',80); unit=clean_text(d.get('unit','units'),'unit',24)
        qty=d.get('quantity'); low=d.get('reorder_level')
        if any(isinstance(x,bool) or not isinstance(x,int) or x<0 for x in (qty,low)): fail(400,'quantity and reorder_level must be non-negative integers')
        with self.db() as db:
            cur=db.execute('INSERT INTO inventory(sku,name,category,quantity,reorder_level,unit,updated_at) VALUES(?,?,?,?,?,?,?)',(sku,name,category,qty,low,unit,now()));
            if qty: db.execute('INSERT INTO stock_movements(inventory_id,delta,reason,actor_id,created_at) VALUES(?,?,?,?,?)',(cur.lastrowid,qty,'Initial quantity',user['id'],now()))
            record_audit(db,user['id'],'create','inventory',cur.lastrowid)
            return self.send_json(201,{'id':cur.lastrowid})
    def stock_movement(self,iid):
        user=self.role('inventory'); d=self.body()
        if not isinstance(d,dict): fail(400,'JSON object required')
        delta=d.get('delta'); reason=clean_text(d.get('reason'),'reason',160)
        if isinstance(delta,bool) or not isinstance(delta,int) or delta==0: fail(400,'delta must be a non-zero integer')
        with self.db() as db:
            row=db.execute('SELECT quantity FROM inventory WHERE id=?',(iid,)).fetchone()
            if not row: fail(404,'Inventory item not found')
            new=row['quantity']+delta
            if new<0: fail(409,'Movement would create negative stock')
            db.execute('UPDATE inventory SET quantity=?,updated_at=? WHERE id=?',(new,now(),iid)); db.execute('INSERT INTO stock_movements(inventory_id,delta,reason,actor_id,created_at) VALUES(?,?,?,?,?)',(iid,delta,reason,user['id'],now())); record_audit(db,user['id'],'stock_movement','inventory',iid,json.dumps({'delta':delta,'reason':reason}))
            return self.send_json(200,{'id':iid,'quantity':new})
    def update_settings(self):
        user=self.role('settings'); d=self.body()
        allowed={'facility_name','low_stock_threshold'}
        if not isinstance(d,dict) or not d or set(d)-allowed: fail(400,'Only facility_name and low_stock_threshold can be changed')
        with self.db() as db:
            for k,v in d.items():
                if k=='facility_name': v=clean_text(v,k,100)
                else:
                    if isinstance(v,bool): fail(400,'low_stock_threshold must be numeric')
                    try: v=str(float(v))
                    except (TypeError,ValueError): fail(400,'low_stock_threshold must be numeric')
                    if not 0<=float(v)<=1: fail(400,'low_stock_threshold must be between 0 and 1')
                db.execute('INSERT INTO settings(key,value,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at',(k,v,now()))
            record_audit(db,user['id'],'update','settings',detail=json.dumps(list(d)))
            return self.send_json(200,{'ok':True})
    def import_patients(self):
        user=self.role('import'); text=self.body(raw=True); reader=csv.DictReader(io.StringIO(text))
        required={'code','full_name','email','age'}
        if not reader.fieldnames: fail(400,'CSV needs a header row')
        original_headers=reader.fieldnames
        headers=[(h or '').strip().lower() for h in original_headers]
        if len(headers)!=len(set(headers)): fail(400,'CSV headers must be unique after case/space normalization')
        if not required.issubset(set(headers)): fail(400,'CSV headers must include code,full_name,email,age')
        rows=[]
        for n,raw_row in enumerate(reader,2):
            if n>1001: fail(413,'CSV limited to 1000 data rows')
            if None in raw_row: fail(400,f'Extra CSV columns on row {n}')
            row={headers[i]:raw_row.get(original_headers[i]) for i in range(len(headers))}
            try: age=int(row.get('age',''))
            except ValueError: fail(400,f'Invalid age on CSV row {n}')
            if not 0<=age<=120: fail(400,f'Age out of range on CSV row {n}')
            email=clean_text(row.get('email',''),'email',254,False)
            if email and not re.fullmatch(r'[^@\s]+@(?:[A-Za-z0-9-]+\.)+invalid',email,re.I): fail(400,f'Use valid-looking .invalid demo emails (row {n})')
            rows.append((clean_text(row.get('code'),'code',32),clean_text(row.get('full_name'),'full_name',120),email,age,'active',now()))
        if not rows: fail(400,'CSV has no data rows')
        with self.db() as db:
            db.executemany('INSERT INTO patients(code,full_name,email,age,status,created_at) VALUES(?,?,?,?,?,?)',rows); record_audit(db,user['id'],'import','patients',detail=json.dumps({'rows':len(rows)}))
        return self.send_json(201,{'imported':len(rows)})
    def export_patients(self):
        self.session()
        with self.db() as db: rows=db.execute('SELECT code,full_name,email,age,status,created_at FROM patients ORDER BY id').fetchall()
        def safe_cell(value):
            if isinstance(value,str) and value.startswith(('=','+','-','@','\t','\r')): return "'"+value
            return value
        buf=io.StringIO(newline=''); w=csv.writer(buf); w.writerow(['code','full_name','email','age','status','created_at']); w.writerows([[safe_cell(v) for v in tuple(r)] for r in rows])
        return self.send_csv('healthops-demo-patients.csv',buf.getvalue())

def serve(host='127.0.0.1',port=8787):
    if host not in ('127.0.0.1','localhost','::1') and not READ_ONLY_MODE:
        raise SystemExit('Refusing remote bind unless HEALTHOPS_READ_ONLY=1; do not expose the mutable local demo.')
    initialize(public_read_only=READ_ONLY_MODE)
    ThreadingHTTPServer((host,port),Handler).serve_forever()
if __name__=='__main__': serve(os.environ.get('HEALTHOPS_HOST','127.0.0.1'),int(os.environ.get('PORT','8787')))
