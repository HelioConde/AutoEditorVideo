import unittest,tempfile,json
from pathlib import Path
from arquivo_otaku.pipeline import episodio,srt,plano
DATA={"id":"death-note","obra":"Death Note","titulo":"Light vs L","roteiro":"Light esconde o caderno. L procura pistas.","fatos_revisados":False,"cenas":[{"id":str(i),"papel":"Teste","descricao":"Cena"} for i in range(3)]}
class Tests(unittest.TestCase):
 def test_private_by_default(self):
  p=plano(DATA,duracao=12)
  self.assertFalse(p["publicacao_automatica"])
  self.assertIn("Roteiro exige revisao factual",p["avisos"])
 def test_srt_timing(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"a.srt";p.write_text("1\n00:00:00,500 --> 00:00:02,300\nTeste\n\n2\n00:00:02,300 --> 00:00:04,100\nFim\n")
   result=plano(DATA,srt(p))
   self.assertEqual(result["metodo"],"srt")
   self.assertEqual(result["planos"][0]["inicio_ms"],500)
 def test_unsafe_id(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"a.json";p.write_text(json.dumps({**DATA,"id":"../../x"}))
   with self.assertRaises(ValueError):episodio(p)
 def test_bad_srt(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"a.srt";p.write_text("1\n00:00:03,000 --> 00:00:01,000\nX")
   with self.assertRaises(ValueError):srt(p)
if __name__=="__main__":unittest.main()
