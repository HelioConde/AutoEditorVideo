import { useMemo, useState } from 'react';
import { Captions, ChevronRight, Play, Sparkles, WandSparkles } from 'lucide-react';
import { rankAutomaticShorts } from '../visual-highlights.js';
import './shorts-studio.css';

const stamp=seconds=>{
  const n=Math.floor(seconds);
  return String(Math.floor(n/60)).padStart(2,'0')+':'+String(n%60).padStart(2,'0');
};
export default function ShortsStudio({
  subtitles=[],duration=0,mediaReady=false,disabled=false,
  transcribing=false,whisperAvailable=false,
  onTranscribe,onPreview,onUse,onGenerate,onAnalyze,analysisSignals=null,analysisBusy=false
}) {
  const [showResults,setShowResults]=useState(false);
  const [profile,setProfile]=useState('podcast');
  const [selectedKeys,setSelectedKeys]=useState(null);
  const keyOf=c=>c.start+':'+c.end;
  const ranked=useMemo(()=>rankAutomaticShorts(subtitles,{duration,maxClips:3,profile,signals:analysisSignals}),[subtitles,duration,profile,analysisSignals]);
  const candidates=ranked.candidates;
  const approved=selectedKeys===null?candidates:candidates.filter(c=>selectedKeys.includes(keyOf(c)));
  return <section className="shorts-studio" aria-labelledby="shorts-studio-title">
    <div className="shorts-studio-head">
      <div><span className="section-kicker">AUTOMAÇÃO / PRIMEIRA VERSÃO</span>
        <h2 id="shorts-studio-title"><WandSparkles size={21} aria-hidden="true"/> Criar Shorts automaticamente</h2>
        <p>O programa sugere os melhores trechos com base na transcrição. Revise antes de publicar.</p>
      </div>
      <span className="shorts-local">Processamento local</span>
    </div>
    {!mediaReady ? <p className="shorts-guidance">Importe um vídeo para começar a encontrar os melhores momentos.</p> : <>
      {subtitles.length===0 && <div className="shorts-empty">
        <Captions size={20} aria-hidden="true"/>
        <div><strong>Vídeo sem transcrição: análise visual disponível.</strong>
          <p>Você pode procurar trechos com movimento mesmo sem fala. Para Shorts legendados, transcreva com Whisper.cpp ou importe um SRT. Sem transcrição, os MP4 serão exportados sem legendas.</p></div>
        <button type="button" disabled={!whisperAvailable||disabled||transcribing||!onTranscribe}
          onClick={onTranscribe}>{transcribing?'Transcrevendo…':'Transcrever áudio'}</button>
      </div>}
          <div className="shorts-profile">
            <label htmlFor="shorts-profile">Tipo de conteúdo</label>
            <select id="shorts-profile" disabled={disabled||analysisBusy} value={profile} onChange={e=>{setProfile(e.target.value);setShowResults(false);setSelectedKeys(null);}}>
              <option value="podcast">Podcast / Entrevista</option>
              <option value="gameplay">Gameplay / Live</option>
              <option value="tutorial">Tutorial / Aula</option>
            </select>
          </div>
          <div className="shorts-actions">
            <button type="button" disabled={disabled||analysisBusy|| (!!ranked.error && subtitles.length>0)}
              onClick={async()=>{
                if(showResults){setShowResults(false);return;}
                if(onAnalyze && !analysisSignals)await onAnalyze();
                setSelectedKeys(null);
                setShowResults(true);
              }}>
              <Sparkles size={18} aria-hidden="true"/>
              {analysisBusy?'Analisando áudio e cenas…':showResults?'Ocultar sugestões':subtitles.length?'Encontrar melhores momentos':'Analisar movimento no vídeo'}
            </button>
            <span>Até 3 Shorts de 8 a 45 segundos, em 9:16.</span>
          </div>
          {analysisSignals && <p className="shorts-analysis-summary" role="status">
            Análise local: {analysisSignals.audio?.length||0} amostras de áudio, {analysisSignals.scenes?.length||0} mudanças de cena e {analysisSignals.motion?.length||0} quadros avaliados para movimento.
            {analysisSignals.coverage?.audio===false?' O vídeo não possui uma faixa de áudio analisável.':''}
          </p>}
          {ranked.error&&<p className="shorts-error" role="status">{ranked.error}</p>}
          {showResults && candidates.length>0 && <>
            <div className="shorts-results" aria-label="Momentos sugeridos">
              {candidates.map(candidate=><article className="shorts-candidate" key={candidate.start+'-'+candidate.end}>
                <label className="shorts-candidate-select">
                  <input type="checkbox" checked={approved.some(c=>keyOf(c)===keyOf(candidate))}
                    disabled={disabled} onChange={e=>{
                      const all=selectedKeys===null?candidates.map(keyOf):selectedKeys;
                      setSelectedKeys(e.target.checked ? [...all,keyOf(candidate)] :
                        all.filter(key=>key!==keyOf(candidate)));
                    }}/>
                  Incluir Short #{candidate.rank} na exportação
                </label>
                <div className="shorts-candidate-top">
                  <strong>#{candidate.rank} · {stamp(candidate.start)}–{stamp(candidate.end)}</strong>
                  <span aria-label={'Pontuação de sinais: '+candidate.score+' em 100'}>{candidate.score}/100 sinais</span>
                </div>
                <p className="shorts-reason">{candidate.reason}</p>
                {candidate.evidence && <p className="shorts-evidence">
                  Evidências: {candidate.evidence.source} · {candidate.evidence.audioPeaks} picos de áudio · {candidate.evidence.sceneChanges} cortes visuais · movimento {candidate.evidence.motionActivity||0}
                </p>}
                <p className="shorts-transcript">“{candidate.transcript}”</p>
                <div className="shorts-candidate-actions">
                  <button type="button" disabled={disabled} onClick={()=>onPreview?.(candidate)}>
                    <Play size={15} aria-hidden="true"/> Ouvir momento
                  </button>
                  <button type="button" disabled={disabled} onClick={()=>onUse?.(candidate)}>
                    Usar na timeline <ChevronRight size={15} aria-hidden="true"/>
                  </button>
                </div>
              </article>)}
            </div>
            <p className="shorts-selected-summary" role="status">{approved.length} de {candidates.length} sugestões selecionadas.</p>
            <button className="shorts-generate" type="button" disabled={disabled||!onGenerate||!approved.length}
              onClick={()=>onGenerate(approved,profile)}>
              <WandSparkles size={19} aria-hidden="true"/>
              Gerar {approved.length} {subtitles.length?(approved.length===1?'Short legendado':'Shorts legendados'):(approved.length===1?'Short sem legendas':'Shorts sem legendas')}
            </button>
          </>}
        </>
    }
    <p className="shorts-note">Ranking experimental por transcrição, variação de volume e cortes visuais no FFmpeg.
      Sem fala, o motor usa movimento entre quadros: ele não reconhece jogadas, emoções ou potencial de viralização. Revise cada sugestão antes de publicar.</p>
  </section>;
}
