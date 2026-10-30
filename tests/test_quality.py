import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'processing'))
from quality import inspect_rows

class DataQualityTests(unittest.TestCase):
    def test_flags_required_email_age_and_possible_duplicate_names(self):
        rows=[{'code':'A','full_name':'Sample Person','email':'sample@example.invalid','age':'30'}, {'code':'B','full_name':' sample   person ','email':'bad@example.com','age':'-1'}, {'code':'','full_name':'','email':'','age':''}]
        report=inspect_rows(rows)
        kinds={item['kind'] for item in report['issues']}
        self.assertEqual(report['rows_scanned'],3)
        self.assertTrue({'possible_duplicate_name','invalid_demo_email','invalid_integer_or_range','missing_required'}<=kinds)
        self.assertFalse(report['source_modified'])
    def test_duplicate_codes_are_flagged(self):
        report=inspect_rows([{'code':'x','full_name':'First','email':'a@example.invalid','age':'22'},{'code':' X ','full_name':'Second','email':'b@example.invalid','age':'23'}])
        self.assertIn('duplicate',{issue['kind'] for issue in report['issues']})
if __name__=='__main__': unittest.main(verbosity=2)
