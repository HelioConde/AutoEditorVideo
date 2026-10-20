import { useEffect, useRef, useState } from 'react';
import { Film, Mic2, Play, WandSparkles, RefreshCw, AudioLines, CircleAlert } from 'lucide-react';
import { scenesFromScript, validateScenes } from '../project-format.js';
import './storyboard.css';

export default function StoryStudio({ script, scenes, onChange, aspect='9:16', mode='web', onRender, renderBusy=false }) {
  const [announcement,setAnnouncement]=useState('');
  const [speaking,setSpeaking]=useState(false);
  const speechId=useRef(0);
  useEffect(()=>()=>{if(typeof window!=='undefined' && window.speechSynthesis)window.speechSynthesis.cancel();},[]);
  function update(values) {onChange(values);setAnnouncement('');}
  function preview(index) {
    if (!('speechSynthesis' in window) || !('SpeechSynthesisUtterance' in window)) {
      setAnnouncement('Narração de prévia indisponível neste navegador.'); return;
    }
    window.speechSynthesis.cancel();
    speechId.current++;
    const id=speechId.current;
    const u=new SpeechSynthesisUtterance(scenes[index].text);
    u.lang='pt-BR';u.rate=0.92;
    const voices=window.speechSynthesis.getVoices();
    const voice=voices.find(v=>v.lang.toLowerCase()==='pt-br');
    if(voice)u.voice=voice;
    u.onend=()=>{if(id===speechId.current)setSpeaking(false);};
    u.onerror=()=>{if(id===speechId.current){setSpeaking(false);setAnnouncement('Não foi possível reproduzir a voz. Confira as vozes disponíveis no sistema.');}};
    setSpeaking(true);
    window.speechSynthesis.speak(u);
  }
  const check = scenes.length ? validateScenes(scenes) : {error:'Adicione pelo menos uma cena.'};
  return <section className="story-studio" aria-labelledby="story-studio-title">
    <div className="story-heading">
      <span className="section-kicker">MODO ROTEIRO</span>
      <h2 id="story-studio-title">Do texto à história</h2>
      <p>Escreva seu roteiro, organize até seis cenas e ouça uma prévia da narração em português.</p>
    </div>
    <label className="story-label" htmlFor="story-script">Roteiro</label>
    <textarea id="story-script" rows={5} maxLength={4000} value={script} placeholder="Escreva aqui seu roteiro. Separe as ideias com parágrafos para criar cenas diferentes."
      onChange={e=>update({script:e.target.value,scenes})}/>
    <div className="story-toolbar">
      <span>{script.length}/4000 caracteres</span>
      <button className="story-generate" type="button" disabled={script.trim().length<3 || renderBusy}
        onClick={()=>{const generated=scenesFromScript(script);update({script,scenes:generated});setAnnouncement(generated.length+' cena(s) criada(s). Revise os textos antes de renderizar.');}}>
        <WandSparkles size={17} aria-hidden="true"/> Organizar cenas
      </button>
    </div>
    {scenes.length > 0 && <div className="story-scenes" aria-label="Cenas do roteiro">
      {scenes.map((scene,i)=><div className="story-scene" key={i}>
        <div className="story-scene-number">0{i+1}</div>
        <div className="story-scene-fields">
          <label htmlFor={'scene-title-'+i}>Título da cena</label>
          <input id={'scene-title-'+i} value={scene.title} maxLength={70} onChange={e=>update({script,scenes:scenes.map((s,n)=>n===i?{...s,title:e.target.value}:s)})}/>
          <label htmlFor={'scene-text-'+i}>Texto da narração</label>
          <textarea id={'scene-text-'+i} value={scene.text} maxLength={500} rows={3}
            onChange={e=>update({script,scenes:scenes.map((s,n)=>n===i?{...s,text:e.target.value}:s)})}/>
        </div>
        <div className="story-scene-actions"><label htmlFor={'scene-length-'+i}>Duração (s)</label>
          <input id={'scene-length-'+i} type="number" min="2" max="15" step=".5" value={scene.duration}
            disabled={renderBusy} onChange={e=>update({script,scenes:scenes.map((s,n)=>n===i?{...s,duration:Number(e.target.value)}:s)})} />
        <button type="button" className="story-listen" disabled={renderBusy} onClick={()=>preview(i)} aria-label={'Ouvir cena '+(i+1)}>
          <Play size={17} aria-hidden="true"/> Ouvir
        </button></div>
      </div>)}
    </div>}
    {announcement && <p className="story-status" role="status" aria-live="polite">{announcement}</p>}
    {check.error && scenes.length>0 && <p className="story-warning" role="alert"><CircleAlert size={16}/>{check.error}</p>}
    <div className="story-foot">
      <p><AudioLines size={16} aria-hidden="true"/> A prévia de voz usa a síntese do seu navegador; ela não é gravada no vídeo automaticamente.</p>
      {mode==='desktop' ? <button type="button" className="story-render" disabled={renderBusy || !!check.error || !onRender}
        onClick={()=>onRender(scenes)}><Film size={17} aria-hidden="true"/>{renderBusy?'Preparando narração…':'Gerar vídeo narrado'}</button> :
        <span className="story-web-info"><Mic2 size={15} aria-hidden="true"/> Vídeo narrado exportável disponível no desktop</span>}
    </div>
  </section>;
}
