import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class RenderBlueprintTests(unittest.TestCase):
    def test_blueprint_uses_pinned_python_free_plan_and_read_only_healthcheck(self):
        config=(ROOT/'render.yaml').read_text()
        for entry in (
            'type: web', 'runtime: python', 'plan: free',
            'buildCommand: python3 --version', 'startCommand: python3 api/server.py',
            'healthCheckPath: /health', 'value: "3.13.5"',
            'value: 0.0.0.0', 'value: "1"',
        ):
            with self.subTest(entry=entry): self.assertIn(entry,config)
        self.assertNotIn('value: "http://',config)
        self.assertNotIn('DATABASE_URL',config)

    def test_runtime_reads_assigned_port_and_has_a_nonclinical_health_probe(self):
        source=(ROOT/'api/server.py').read_text()
        self.assertIn("int(os.environ.get('PORT','8787'))",source)
        self.assertIn("path in ('/health','/api/health')",source)
        self.assertIn("'synthetic_data_only':True",source)
if __name__=='__main__': unittest.main(verbosity=2)
