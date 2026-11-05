#!/usr/bin/env python3
"""One-shot private Alchemy Lab V4 retry, same non-resumable API as Gamer."""
import hashlib,json,os,re,time
from pathlib import Path
from datetime import datetime,timezone
from googleapiclient.http import MediaFileUpload
from games_alchemy_ai_upload import get_youtube,set_thumbnail
from youtube_public_tags import public_tags
from production_reservations import assert_reserved
from youtube_channel_registry import get_channel,KNOWN_IDS

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"alchemy-source-v4"
OUTPUT=ROOT/"alchemy-v4-retry-receipts.json"
OWNER="alchemy_v4_three_processing_reupload_20261105"
CHANNEL=KNOWN_IDS["alchemy"]
WORKFLOW="Alchemy - retry three Shorts with single-request upload"
TAG="autoeditorvideo-alchemy-v4-retry-single-20261105"
ROWS=[
 ("alchemy-001-chatgpt-gifs-v4","xeABjVrX09U"),
 ("alchemy-002-images-26-consistencia-v4","Vg1QNyPbN7s"),
 ("alchemy-003-gif-animado-tutorial-v4","ujhj3LgdqVc")
]
class UploadBlocked(Exception):pass

def digest(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
 return h.hexdigest()

def check():
 e=os.environ
 for k,v in {"GITHUB_REPOSITORY":"HelioConde/AutoEditorVideo","GITHUB_REF":"refs/heads/main","GITHUB_EVENT_NAME":"push","GITHUB_RUN_ATTEMPT":"1","GITHUB_WORKFLOW":WORKFLOW,"ALCHEMY_V4_RETRY_APPROVED":"true"}.items():
  if e.get(k)!=v:raise UploadBlocked("UNAPPROVED_WORKFLOW_"+k)
 if not e.get("YOUTUBE_CLIENT_JSON") or not e.get("YOUTUBE_CHANNEL_TOKEN_JSON"):
  raise UploadBlocked("OAUTH_NOT_CONFIGURED")
 c=get_channel("alchemy")
 if c["youtube_channel_id"]!=CHANNEL or c["oauth_token_secret_name"]!="YOUTUBE_ALCHEMY_TOKEN_JSON" or c["youtube_environment"]!="youtube-private-upload":
  raise UploadBlocked("WRONG_CHANNEL_CONFIG")
 if OUTPUT.exists():raise UploadBlocked("RECEIPT_EXISTS_NO_SECOND_RUN")
 summary=json.loads((DATA/"summary.json").read_text())
 if summary.get("schema")!="autoeditorvideo/games-alchemy-six-native-remotion-v4/v1" or summary.get("owner")!="games_alchemy_six_reference_v4_20261105" or len(summary.get("videos",[]))!=6:
  raise UploadBlocked("WRONG_SOURCE_ARTIFACT")
 listed={v["id"]:v for v in summary["videos"]}
 checked=[]
 for eid,old in ROWS:
  assert_reserved("alchemy",eid+"-reenvio1",OWNER)
  if eid not in listed or listed[eid]["channel"]!="alchemy":raise UploadBlocked("SOURCE_IS_NOT_ALCHEMY")
  folder=DATA/eid
  video=folder/"final.mp4";cover=folder/"thumb.jpg"
  meta=json.loads((folder/"metadata.json").read_text());qa=json.loads((folder/"qa.json").read_text())
  if (meta.get("id")!=eid or meta.get("channel_id")!=CHANNEL or meta.get("visibility")!="private"
      or str(meta.get("categoryId"))!="28" or meta.get("cover_template")!="gamer-alchemy-reference"
      or qa.get("structural_qa")!="passed" or qa.get("visual_profile")!="gamer-alchemy-reference"
      or qa.get("highlight_by_word_boundaries") is not True
      or digest(video)!=listed[eid]["sha256"] or digest(cover)!=qa["cover_sha256"]):
   raise UploadBlocked("SOURCE_QA_FAILED_"+eid)
  checked.append((eid,old,meta,video,cover))
 return checked

def existing(api,episode,title):
 owner=api.channels().list(part="contentDetails",mine=True).execute().get("items",[])
 if len(owner)!=1 or owner[0].get("id")!=CHANNEL:raise UploadBlocked("OAUTH_CHANNEL_MISMATCH")
 playlist=owner[0]["contentDetails"]["relatedPlaylists"]["uploads"]
 ids=[];cursor=None
 for i in range(6):
  req={"part":"contentDetails","playlistId":playlist,"maxResults":50}
  if cursor:req["pageToken"]=cursor
  result=api.playlistItems().list(**req).execute()
  ids.extend(v["contentDetails"]["videoId"] for v in result.get("items",[]) if v.get("contentDetails",{}).get("videoId"))
  cursor=result.get("nextPageToken")
  if not cursor:break
 matched=[]
 for i in range(0,len(ids),50):
  for v in api.videos().list(part="snippet,status",id=",".join(ids[i:i+50])).execute().get("items",[]):
   snippet=v.get("snippet",{})
   if (snippet.get("channelId")==CHANNEL and snippet.get("title")==title
       and v.get("status",{}).get("privacyStatus")=="private"
       and TAG in snippet.get("tags",[]) and "autoeditorvideo-episode-"+episode in snippet.get("tags",[])):
    matched.append(v["id"])
 if len(matched)>1:raise UploadBlocked("MORE_THAN_ONE_MATCH")
 return matched

def state(api,id):
 rows=api.videos().list(part="snippet,status,processingDetails,contentDetails",id=id).execute().get("items",[])
 if len(rows)!=1 or rows[0]["snippet"]["channelId"]!=CHANNEL or rows[0]["status"]["privacyStatus"]!="private":
  raise UploadBlocked("VIDEO_NOT_PRIVATE_IN_ALCHEMY")
 row=rows[0]
 return {"upload":row["status"].get("uploadStatus"),"processing":row.get("processingDetails",{}).get("processingStatus"),"duration":row.get("contentDetails",{}).get("duration")}

def save(items):
 OUTPUT.write_text(json.dumps(items,ensure_ascii=False,indent=2)+"\n")

def main():
 jobs=check();api=get_youtube("alchemy",dict(os.environ));receipts=[]
 for eid,old,meta,video,cover in jobs:
  state(api,old) # originals stay private
  seen=existing(api,eid,meta["title"])
  if seen:id=seen[0];reused=True
  else:
   body={"snippet":{"title":meta["title"],"description":meta["description"],
         "tags":public_tags(meta["tags"]),
         "categoryId":"28","defaultLanguage":"pt-BR"},
         "status":{"privacyStatus":"private","containsSyntheticMedia":True,"selfDeclaredMadeForKids":False}}
   try:
    result=api.videos().insert(part="snippet,status",body=body,
       media_body=MediaFileUpload(str(video),mimetype="video/mp4",resumable=False),
       notifySubscribers=False).execute(num_retries=0)
    id=result["id"];reused=False
   except Exception:
    time.sleep(20)
    recovered=existing(api,eid,meta["title"])
    if len(recovered)!=1:raise UploadBlocked("AMBIGUOUS_UPLOAD_NO_RETRY_"+eid)
    id=recovered[0];reused=True
  details=state(api,id)
  rec={"episode":eid+"-reenvio1","id":id,"url":"https://www.youtube.com/watch?v="+id,
       "old_id":old,"channel":"alchemy","private":True,"method":"non_resumable_single_request",
       "processing":details,"thumbnail_api_acknowledged":False,
       "created_utc":datetime.now(timezone.utc).isoformat()}
  receipts.append(rec);save(receipts)
  print("ALCHEMY_RETRY_PRIVATE_ID_"+eid+"_"+id,flush=True)
  if not reused:time.sleep(75)
  rec["thumbnail_api_acknowledged"]=set_thumbnail(api,id,cover)
  rec["processing"]=state(api,id);save(receipts)
  print("ALCHEMY_RETRY_THUMB_"+eid+"_"+str(rec["thumbnail_api_acknowledged"]),flush=True)
 if len(receipts)!=3:raise UploadBlocked("NOT_THREE_UPLOADS")
 print("ALCHEMY_ALL_THREE_PRIVATE_"+str(sum(x["processing"]["processing"]=="succeeded" for x in receipts))+"_PROCESSED",flush=True)

if __name__=="__main__":
 try:main()
 except Exception as exc:
  print("ALCHEMY_RETRY_BLOCKED_"+(str(exc) if isinstance(exc,UploadBlocked) else type(exc).__name__),flush=True)
  raise SystemExit(2)
