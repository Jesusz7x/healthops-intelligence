"""SQLite persistence and seed data for the fictional HealthOps demo."""
from __future__ import annotations
import os, sqlite3, hashlib, secrets
from pathlib import Path
from datetime import datetime, timezone, timedelta

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.environ.get('HEALTHOPS_DB', ROOT / 'data' / 'healthops.sqlite3'))
ROLES = ('admin', 'operations', 'clinical', 'inventory', 'viewer')

def now(): return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
class ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc, tb):
        try:
            return super().__exit__(exc_type, exc, tb)
        finally:
            self.close()

def connect(path=DB_PATH):
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=8, factory=ClosingConnection)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    db.execute('PRAGMA busy_timeout=8000')
    return db

def password_hash(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    return salt.hex() + ':' + hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 240000).hex()
def verify_password(password, encoded):
    try:
        salt_hex, digest = encoded.split(':', 1)
        return secrets.compare_digest(password_hash(password, bytes.fromhex(salt_hex)).split(':',1)[1], digest)
    except (ValueError, TypeError): return False

def initialize(path=DB_PATH):
    with connect(path) as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL, display_name TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('admin','operations','clinical','inventory','viewer')), password_hash TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, expires_at TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS patients(id INTEGER PRIMARY KEY, code TEXT UNIQUE NOT NULL, full_name TEXT NOT NULL, email TEXT, age INTEGER NOT NULL CHECK(age BETWEEN 0 AND 120), status TEXT NOT NULL CHECK(status IN ('active','inactive')), created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS staff(id INTEGER PRIMARY KEY, code TEXT UNIQUE NOT NULL, full_name TEXT NOT NULL, role TEXT NOT NULL, department TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS appointments(id INTEGER PRIMARY KEY, patient_id INTEGER REFERENCES patients(id), staff_id INTEGER REFERENCES staff(id), starts_at TEXT NOT NULL, department TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('scheduled','completed','cancelled','no_show')), created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS inventory(id INTEGER PRIMARY KEY, sku TEXT UNIQUE NOT NULL, name TEXT NOT NULL, category TEXT NOT NULL, quantity INTEGER NOT NULL CHECK(quantity >= 0), reorder_level INTEGER NOT NULL CHECK(reorder_level >= 0), unit TEXT NOT NULL DEFAULT 'units', updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS stock_movements(id INTEGER PRIMARY KEY, inventory_id INTEGER NOT NULL REFERENCES inventory(id), delta INTEGER NOT NULL CHECK(delta <> 0), reason TEXT NOT NULL, actor_id INTEGER REFERENCES users(id), created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY, actor_id INTEGER REFERENCES users(id), action TEXT NOT NULL, entity TEXT NOT NULL, entity_id TEXT, detail TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS idx_appointments_starts ON appointments(starts_at);
        CREATE INDEX IF NOT EXISTS idx_audit_created ON audit(created_at DESC);
        ''')
        if db.execute('SELECT COUNT(*) FROM users').fetchone()[0] == 0:
            demos = [('admin@healthops.local','Demo Administrator','admin'),('ops@healthops.local','Demo Operations','operations'),('clinical@healthops.local','Demo Clinical','clinical'),('stock@healthops.local','Demo Inventory','inventory'),('viewer@healthops.local','Demo Viewer','viewer')]
            for email,name,role in demos: db.execute('INSERT INTO users(email,display_name,role,password_hash,created_at) VALUES(?,?,?,?,?)',(email,name,role,password_hash('DemoHealthOps!2026'),now()))
        if db.execute('SELECT COUNT(*) FROM patients').fetchone()[0] == 0:
            patients=[('P-1001','Avery Example','avery@example.invalid',34,'active'),('P-1002','Morgan Sample','morgan@example.invalid',58,'active'),('P-1003','Taylor Fiction','taylor@example.invalid',22,'active'),('P-1004','Riley Demo','riley@example.invalid',71,'inactive'),('P-1005','Jordan Placeholder','jordan@example.invalid',46,'active')]
            for code,name,email,age,status in patients: db.execute('INSERT INTO patients(code,full_name,email,age,status,created_at) VALUES(?,?,?,?,?,?)',(code,name,email,age,status,now()))
        if db.execute('SELECT COUNT(*) FROM staff').fetchone()[0] == 0:
            staff=[('S-201','Casey Example','Physician','Primary Care'),('S-202','Drew Sample','Nurse','Primary Care'),('S-203','Alex Fiction','Technician','Diagnostics'),('S-204','Sam Demo','Coordinator','Operations')]
            for code,name,role,dept in staff: db.execute('INSERT INTO staff(code,full_name,role,department,created_at) VALUES(?,?,?,?,?)',(code,name,role,dept,now()))
        if db.execute('SELECT COUNT(*) FROM inventory').fetchone()[0] == 0:
            items=[('MED-001','Demo gloves','PPE',240,80,'boxes'),('MED-002','Fictional gauze','Supplies',38,50,'packs'),('EQ-003','Sample thermometer','Equipment',12,5,'units'),('MED-004','Placeholder masks','PPE',95,30,'boxes')]
            for sku,name,cat,qty,low,unit in items: db.execute('INSERT INTO inventory(sku,name,category,quantity,reorder_level,unit,updated_at) VALUES(?,?,?,?,?,?,?)',(sku,name,cat,qty,low,unit,now()))
        if db.execute('SELECT COUNT(*) FROM appointments').fetchone()[0] == 0:
            pids=[r[0] for r in db.execute('SELECT id FROM patients ORDER BY id')]; sids=[r[0] for r in db.execute('SELECT id FROM staff ORDER BY id')]
            base=datetime.now(timezone.utc).replace(hour=9,minute=0,second=0,microsecond=0)
            for i in range(28):
                day=base-timedelta(days=27-i)
                daily_count=12 if i==15 else 1+(i%3)
                for j in range(daily_count):
                    start=day+timedelta(hours=(j%8))
                    status='completed' if start < datetime.now(timezone.utc) else 'scheduled'
                    db.execute('INSERT INTO appointments(patient_id,staff_id,starts_at,department,status,created_at) VALUES(?,?,?,?,?,?)',(pids[(i+j)%len(pids)],sids[(i+j)%len(sids)],start.isoformat(),('Primary Care','Diagnostics','Operations')[(i+j)%3],status,now()))
        db.execute("INSERT OR IGNORE INTO settings(key,value,updated_at) VALUES('facility_name','HealthOps Demo Center',?)",(now(),))
        db.execute("INSERT OR IGNORE INTO settings(key,value,updated_at) VALUES('low_stock_threshold','0.2',?)",(now(),))

def record_audit(db, actor, action, entity, entity_id=None, detail='{}'):
    db.execute('INSERT INTO audit(actor_id,action,entity,entity_id,detail,created_at) VALUES(?,?,?,?,?,?)',(actor,action,entity,str(entity_id) if entity_id is not None else None,detail,now()))
