import { useRef, useState } from 'react';
import { Captions, Download, FileUp, Plus, Sparkles, Trash2 } from 'lucide-react';
import { parseSubtitleText, toSrt, validateSubtitles, MAX_SUBTITLES } from '../subtitles.js';
import './subtitles.css';

export default function SubtitleStudio({
  subtitles=[],onChange,mediaDuration=0,previewTime=0,disabled=false,
  mode='web',onTranscribe,transcribing=false,whisperAvailable=false
}) {
  const inputRef=useRef(null);
  const [notice,setNotice]=useState('');
  const active=subtitles.find(c=>previewTime>=c.start&&previewTime<c.end);
  function update(next) {
    // Permit intermediate typing in the editor; validation is performed on export.
    onChange(next);setNotice('');
  }
  function patch(index,key,value) {
    update(subtitles.map((s,i)=>i===index?{...s,[key]:value}:s));
  }
  async function importFile(file) {
    if(!file)return;
    try{
      if(file.size>64000)throw new Error('O arquivo excede 64 KB.');
      const parsed=parseSubtitleText(await file.text());
      update(parsed);
      setNotice(parsed.length+' legendas importadas.');
    }catch(e){setNotice('Não foi possível importar: '+e.message);}
    finally{if(inputRef.current)inputRef.current.value='';}
  }
  function downloadSrt() {
    try {
      const content=toSrt(subtitles);
      const uri=URL.createObjectURL(new Blob(['\uFEFF'+content],{type:'text/plain;charset=utf-8'}));
      const anchor=document.createElement('a');
      anchor.href=uri;anchor.download='autoeditor-legendas.srt';document.body.append(anchor);anchor.click();anchor.remove();
      window.setTimeout(()=>URL.revokeObjectURL(uri),1000);
      setNotice('Legendas SRT exportadas.');
    }catch(e){setNotice(e.message);}
  }
  function addCue() {
    if(subtitles.length>=MAX_SUBTITLES)return;
    const last=subtitles.at(-1);
    const start=last?.end??0;
    if(start >= 3598)return setNotice('Limite de tempo das legendas atingido.');
    const end=Math.min(start+2,Math.max(start+2,Number(mediaDuration)||start+2));
    update([...subtitles,{start,end,text:'Nova legenda'}]);
  }
  const error=validateSubtitles(subtitles).error;
  return <section className="sub-studio" aria-labelledby="sub-studio-title">
    <div className="sub-head">
      <div><span className="section-kicker">LEGENDAS</span><h2 id="sub-studio-title"><Captions size={18} aria-hidden="true"/> Texto sincronizado</h2></div>
      <span className="sub-count">{subtitles.length}/{MAX_SUBTITLES}</span>
    </div>
    <p>Importe SRT ou VTT, corrija as falas e ajuste os horários antes de exportar.</p>
    <div className="sub-toolbar">
      <button type="button" disabled={disabled} onClick={()=>inputRef.current?.click()}><FileUp size={16}/> Importar SRT/VTT</button>
      <input ref={inputRef} type="file" accept=".srt,.vtt,text/plain,text/vtt" tabIndex={-1} className="visually-hidden"
        disabled={disabled} onChange={e=>importFile(e.target.files?.[0])} />
      <button type="button" disabled={disabled||!subtitles.length||!!error} onClick={downloadSrt}><Download size={16}/> Baixar SRT</button>
      <button type="button" disabled={disabled||subtitles.length>=MAX_SUBTITLES} onClick={addCue}><Plus size={16}/> Nova legenda</button>
    </div>
    {mode==='desktop' && <div className="sub-whisper">
      <div><strong><Sparkles size={16}/> Transcrição automática local</strong><small>{whisperAvailable?
        'Whisper.cpp disponível. A transcrição depende da velocidade do computador.':
        'Para ativar, configure WHISPER_BIN e WHISPER_MODEL no computador.'}</small></div>
      <button type="button" disabled={!whisperAvailable||!mediaDuration||disabled||transcribing||!onTranscribe}
        onClick={onTranscribe}>{transcribing?'Transcrevendo…':'Transcrever áudio'}</button>
    </div>}
    <div className="sub-preview" aria-live="off">
      <span>Prévia no tempo atual</span>
      <strong>{active?.text||'Sem legenda neste instante'}</strong>
    </div>
    {subtitles.length>0 && <ol className="sub-lines">
      {subtitles.map((cue,i)=><li key={i}>
        <div className="sub-line-head"><strong>Legenda {i+1}</strong><button type="button" title="Remover legenda"
          aria-label={'Remover legenda '+(i+1)} disabled={disabled} onClick={()=>update(subtitles.filter((_,j)=>i!==j))}><Trash2 size={15}/></button></div>
        <div className="sub-time-fields">
          <label>Início (s)<input type="number" step=".1" min="0" max="3600" disabled={disabled} value={cue.start}
            onChange={e=>patch(i,'start',Number(e.target.value))}/></label>
          <label>Fim (s)<input type="number" step=".1" min="0" max="3600" disabled={disabled} value={cue.end}
            onChange={e=>patch(i,'end',Number(e.target.value))}/></label>
        </div>
        <label>Texto da legenda<textarea maxLength={240} rows={2} disabled={disabled} value={cue.text}
          onChange={e=>patch(i,'text',e.target.value)}/></label>
      </li>)}
    </ol>}
    {error && <p className="sub-error" role="alert">{error}</p>}
    {notice && <p className="sub-notice" role="status">{notice}</p>}
    <p className="sub-explain">{mode==='desktop'?
      'No desktop, as legendas podem ser gravadas visualmente no MP4 dos cortes. Também é possível baixar SRT separado.':
      'No GitHub Pages, as legendas são exibidas na prévia e baixadas em SRT separado; ainda não são incorporadas ao MP4.'}</p>
  </section>;
}
