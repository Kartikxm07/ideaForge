import { z } from 'zod';
export const BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1';
export class ApiError extends Error { constructor(public status:number,message:string){super(message);} }
export async function api<T>(path:string, options:RequestInit = {}):Promise<T>{
  const response=await fetch(BASE+path,{...options,credentials:'include',headers:{'Content-Type':'application/json','X-Odin-Client':'web',...options.headers}});
  if(!response.ok){const data=await response.json().catch(()=>({})); const detail=Array.isArray(data.detail)?data.detail.map((d:{msg:string})=>d.msg).join('; '):data.detail;
    if(response.status===401 && !path.startsWith('/auth/')) window.dispatchEvent(new Event('odin:expired'));
    throw new ApiError(response.status, typeof detail==='string'?detail:`Request failed (${response.status})`);
  }
  return response.status===204?undefined:response.json();
}
export const send=<T>(path:string,data:unknown,method='POST')=>api<T>(path,{method,body:JSON.stringify(data)});
export const sessionSchema=z.object({user:z.object({id:z.string(),name:z.string(),email:z.string()}),organization_id:z.string(),role:z.enum(['admin','reviewer','viewer']),organizations:z.array(z.object({id:z.string(),name:z.string(),role:z.string()}))});
export type Session=z.infer<typeof sessionSchema>;
export type Evidence={document_key:string;clause_ref:string;quote:string;offset:number;content_sha256?:string};
export type Risk={id:string;run_id:string;claim:string;explanation:string;evidence:Evidence[];status:string;severity:string;review_status:string;created_at:string};
export type Run={id:string;question:string;focus:string;status:string;document_keys:string[];provider_kind:string;error:string|null;created_at:string;updated_at:string;findings:Risk[]};
export type Contract={id:string;document_key:string;title:string;status:string;severity:string;next_deadline:string|null;last_analyzed:string|null;updated_at:string;created_at:string;content_sha256:string;source:string};
export type Clause={id:string;title:string;text:string;offset:number};
export type Obligation={id:string;contract_id:string;title:string;due_date:string;kind:string;quote:string;clause_ref:string;basis:string;state?:string;days_remaining?:number;stale?:boolean};
export type Action={id:string;title:string;contract_id:string;finding_id:string;draft:string;type:string;status:string;version:number;evidence:Evidence[];rationale:string;history:{status:string;at:string}[]};
export type ContractDetail=Contract & {content:string;clauses:Clause[];analyses:Run[];risks:Risk[];obligations:Obligation[];actions:Action[]};
export type Agent={name:string;responsibility:string;state:string;task:string;executions:Run[]};
export type Audit={id:number;action:string;resource_id:string;outcome:string;created_at:string};
export type Dashboard={metrics:{contracts:number;high_risk:number;deadlines:number;actions:number;events:number};distribution:{name:string;value:number}[];deadlines:Obligation[];activity:Audit[];exposure:unknown[];exposure_note:string;unrated:number};
export type Simulation={id:string;reference_date:string;obligations:Obligation[];assumptions:string;summary:string;exposure:null};
export type Report={id:string;title:string;generated_at:string;contract_id:string|null;analyses:Run[];obligations:Obligation[];actions:Action[];uncertainty:string};
export type EventRecord={event_id:string;subject:string;body:string;occurred_at:string;channel:string;sender:string;recipient:string;source:string};
export type Settings={name:string;organization:string;notifications:boolean;provider:string;event_source:string;upload_formats:string[];analysis_limit:number;members:{id:string;name:string;email:string;role:string}[]};
export type Page<T>={items:T[];total:number;page:number;page_size:number};
export function uploadText(data:{document_key:string;title:string;content:string},onProgress:(n:number)=>void):Promise<Contract>{
 return new Promise((resolve,reject)=>{const xhr=new XMLHttpRequest();xhr.open('POST',BASE+'/workspace/upload');xhr.withCredentials=true;xhr.setRequestHeader('Content-Type','application/json');xhr.setRequestHeader('X-Odin-Client','web');xhr.upload.onprogress=e=>{if(e.lengthComputable)onProgress(Math.round(e.loaded/e.total*100));};xhr.onload=()=>{let body;try{body=JSON.parse(xhr.responseText);}catch{reject(new ApiError(xhr.status,'Invalid upload response'));return;}if(xhr.status>=200&&xhr.status<300)resolve(body);else reject(new ApiError(xhr.status,typeof body.detail==='string'?body.detail:'Upload rejected'));};xhr.onerror=()=>reject(new Error('Upload connection failed. Please retry.'));xhr.send(JSON.stringify(data));});
}
