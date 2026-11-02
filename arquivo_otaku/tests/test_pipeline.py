import json
import tempfile
import unittest
from pathlib import Path
from arquivo_otaku.pipeline import load_episode, plan_cuts, read_srt, visual_qa

SAMPLE={'id':'death-note','obra':'Death Note','titulo':'A disputa de Light e L',
        'roteiro':'Uma pergunta muda tudo. L encontra uma pista. Light precisa reagir.',
        'fatos_revisados':False,
        'cenas':[{'id':str(n),'papel':'teste','descricao':'cena'} for n in range(3)]}

class PipelineTests(unittest.TestCase):
    def test_no_publication_without_review(self):
        plan=plan_cuts(SAMPLE,seconds=12)
        self.assertTrue(plan['revisao_obrigatoria'])
        self.assertFalse(plan['publicacao_automatica'])
        self.assertEqual(len(plan['planos']),3)
    def test_cues_follow_srt(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'a.srt'
            p.write_text('1\n00:00:00,500 --> 00:00:02,300\nTeste.\n\n2\n00:00:02,300 --> 00:00:04,100\nFinal.\n',encoding='utf-8')
            cues=read_srt(p)
            plan=plan_cuts(SAMPLE,cues)
            self.assertEqual([p['inicio_ms'] for p in plan['planos']],[500,2300])
            self.assertEqual(plan['origem_tempos'],'srt')
    def test_invalid_id(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'a.json';p.write_text(json.dumps({**SAMPLE,'id':'../../x'}))
            with self.assertRaises(ValueError): load_episode(p)
    def test_invalid_cue(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'a.srt';p.write_text('1\n00:00:04,000 --> 00:00:01,000\nBad\n')
            with self.assertRaises(ValueError):read_srt(p)
    def test_invalid_seconds(self):
        with self.assertRaises(ValueError):plan_cuts(SAMPLE,seconds=-1)

if __name__=='__main__':unittest.main()
