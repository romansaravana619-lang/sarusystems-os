const request=async<T>(token:string,path:string,init?:RequestInit):Promise<T>=>{const r=await fetch(`${import.meta.env.VITE_API_BASE_URL||"http://localhost:8000"}${path}`,{...init,headers:{"Content-Type":"application/json",Authorization:`Bearer ${token}`,...(init?.headers||{})}});if(!r.ok)throw new Error((await r.json()).detail||"Request failed");return r.json()};
export type SocialPost={id:string;platform:string;post_id:string;post_title:string|null;post_content:string|null;alt_text:string|null;creative_url:string|null;external_link:string|null;status:string;post_date:string|null;notes:string|null};
export type SocialDashboard={total_posts:number;drafts:number;ready:number;scheduled:number;published:number;by_platform:Record<string,number>;recent_posts:SocialPost[]};
export const getSocialDashboard=(token:string)=>request<SocialDashboard>(token,"/social-media/dashboard");
export const getSocialPosts=(token:string)=>request<SocialPost[]>(token,"/social-media/posts");
export const createSocialPost=(token:string,p:Partial<SocialPost>)=>request<SocialPost>(token,"/social-media/posts",{method:"POST",body:JSON.stringify(p)});
export const updateSocialPost=(token:string,id:string,p:Partial<SocialPost>)=>request<SocialPost>(token,`/social-media/posts/${id}`,{method:"PATCH",body:JSON.stringify(p)});
