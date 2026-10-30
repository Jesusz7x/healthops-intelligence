import re, unittest
from html.parser import HTMLParser
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class Markup(HTMLParser):
    def __init__(self): super().__init__(); self.ids=[]; self.keys=[]
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if 'id' in attrs: self.ids.append(attrs['id'])
        if 'data-i' in attrs: self.keys.append(attrs['data-i'])
class FrontendContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html=(ROOT/'web/index.html').read_text(); cls.js=(ROOT/'web/app.js').read_text(); cls.parser=Markup(); cls.parser.feed(cls.html)
    def test_ids_are_unique_and_javascript_selectors_exist(self):
        ids=self.parser.ids
        self.assertEqual(len(ids),len(set(ids)))
        selectors=set(re.findall(r"\$\('#([A-Za-z0-9_-]+)'\)",self.js))
        dynamic={'settings-form','status-filter','appointment-filter','records-table','csv-import','table-search'}
        self.assertFalse(selectors-(set(ids)|dynamic),f'Missing static/dynamic IDs for JS selectors: {selectors-(set(ids)|dynamic)}')
    def test_every_static_translation_key_exists_in_both_languages(self):
        blocks=re.findall(r"(?:^|\n) (en|es):\{(.*?)\n \}",self.js,re.S)
        dictionaries={name:set(re.findall(r"(?:^|[,{])\s*([A-Za-z][A-Za-z0-9_]*):'",body)) for name,body in blocks}
        self.assertEqual(set(dictionaries),{'en','es'})
        self.assertEqual(dictionaries['en'],dictionaries['es'])
        self.assertFalse(set(self.parser.keys)-dictionaries['en'])
    def test_frontend_uses_same_origin_static_assets(self):
        self.assertIn('href="/styles.css"',self.html)
        self.assertIn('src="/app.js" defer',self.html)
        self.assertNotRegex(self.html,r'<script[^>]+src="https?://')
if __name__=='__main__': unittest.main(verbosity=2)
