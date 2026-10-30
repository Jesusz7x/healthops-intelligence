"""Transparent descriptive analytics; no clinical decisions or accuracy claims."""
from collections import Counter
from statistics import median
from datetime import datetime, timezone, timedelta

def dashboard(db):
    total=db.execute('SELECT COUNT(*) FROM patients WHERE status="active"').fetchone()[0]
    appts=db.execute('SELECT status, COUNT(*) n FROM appointments GROUP BY status').fetchall()
    statuses={r['status']:r['n'] for r in appts}
    inv=db.execute('SELECT COUNT(*) n, SUM(CASE WHEN quantity<=reorder_level THEN 1 ELSE 0 END) low FROM inventory').fetchone()
    staff=db.execute('SELECT COUNT(*) FROM staff WHERE active=1').fetchone()[0]
    return {'active_patients':total,'appointments_total':sum(statuses.values()),'appointments_by_status':statuses,'inventory_items':inv['n'],'low_stock_items':inv['low'] or 0,'active_staff':staff}

def reports(db):
    rows=db.execute("SELECT substr(starts_at,1,10) day, COUNT(*) count FROM appointments WHERE starts_at >= ? GROUP BY day ORDER BY day",((datetime.now(timezone.utc)-timedelta(days=27)).date().isoformat(),)).fetchall()
    byday={r['day']:r['count'] for r in rows}
    days=[(datetime.now(timezone.utc)-timedelta(days=n)).date().isoformat() for n in range(27,-1,-1)]
    values=[byday.get(d,0) for d in days]
    base=values[:-7]; recent=values[-7:]
    avg=sum(base)/len(base) if base else 0
    trend={'direction':'up' if sum(recent)>sum(values[-14:-7]) else 'down' if sum(recent)<sum(values[-14:-7]) else 'flat','change_percent':round((sum(recent)-sum(values[-14:-7]))/sum(values[-14:-7])*100,1) if sum(values[-14:-7]) else None}
    items=[dict(r) for r in db.execute('SELECT sku,name,category,quantity,reorder_level,unit FROM inventory ORDER BY quantity*1.0/CASE WHEN reorder_level=0 THEN 1 ELSE reorder_level END ASC')]
    low=[x for x in items if x['quantity']<=x['reorder_level']]
    threshold_row=db.execute("SELECT value FROM settings WHERE key='low_stock_threshold'").fetchone()
    try: critical_ratio=float(threshold_row['value']) if threshold_row else 0.2
    except (ValueError,TypeError): critical_ratio=0.2
    critical=[x for x in items if x['reorder_level']>0 and x['quantity']<=x['reorder_level']*critical_ratio]
    # Experimental robust outlier flags on daily counts (median absolute deviation, 3.5 scaled MAD).
    med=median(values) if values else 0
    mad=median([abs(v-med) for v in values]) if values else 0
    anomalies=[{'date':d,'appointments':v,'method':'median absolute deviation','reason':'Daily count is unusually far from the 28-day median'} for d,v in zip(days,values) if mad and abs(v-med)/(1.4826*mad)>3.5]
    # Baseline forecast is the trailing 28-day mean, rounded; this is a naive baseline, not a validated prediction.
    forecast=[{'day':(datetime.now(timezone.utc).date()+timedelta(days=i+1)).isoformat(),'expected_count':round(sum(values)/len(values),1) if values else 0} for i in range(7)]
    return {'appointments_daily':[{'day':d,'count':v} for d,v in zip(days,values)],'trend_last_7_vs_previous_7':trend,'inventory':items,'low_stock':low,'critical_stock':critical,'critical_stock_ratio':critical_ratio,'anomalies':anomalies,'demand_baseline_7d':forecast,'methods':{'trend':'sum of last 7 calendar days compared with previous 7 days','anomaly':'median absolute deviation (scaled MAD); flags only, never suppresses records','forecast':'constant mean of prior 28 calendar days; exploratory baseline only'},'limitations':['Synthetic demo data only.','Small sample and incomplete appointment history make the forecast unsuitable for staffing, diagnosis, or clinical decisions.','Outlier flags are exploratory and require human review.']}
