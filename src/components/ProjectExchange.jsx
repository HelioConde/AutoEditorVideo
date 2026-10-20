import { useRef,useState } from 'react';
import { ArrowDownToLine, FileJson2, Upload } from 'lucide-react';
import { createProjectFile, parseProjectFile } from '../project-format.js';
import './project-exchange.css';

export default function ProjectExchange({name,aspect,media,start,end,clips,script,scenes,voiceEngine='system',onImport,disabled=false}) {
  const input=useRef(null);
  const [status,setStatus]=useState('');
  const [importing,setImporting]=useState(false);
  function download() {
    const project=createProjectFile({name,aspect,media,start,end,clips,script,scenes,voiceEngine});
    const blob=new Blob([JSON.stringify(project,null,2)+'\n'],{type:'application/json'});
    const url=URL.createObjectURL(blob);
    const link=document.createElement('a');
    link.href=url;link.download=(name||'projeto').replace(/[^\p{L}\p{N}_ -]/gu,'').slice(0,48).trim().replace(/\s+/g,'-')+'.autoeditor.json';
    document.body.append(link);link.click();link.remove();
    window.setTimeout(()=>URL.revokeObjectURL(url),1000);
    setStatus('Projeto exportado. O vídeo original não faz parte deste arquivo.');
  }
  async function read(file) {
    if (!file || importing || disabled) return;
    setStatus('');
    setImporting(true);
    try {
      if (file.size>1024*1024) throw new Error('Arquivo de projeto acima de 1 MB.');
      const parsed=parseProjectFile(JSON.parse(await file.text()));
      await onImport(parsed);
      setStatus(parsed.media ? 'Projeto importado. Selecione o vídeo original para recuperar os cortes.' : 'Projeto importado com sucesso.');
    } catch(e) {setStatus('Não foi possível importar: '+(e?.message||'arquivo inválido'));}
    finally {setImporting(false);if(input.current)input.current.value='';}
  }
  return <div className="project-exchange" aria-label="Projetos portáteis">
    <div className="project-exchange-copy"><strong><FileJson2 size={16} aria-hidden="true"/> Mesmo projeto no site e desktop</strong><span>Exporte ou importe um projeto JSON. Os arquivos de vídeo devem ser selecionados novamente em outro dispositivo.</span></div>
    <div className="project-exchange-actions">
      <button type="button" className="exchange-btn" disabled={disabled} onClick={download}><ArrowDownToLine size={16} aria-hidden="true"/> Exportar projeto</button>
      <button type="button" className="exchange-btn exchange-import" disabled={disabled||importing} onClick={()=>input.current?.click()}><Upload size={16} aria-hidden="true"/> Importar projeto</button>
      <input id="project-json-input" type="file" ref={input} tabIndex={-1} accept=".json,application/json" disabled={disabled||importing} onChange={e=>read(e.target.files?.[0])} className="visually-hidden" />
    </div>
    {status && <p className="exchange-notice" role="status">{status}</p>}
  </div>;
}
