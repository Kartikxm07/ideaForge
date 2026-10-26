// Next.js is the canonical ODIN workspace; keep the old development URL usable.
const destination = new URL(window.location.href);
destination.port = '3000';
destination.pathname = '/war-room';
destination.search = '?view=odin_web';
destination.hash = '';
window.location.replace(destination.toString());
export {};
