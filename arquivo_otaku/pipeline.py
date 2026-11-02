"""Arquivo Otaku: planejamento e QA local, sem IA nem upload."""
import argparse,json,re
from pathlib import Path

def episodio(path):
    obj=json.loads(Path(path).read_text(encoding="utf-8-sig"))
    for key in ("id","obra","titulo","roteiro","cenas"):
        if not obj.get(key): raise ValueError("Campo ausente: "+key)
    if not re.fullmatch(r"[a-z0-9-]{1,70}",obj["id"]):
        raise ValueError("ID inseguro")
    if not 3<=len(obj["cenas"])<=20:raise ValueError("Requer 3-20 cenas")
    for cena in obj["cenas"]:
        if not all(cena.get(k) for k in ("id","papel","descricao")):
            raise ValueError("Cena incompleta")
    return obj

def srt(path):
    raw=Path(path).read_text(encoding="utf-8-sig").replace("\r\n","\n")
    out=[]
    pat=r"(\d\d:\d\d:\d\d,\d{3})\s*-->\s*(\d\d:\d\d:\d\d,\d{3})"
    def ms(v):
        h,m,s,t=map(int,re.split(r"[:,]",v))
        return ((h*60+m)*60+s)*1000+t
    for block in re.split(r"\n\s*\n",raw.strip()):
        lines=[x.strip() for x in block.split("\n") if x.strip()]
        found=next(((i,m) for i,line in enumerate(lines) if (m:=re.fullmatch(pat,line))),None)
        if found:
            i,m=found
            a,b=map(ms,m.groups())
            if b<=a or (out and a<out[-1]["inicio_ms"]):
                raise ValueError("SRT invalido")
            out.append({"inicio_ms":a,"fim_ms":b,"texto":" ".join(lines[i+1:])})
    if not out:raise ValueError("SRT vazio")
    return out

def plano(ep,legendas=None,duracao=None):
    cenas=ep["cenas"]; cortes=[]
    if legendas:
        for i,l in enumerate(legendas):
            cena=cenas[min(len(cenas)-1,i*len(cenas)//len(legendas))]
            cortes.append({**l,"cena_id":cena["id"],"papel":cena["papel"]})
        metodo="srt"; total=max(x["fim_ms"] for x in cortes)
    else:
        if duracao is not None and duracao<=0:raise ValueError("Duracao invalida")
        total=round(duracao*1000) if duracao else max(2500*len(cenas),2700*len(re.split(r"(?<=[.!?])\s+",ep["roteiro"])))
        for i,cena in enumerate(cenas):
            cortes.append({"inicio_ms":round(i*total/len(cenas)),"fim_ms":round((i+1)*total/len(cenas)),"cena_id":cena["id"],"papel":cena["papel"]})
        metodo="estimado"
    avisos=[]
    if metodo!="srt":avisos.append("Cortes estimados: fornecer SRT para alinhar falas")
    if not ep.get("fatos_revisados",False):avisos.append("Roteiro exige revisao factual")
    if any(x["fim_ms"]-x["inicio_ms"]>6500 for x in cortes):avisos.append("Planos longos: variar enquadramentos")
    if len({c["cena_id"] for c in cortes})<3:avisos.append("Pouca variedade de cenas")
    return {"id":ep["id"],"titulo":ep["titulo"],"metodo":metodo,"duracao_ms":total,"planos":cortes,"avisos":avisos,"publicacao_automatica":False}

def qa_imagens(files):
    from PIL import Image,ImageStat
    results=[]
    for f in files:
        with Image.open(f) as im:
            gray=im.convert("L").resize((128,128)); h=gray.histogram()
            ratio=sum(h[:64])/sum(h)
            results.append({"arquivo":Path(f).name,"brilho":round(ImageStat.Stat(gray).mean[0],1),"sombras_pct":round(ratio*100,1),"avisos":(["Muito escura"] if ratio>.82 else [])+(["Resolucao baixa"] if min(im.size)<640 else [])})
    return results

def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument("--episodio",type=Path,required=True)
    p.add_argument("--srt",type=Path)
    p.add_argument("--duracao",type=float)
    p.add_argument("--imagem",type=Path,action="append",default=[])
    p.add_argument("--saida",type=Path,default=Path("assets/gerados/plano-cortes.json"))
    a=p.parse_args(argv)
    r=plano(episodio(a.episodio),srt(a.srt) if a.srt else None,a.duracao)
    if a.imagem:r["qa_visual"]=qa_imagens(a.imagem)
    a.saida.parent.mkdir(parents=True,exist_ok=True)
    a.saida.write_text(json.dumps(r,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("[OK] Plano:",a.saida,"; sem APIs ou upload")
    for aviso in r["avisos"]:print("[AVISO]",aviso)
    return 0

if __name__=="__main__":raise SystemExit(main())
