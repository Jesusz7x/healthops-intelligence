#!/usr/bin/env python3
"""Review CSV structure and data quality without changing source files."""
from __future__ import annotations
import argparse, csv, json, re, sys
from collections import defaultdict
from pathlib import Path

EMAIL_RE=re.compile(r'^[^\s@]+@[^\s@]+\.invalid$',re.I)
def inspect_rows(rows, required=('code','full_name','email','age')):
    issues=[]; keys=defaultdict(list); seen_codes={}
    for n,row in enumerate(rows, start=2):
        normalized={str(k or '').strip().lower():str(v or '').strip() for k,v in row.items()}
        for field in required:
            if not normalized.get(field): issues.append({'row':n,'field':field,'kind':'missing_required'})
        code=normalized.get('code','').casefold()
        if code:
            if code in seen_codes: issues.append({'row':n,'field':'code','kind':'duplicate','matches_row':seen_codes[code]})
            else: seen_codes[code]=n
        name=' '.join(normalized.get('full_name','').split()).casefold()
        if name: keys[name].append(n)
        email=normalized.get('email','')
        if email and not EMAIL_RE.fullmatch(email): issues.append({'row':n,'field':'email','kind':'invalid_demo_email'})
        age=normalized.get('age','')
        if age:
            try:
                if not 0<=int(age)<=120: raise ValueError
            except ValueError: issues.append({'row':n,'field':'age','kind':'invalid_integer_or_range'})
    for name,lines in keys.items():
        if len(lines)>1:
            for n in lines[1:]: issues.append({'row':n,'field':'full_name','kind':'possible_duplicate_name','matches_row':lines[0]})
    return {'rows_scanned':len(rows),'issue_count':len(issues),'issues':issues,'source_modified':False,'limitations':['Names are only possible duplicate signals; shared names are not proof of duplicate people.','The reserved .invalid domain is required for demo email addresses.','This tool reports issues and never edits the input file.']}
def inspect_file(path):
    with Path(path).open('r',encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f)
        if not reader.fieldnames: return {'rows_scanned':0,'issue_count':1,'issues':[{'row':1,'kind':'missing_header'}],'source_modified':False}
        return inspect_rows(list(reader))
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('csv_file');p.add_argument('--output',help='Optional JSON report path; never overwrites input')
    args=p.parse_args()
    try: report=inspect_file(args.csv_file)
    except (OSError,UnicodeError,csv.Error) as e: p.error(str(e))
    text=json.dumps(report,indent=2,ensure_ascii=False)+'\n'
    if args.output:
        if Path(args.output).resolve()==Path(args.csv_file).resolve(): p.error('report output must not overwrite the input file')
        if Path(args.output).exists(): p.error('report output already exists; choose a new path')
        Path(args.output).write_text(text,encoding='utf-8')
    else: sys.stdout.write(text)
    return 1 if report['issue_count'] else 0
if __name__=='__main__': raise SystemExit(main())
