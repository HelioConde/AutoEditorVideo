/**
 * Map explicit reviewer approvals to server-ranked candidates.
 * Never accept timestamps alone as authorization for arbitrary source cuts.
 * Candidate start/end are already rounded to hundredths in the ranker.
 */
export function selectApprovedShorts(candidates,selection) {
  if(!Array.isArray(candidates))return {error:'Sugestões inválidas.',candidates:[]};
  if(selection===undefined)return {error:null,candidates};
  if(!Array.isArray(selection)||selection.length===0||selection.length>3)
    return {error:'Selecione entre 1 e 3 Shorts.',candidates:[]};
  const used=new Set();
  const selected=[];
  for(const value of selection) {
    if(!value||typeof value!=='object'||Array.isArray(value)||
      !Number.isFinite(value.start)||!Number.isFinite(value.end))
      return {error:'Seleção de Short inválida.',candidates:[]};
    const match=candidates.find(c=>Math.abs(c.start-value.start)<.005 && Math.abs(c.end-value.end)<.005);
    const key=match?match.start+':'+match.end:null;
    if(!match||used.has(key))return {error:'Os destaques mudaram. Analise novamente e revise a seleção.',candidates:[]};
    used.add(key);
    selected.push(match);
  }
  return {error:null,candidates:selected};
}
