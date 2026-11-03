/**
 * Preserve true caption word timings but display short phrases instead of
 * cycling one lonely word at a time. Existing timed phrases stay untouched.
 */
export type TimedWord={text:string;startFrame:number;endFrame:number};
export type TimedCaption={startFrame:number;endFrame:number;text:string;words?:TimedWord[]};

export const groupLegacyCaptionWords=(input:TimedCaption[],fps:number):TimedCaption[]=>{
  if(!Number.isFinite(fps)||fps<=0)return input;
  const result:TimedCaption[]=[];
  let pending:TimedWord[]=[];
  const emit=()=>{
    if(!pending.length)return;
    result.push({
      startFrame:pending[0].startFrame,
      endFrame:pending[pending.length-1].endFrame,
      text:pending.map(w=>w.text).join(' '),
      words:pending,
    });
    pending=[];
  };
  for(const c of input){
    const text=(c.text||'').trim();
    if(!text||!Number.isFinite(c.startFrame)||!Number.isFinite(c.endFrame)||
       c.endFrame<=c.startFrame)continue;
    // Master subtitles already contain real grouped word timings.
    if(c.words?.length || text.split(/\s+/).length>1){
      emit();
      result.push(c);
      continue;
    }
    const last=pending[pending.length-1];
    if(last && (pending.length>=3 ||
       c.startFrame-pending[0].startFrame>fps*1.2 ||
       c.startFrame-last.endFrame>fps*.25 ||
       /[.!?…]$/.test(last.text))){
      emit();
    }
    pending.push({text,startFrame:c.startFrame,endFrame:c.endFrame});
  }
  emit();
  return result;
};
