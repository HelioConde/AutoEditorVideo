"""Read-only inspection after a tag-cleanup privacy/ownership guard failed."""
import os,json,argparse
from pathlib import Path
from games_alchemy_ai_upload import get_youtube
from youtube_channel_registry import KNOWN_IDS
IDS={"games":["GPJa03DRf5Y","BCqrEmJa77E","j7_cAomsPvM"],
     "alchemy":["WNlK9OYe1jc","bk433QOIdK0","iKlsUANJ8og"]}
def main(channel):
  api=get_youtube(channel,dict(os.environ))
  mine=api.channels().list(part="id",mine=True).execute().get("items",[])
  if [x.get("id") for x in mine]!=[KNOWN_IDS[channel]]:raise ValueError("WRONG_ACCOUNT")
  items=api.videos().list(part="snippet,status",id=",".join(IDS[channel])).execute().get("items",[])
  results=[]
  for id in IDS[channel]:
    v=next((x for x in items if x.get("id")==id),None)
    row={"id":id,"found":v is not None,"owner_channel":v.get("snippet",{}).get("channelId") if v else None,
         "expected_channel":KNOWN_IDS[channel],
         "privacy":v.get("status",{}).get("privacyStatus") if v else None,
         "tag_count":len(v.get("snippet",{}).get("tags",[])) if v else None,
         "internal_tag_count":sum(x.casefold().startswith("autoeditorvideo") for x in v.get("snippet",{}).get("tags",[])) if v else None}
    results.append(row)
    print("DIAGNOSTIC_"+json.dumps(row,ensure_ascii=False),flush=True)
  out=Path("seo-tag-privacy-diagnostic");out.mkdir(exist_ok=True)
  (out/(channel+".json")).write_text(json.dumps(results,indent=2,ensure_ascii=False)+"\n")
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--channel",choices=list(IDS),required=True);v=p.parse_args();main(v.channel)
