import { useMemo, useState } from 'react';
import { Captions, ChevronRight, Play, Sparkles, WandSparkles } from 'lucide-react';
import { rankShortsFromTranscript } from '../shorts-ranking.js';
import './shorts-studio.css';

const stamp=seconds=>{
  const n=Math.floor(seconds);
  return String(Math.floor(n/60)).padStart(2,'0')+':'+String(n%60).padStart(2,'0');
};
export default function ShortsStudio({
  subtitles=[],duration=0,mediaReady=false,disabled=false,
  transcribing=false,whisperAvailable=false,
  onTranscribe,onPreview,onUse,onGenerate
}) {
  const [showResults,setShowResults]=useState(false);
  const ranked=useMemo(()=>rankShortsFromTranscript(subtitles,{duration,maxClips:3}),[subtitles,duration]);
  const candidates=ranked.candidates;
  return <section className="shorts-studio" aria-labelledby="shorts-studio-title">
    <div className="shorts-studio-head">
      <div><span className="section-kicker">AUTOMAÇÃO / PRIMEIRA VERSÃO</span>
        <h2 id="shorts-studio-title"><WandSparkles size={21} aria-hidden="true"/> Criar Shorts automaticamente</h2>
        <p>O programa sugere os melhores trechos com base na transcrição. Revise antes de publicar.</p>
      </div>
      <span className="shorts-local">Processamento local</span>
    </div>
    {!mediaReady ? <p className="shorts-guidance">Importe um vídeo para começar a encontrar os melhores momentos.</p> :
      subtitles.length===0 ?
        <div className="shorts-empty">
          <Captions size={20} aria-hidden="true"/>
          <div><strong>Primeiro precisamos das falas do vídeo.</strong>
            <p>Use o Whisper.cpp local ou importe um SRT no editor de legendas. Assim conseguimos localizar trechos completos sem cortar frases ao acaso.</p></div>
          <button type="button" disabled={!whisperAvailable||disabled||transcribing||!onTranscribe}
            onClick={onTranscribe}>{transcribing?'Transcrevendo…':'Transcrever áudio'}</button>
        </div> :
        <>
          <div className="shorts-actions">
            <button type="button" disabled={disabled||!!ranked.error}
              onClick={()=>setShowResults(v=>!v)}>
              <Sparkles size={18} aria-hidden="true"/>
              {showResults?'Ocultar sugestões':'Encontrar melhores momentos'}
            </button>
            <span>Até 3 Shorts de 8 a 45 segundos, em 9:16.</span>
          </div>
          {ranked.error&&<p className="shorts-error" role="status">{ranked.error}</p>}
          {showResults && candidates.length>0 && <>
            <div className="shorts-results" aria-label="Momentos sugeridos">
              {candidates.map(candidate=><article className="shorts-candidate" key={candidate.start+'-'+candidate.end}>
                <div className="shorts-candidate-top">
                  <strong>#{candidate.rank} · {stamp(candidate.start)}–{stamp(candidate.end)}</strong>
                  <span aria-label={'Pontuação de sinais: '+candidate.score+' em 100'}>{candidate.score}/100 sinais</span>
                </div>
                <p className="shorts-reason">{candidate.reason}</p>
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
            <button className="shorts-generate" type="button" disabled={disabled||!onGenerate}
              onClick={()=>onGenerate(candidates)}>
              <WandSparkles size={19} aria-hidden="true"/>
              Gerar {candidates.length} {candidates.length===1?'Short legendado':'Shorts legendados'}
            </button>
          </>}
        </>
    }
    <p className="shorts-note">Pontuação experimental por padrões de fala, perguntas, contraste e continuidade.
      Não analisa emoções, imagens nem prevê viralização. A seleção precisa de revisão humana.</p>
  </section>;
}
