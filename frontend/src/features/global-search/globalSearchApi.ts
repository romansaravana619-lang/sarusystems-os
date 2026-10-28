export type SearchResult={type:string;id:string;title:string;subtitle:string|null;status:string|null};
export type GlobalSearchResponse={query:string;count:number;results:SearchResult[]};
export const globalSearchApi={search:async(token:string,q:string,limit=30):Promise<GlobalSearchResponse>=>{const r=await fetch(`/global-search?q=${encodeURIComponent(q)}&limit=${limit}`,{headers:{Authorization:`Bearer ${token}`}});if(!r.ok)throw new Error(await r.text());return r.json()}};
