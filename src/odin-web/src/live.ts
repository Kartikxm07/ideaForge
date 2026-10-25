import { BASE } from './api';
export function connectLive(onUpdate:()=>void,onState:(state:string)=>void,onExpired:()=>void){
 let source:EventSource|undefined,timer:ReturnType<typeof setTimeout>|undefined,closed=false,delay=1000;
 function connect(){if(closed)return;source=new EventSource(BASE+'/workspace/stream',{withCredentials:true});source.onopen=()=>{delay=1000;onState('Connected');};source.addEventListener('update',()=>onUpdate());source.addEventListener('expired',()=>{close();onExpired();});source.onerror=()=>{source?.close();onState('Reconnecting');timer=setTimeout(connect,delay);delay=Math.min(delay*2,30000);};}
 function close(){closed=true;clearTimeout(timer);source?.close();}
 connect();return close;
}
