export type Activity={id:string;activity_type:string;direction:string;subject?:string|null;summary:string;occurred_at:string;actor_user_id?:string|null;client_id?:string|null;contact_id?:string|null;prospect_id?:string|null;opportunity_id?:string|null;project_id?:string|null;freelancer_id?:string|null;entity_type?:string|null;entity_id?:string|null;external_reference?:string|null;notes?:string|null};
export type ActivityDashboard={total:number;emails:number;calls:number;meetings:number;client_notes:number;internal_notes:number;interactions:number};
const request=async<T>(token:string,path:string,options?:RequestInit):Promise<T>=>{const response=await fetch(path,{...options,headers:{Authorization:`Bearer ${token}`,"Content-Type":"application/json",...(options?.headers??{})}});if(!response.ok)throw new Error(await response.text());return response.json()};
export const communicationApi={
 dashboard:(token:string)=>request<ActivityDashboard>(token,"/communication/dashboard"),
 activities:(token:string,params="")=>request<Activity[]>(token,`/communication/activities${params}`),
 create:(token:string,payload:unknown)=>request<Activity>(token,"/communication/activities",{method:"POST",body:JSON.stringify(payload)}),
 update:(token:string,id:string,payload:unknown)=>request<Activity>(token,`/communication/activities/${id}`,{method:"PATCH",body:JSON.stringify(payload)}),
 history:(token:string,entityType:string,entityId:string)=>request<Activity[]>(token,`/communication/activities/${entityType}/${entityId}`),
};
