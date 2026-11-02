'use strict';
const token = document.querySelector('meta[name="studio-token"]').content;
const el = id => document.getElementById(id);
let previous = '';
let running = false;

async function api(path, opts={}) {
  const response = await fetch(path, {cache:'no-store', ...opts,
    headers: {'X-Studio-Token':token, ...(opts.headers||{})}});
  const data = await response.json();
  if (!response.ok) throw Error(data.error||'Erro HTTP '+response.status);
  return data;
}

function payload(action) {
  return {
    action,
    id:el('episode').value.trim(),
    scene:Number(el('scene').value),
    model:el('model').value,
    budget:Number(el('budget').value),
    all:el('allScenes').checked
  };
}

async function launch(action) {
  if(running) return;
  const p=payload(action);
  if(action==='reparar' && p.all) {
    alert('Desmarque “Todas as cenas” para reparar apenas um fundo.');
    return;
  }
  if(action==='gerar') {
    if(p.budget===0) {
      alert('O limite está em zero. Para reutilizar o cache, use o botão “Recriar do cache”.');
      return;
    }
    if(!confirm('Autorizar até '+p.budget+' chamadas novas de imagem para este episódio?')) return;
  }
  if(action==='reparar' && !confirm('Refazer o fundo da cena '+p.scene+' com até 1 chamada de IA?')) return;
  if(action==='iniciar_proxy' && !confirm('Iniciar o serviço de terceiros já instalado no Docker? Nenhuma conta será trocada.')) return;
  if(action==='login_proxy' && !confirm('Iniciar autorização de login manual no Codex Proxy de terceiros? Verifique o domínio mostrado no log.')) return;
  try {
    await api('/api/run',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify(p)});
    await status();
  } catch(err) {
    alert('Não foi possível iniciar: '+err.message);
  }
}

async function status() {
  try {
    const state=await api('/api/state');
    running=state.busy;
    document.querySelectorAll('[data-action]').forEach(b=>b.disabled=running);
    el('taskState').textContent=running?'● Executando '+state.action
      :state.code===null?'Pronto':state.code===0?'✓ Concluído':'✕ Falhou';
    const lines=state.logs.join('\n');
    if(lines!==previous) {
      const node=el('logs');
      const nearBottom=node.scrollHeight-node.scrollTop-node.clientHeight<80;
      node.textContent=lines||'Nenhuma tarefa ainda.';
      if(nearBottom) node.scrollTop=node.scrollHeight;
      previous=lines;
    }
  } catch(err) {
    el('taskState').textContent='Servidor do Studio desconectado';
  }
}

async function connection() {
  try {
    const info=await api('/api/connection');
    const title=el('connectionTitle'),details=el('connectionDetails'),top=el('topStatus');
    const labels={
      conectado:'Codex conectado',offline:'Proxy offline',sem_chave:'Chave local ausente',
      erro_autenticacao:'Erro de autenticação',erro_contas:'Falha na consulta',
      sem_conta_elegivel:'Sem conta elegível'
    };
    title.textContent=labels[info.state]||info.state;
    details.textContent=info.message+' · '+info.accounts+' conta(s), '+info.eligible+' elegível(is).';
    top.dataset.state=info.state;
    top.textContent='● '+(labels[info.state]||'Estado desconhecido');
  } catch(err) {
    el('connectionTitle').textContent='Não foi possível consultar o proxy';
    el('connectionDetails').textContent=err.message;
  }
}

document.querySelectorAll('[data-action]').forEach(button=>
  button.addEventListener('click',()=>launch(button.dataset.action)));
el('checkConnection').addEventListener('click',connection);
status();
connection();
setInterval(status,1000);
setInterval(connection,30000);
