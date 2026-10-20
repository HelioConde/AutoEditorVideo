// Frame renderer shared by both editions. Only client-created PNG data URIs
// are sent to the local desktop API; the web preview remains entirely local.
function wrap(ctx,text,maxWidth,maxLines) {
  const words=String(text).split(/\s+/),lines=[];
  let line='';
  for(const word of words) {
    const trial=line ? line+' '+word : word;
    if(ctx.measureText(trial).width>maxWidth && line) {
      lines.push(line); line=word;
      if(lines.length>=maxLines-1) break;
    } else line=trial;
  }
  if(line) lines.push(line);
  return lines.slice(0,maxLines);
}
export function createSceneImages(scenes,aspect='9:16') {
  if(typeof document==='undefined')throw new Error('A exportação de cenas precisa do navegador.');
  const vertical=aspect==='9:16',width=vertical?360:640,height=vertical?640:360;
  const palettes=[['#182b23','#507b50'],['#1b2635','#4c7294'],['#30263b','#9b648b'],['#302c21','#a58a55'],['#172e30','#4c8788'],['#292e31','#597282']];
  return scenes.map((scene,i)=>{
    const canvas=document.createElement('canvas');canvas.width=width;canvas.height=height;
    const ctx=canvas.getContext('2d');
    if(!ctx)throw new Error('Canvas indisponível para criar cenas.');
    const [dark,light]=palettes[i%palettes.length];
    const gradient=ctx.createLinearGradient(0,0,width,height);
    gradient.addColorStop(0,dark);gradient.addColorStop(1,light);
    ctx.fillStyle=gradient;ctx.fillRect(0,0,width,height);
    ctx.globalAlpha=.11;ctx.strokeStyle='#efffd5';ctx.lineWidth=2;
    for(let j=0;j<6;j++){ctx.beginPath();ctx.arc(width*.82,height*.17,60+j*35,0,Math.PI*2);ctx.stroke();}
    ctx.globalAlpha=1;
    const margin=28,maxW=width-margin*2;
    ctx.font='700 12px Arial,sans-serif';ctx.fillStyle='#d5f579';
    ctx.fillText('AUTOEDITOR  /  CENA '+String(i+1).padStart(2,'0'),margin,vertical?88:54);
    ctx.fillStyle='#f5f9ef';ctx.font='bold '+(vertical?26:29)+'px Arial,sans-serif';
    const title=wrap(ctx,scene.title,maxW,3);
    let y=vertical?176:123;
    title.forEach(line=>{ctx.fillText(line,margin,y);y+=vertical?36:38;});
    y+=vertical?30:10;
    ctx.font=(vertical?17:18)+'px Arial,sans-serif';
    ctx.fillStyle='#edf4e4';
    const lines=wrap(ctx,scene.text,maxW,vertical?12:7);
    lines.forEach(line=>{ctx.fillText(line,margin,y);y+=vertical?29:26;});
    ctx.fillStyle='#d5f579';ctx.fillRect(margin,height-46,Math.min(width-2*margin,75),4);
    const data=canvas.toDataURL('image/png');
    return data;
  });
}
