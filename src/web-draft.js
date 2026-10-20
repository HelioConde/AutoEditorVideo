import { createProjectFile, parseProjectFile } from './project-format.js';

export const WEB_DRAFT_KEY = 'autoeditor:web-draft:v1';
export const WEB_DRAFT_LIMIT = 140000;

export function loadWebDraft(storage) {
  if(!storage)return null;
  try {
    const raw=storage.getItem(WEB_DRAFT_KEY);
    if(!raw||raw.length>WEB_DRAFT_LIMIT)return null;
    const draft=JSON.parse(raw);
    if(draft.version!==1||typeof draft.savedAt!=='number')return null;
    return {savedAt:draft.savedAt,project:parseProjectFile(draft.project)};
  }catch{return null;}
}
export function saveWebDraft(storage,values) {
  if(!storage)return false;
  try{
    const project=createProjectFile(values);
    parseProjectFile(project);
    const raw=JSON.stringify({version:1,savedAt:Date.now(),project});
    if(raw.length>WEB_DRAFT_LIMIT)return false;
    storage.setItem(WEB_DRAFT_KEY,raw);
    return true;
  }catch{return false;}
}
export function clearWebDraft(storage) {
  try{storage?.removeItem(WEB_DRAFT_KEY);return true;}catch{return false;}
}
export function browserStorage(){try{return typeof window==='undefined'?null:window.localStorage;}catch{return null;}}
