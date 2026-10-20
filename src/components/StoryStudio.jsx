import { useEffect, useRef, useState } from 'react';
import { Film, Mic2, Play, WandSparkles, AudioLines, CircleAlert } from 'lucide-react';
import { scenesFromScript, validateScenes } from '../project-format.js';
import { SCENE_THEMES, SCENE_TRANSITIONS, defaultSceneTheme, sceneTheme } from '../scene-presets.js';
import './storyboard.css';

export default function StoryStudio({
  script, scenes, onChange, aspect='9:16', mode='web', onRender, renderBusy=false,
  voiceEngine='system', onVoiceEngineChange, voiceCapabilities, scenePictures=[], onScenePicturesChange
}) {
  const [announcement,setAnnouncement]=useState('');
  const speechId=useRef(0);
  useEffect(()=>()=>{if(typeof window!=='undefined' && window.speechSynthesis)window.speechSynthesis.cancel();},[]);
  function update(values) {onChange(values);setAnnouncement('');}
  async function loadBackground(index,file) {
    if(!file) return;
    if(!['image/jpeg','image/png','image/webp'].includes(file.type) || file.size>2*1024*1024) {
      setAnnouncement('Use uma imagem JPG, PNG ou WebP de até 2 MB.');
      return;
    }
    const encoded=await new Promise((resolve,reject)=>{
      const reader=new FileReader();
      reader.onload=()=>resolve(reader.result);
      reader.onerror=()=>reject(new Error('Não foi possível ler a imagem.'));
      reader.readAsDataURL(file);
    }).catch(e=>{setAnnouncement(e.message);return null;});
    if(!encoded) return;
    const next=scenePictures.slice();next[index]=encoded;
    onScenePicturesChange?.(next);
    setAnnouncement('Imagem aplicada à cena '+(index+1)+'. O projeto JSON guarda apenas o tema, não a fotografia.');
  }
  function changeScene(index,changes) {
    update({script,scenes:scenes.map((s,n)=>n===index?{...s,...changes}:s)});
  }
  function preview(index) {
    if (!('speechSynthesis' in window) || !('SpeechSynthesisUtterance' in window)) {
      setAnnouncement('Narração de prévia indisponível neste navegador.'); return;
    }
    window.speechSynthesis.cancel();speechId.current++;
    const id=speechId.current;
    const u=new SpeechSynthesisUtterance(scenes[index].text);
    u.lang='pt-BR';u.rate=.92;
    const voice=window.speechSynthesis.getVoices().find(v=>v.lang.toLowerCase()==='pt-br');
    if(voice)u.voice=voice;
    u.onerror=()=>{if(id===speechId.current)setAnnouncement('Confira as vozes instaladas no sistema.');};
    window.speechSynthesis.speak(u);
  }
  const check=scenes.length?validateScenes(scenes):{error:'Adicione pelo menos uma cena.'};
  return <section id="studio-script" className="story-studio" aria-labelledby="story-studio-title">
    <div className="story-heading">
      <span className="section-kicker">MODO ROTEIRO</span>
      <h2 id="story-studio-title">Do texto à história</h2>
      <p>Organize até seis cenas, escolha os visuais, ouça a prévia e defina como serão as transições.</p>
    </div>
    <label className="story-label" htmlFor="story-script">Roteiro</label>
    <textarea id="story-script" rows={5} maxLength={4000} value={script} placeholder="Escreva aqui seu roteiro. Separe os assuntos com parágrafos."
      onChange={e=>update({script:e.target.value,scenes})}/>
    <div className="story-toolbar">
      <span>{script.length}/4000 caracteres</span>
      <button className="story-generate" type="button" disabled={script.trim().length<3 || renderBusy}
        onClick={()=>{const generated=scenesFromScript(script);onScenePicturesChange?.([]);update({script,scenes:generated});setAnnouncement(generated.length+' cena(s) criada(s). Ajuste os temas e transições antes de renderizar.');}}>
        <WandSparkles size={17} aria-hidden="true"/> Organizar cenas
      </button>
    </div>
    {scenes.length>0 && <div className="story-scenes" aria-label="Cenas do roteiro">
      {scenes.map((scene,i)=>{
        const theme=sceneTheme(scene.theme,i);
        return <div className="story-scene" key={i}>
          <div className="story-scene-number">0{i+1}</div>
          <div className="story-scene-fields">
            <div className="story-scene-preview" role="img" aria-label={'Prévia do tema '+theme.name}
              style={{background:scenePictures[i] ? 'linear-gradient(#06171175,#0617119e),url('+scenePictures[i]+') center/cover' : 'linear-gradient(125deg,'+theme.colors.join(',')+')'}}>
              <span>{scene.title || 'Cena '+(i+1)}</span>
              <small>{scene.text?.slice(0,110)}</small>
            </div>
            <div className="story-picture-controls">
              <label htmlFor={'scene-picture-'+i} className="story-picture-label">Imagem de fundo (JPG, PNG ou WebP, até 2 MB)</label>
              <input id={'scene-picture-'+i} type="file" accept="image/jpeg,image/png,image/webp" disabled={renderBusy}
                onChange={e=>loadBackground(i,e.target.files?.[0])}/>
              {scenePictures[i] && <button type="button" className="story-picture-clear" onClick={()=>onScenePicturesChange?.(scenePictures.map((p,n)=>i===n?null:p))}>Remover imagem</button>}
            </div>
            <label htmlFor={'scene-title-'+i}>Título da cena</label>
            <input id={'scene-title-'+i} value={scene.title} maxLength={70}
              onChange={e=>changeScene(i,{title:e.target.value})}/>
            <label htmlFor={'scene-text-'+i}>Texto da narração</label>
            <textarea id={'scene-text-'+i} value={scene.text} maxLength={500} rows={3}
              onChange={e=>changeScene(i,{text:e.target.value})}/>
            <div className="story-scene-options">
              <label htmlFor={'scene-theme-'+i}>Tema visual
                <select id={'scene-theme-'+i} value={scene.theme||defaultSceneTheme(i)} onChange={e=>changeScene(i,{theme:e.target.value})}>
                  {SCENE_THEMES.map(item=><option key={item.id} value={item.id}>{item.name}</option>)}
                </select>
              </label>
              <label htmlFor={'scene-transition-'+i}>Transição
                <select id={'scene-transition-'+i} value={scene.transition||'fade'} onChange={e=>changeScene(i,{transition:e.target.value})}>
                  {SCENE_TRANSITIONS.map(item=><option key={item.id} value={item.id}>{item.name}</option>)}
                </select>
              </label>
            </div>
          </div>
          <div className="story-scene-actions">
            <label htmlFor={'scene-length-'+i}>Duração (s)</label>
            <input id={'scene-length-'+i} type="number" min="2" max="15" step=".5" value={scene.duration}
              disabled={renderBusy} onChange={e=>changeScene(i,{duration:Number(e.target.value)})}/>
            <button type="button" className="story-listen" disabled={renderBusy} onClick={()=>preview(i)} aria-label={'Ouvir cena '+(i+1)}>
              <Play size={16} aria-hidden="true"/> Ouvir
            </button>
          </div>
        </div>;
      })}
    </div>}
    {mode==='desktop' && <fieldset className="story-voices">
      <legend><AudioLines size={17} aria-hidden="true"/> Voz da exportação</legend>
      <label className="story-voice-choice">
        <input type="radio" name="story-voice" value="system" checked={voiceEngine==='system'}
          onChange={()=>onVoiceEngineChange?.('system')} disabled={renderBusy}/>
        <span><strong>Voz do sistema</strong><small>Windows ou eSpeak NG, sem modelo extra.</small></span>
      </label>
      <label className="story-voice-choice">
        <input type="radio" name="story-voice" value="piper" checked={voiceEngine==='piper'}
          onChange={()=>onVoiceEngineChange?.('piper')} disabled={renderBusy}/>
        <span><strong>Piper neural (pt-BR)</strong><small>{voiceCapabilities?.piper?'Modelo local disponível.':'Configure PIPER_BIN e PIPER_MODEL para ativar.'}</small></span>
      </label>
      <p>O áudio da exportação é produzido pelo motor selecionado. A prévia “Ouvir” usa a voz do navegador, que pode soar diferente.</p>
    </fieldset>}
    {announcement && <p className="story-status" role="status" aria-live="polite">{announcement}</p>}
    {check.error && scenes.length>0 && <p className="story-warning" role="alert"><CircleAlert size={16}/>{check.error}</p>}
    <div className="story-foot">
      <p><AudioLines size={16} aria-hidden="true"/> A prévia é reproduzida no navegador. Temas e transições entram no projeto JSON; fotografias precisam ser escolhidas novamente.</p>
      {mode==='desktop' ? <button type="button" className="story-render"
        disabled={renderBusy || !!check.error || !onRender || (voiceCapabilities && !voiceCapabilities[voiceEngine])}
        onClick={()=>onRender(scenes)}><Film size={17} aria-hidden="true"/>{renderBusy?'Preparando narração…':'Gerar vídeo narrado'}</button>
        : <span className="story-web-info"><Mic2 size={15} aria-hidden="true"/> MP4 narrado disponível no desktop</span>}
    </div>
  </section>;
}
