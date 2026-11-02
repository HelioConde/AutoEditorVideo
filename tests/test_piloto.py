"""Testes básicos do pacote sem acesso à internet nem renderização do mpt."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TestKit(unittest.TestCase):
    def test_todos_os_roteiros(self):
        for path in (ROOT / 'conteudos').glob('[0-9][0-9][0-9]-*.json'):
            if path.name.endswith('-direcao.json'):
                continue
            data=json.loads(path.read_text(encoding='utf-8'))
            self.assertGreater(len(data['roteiro']), 70)
            self.assertEqual(len(data['cenas']),6)
            self.assertTrue(all(len(s['cartela'])>4 for s in data['cenas']))

    def test_piloto_gera_cartelas_e_licencas(self):
        run=subprocess.run([sys.executable,str(ROOT/'scripts'/'piloto.py'), '--episodio','001-death-note'],
                          capture_output=True,text=True,check=False)
        self.assertEqual(run.returncode,0,run.stderr)
        dest=ROOT/'assets'/'gerados'/'001-death-note'
        self.assertEqual(len(list(dest.glob('cena-*.png'))),6)
        manifest=json.loads((dest/'licencas.json').read_text(encoding='utf-8'))
        self.assertEqual(len(manifest['material']),6)
        self.assertEqual(manifest['revisao_humana'],'PENDENTE')

    def test_sem_travessia_de_diretorio(self):
        run=subprocess.run([sys.executable,str(ROOT/'scripts'/'piloto.py'), '--episodio','../../etc/passwd'],
                          capture_output=True,text=True,check=False)
        self.assertNotEqual(run.returncode,0)


if __name__=='__main__': unittest.main()
