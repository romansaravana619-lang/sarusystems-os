import { apiRequest } from "../../services/http";

export type Notification={id:string;company_id:string;recipient_user_id:string;notification_type:string;channel:string;priority:string;title:string;message:string;status:string;scheduled_for?:string|null;sent_at?:string|null;read_at?:string|null;source_type?:string|null;source_id?:string|null;action_url?:string|null;payload:Record<string,unknown>;error_message?:string|null};
export type NotificationDashboard={unread:number;high_priority:number;scheduled:number;failed:number;total:number};
export type Preference={id:string;notification_type:string;channel:string;enabled:boolean};
export const notificationsApi={
 dashboard:(t:string)=>apiRequest<NotificationDashboard>(t,"/notifications/dashboard"),
 list:(t:string)=>apiRequest<Notification[]>(t,"/notifications"),
 create:(t:string,p:unknown)=>apiRequest<Notification>(t,"/notifications",{method:"POST",body:JSON.stringify(p)}),
 read:(t:string,id:string)=>apiRequest<Notification>(t,`/notifications/${id}/read`,{method:"PATCH"}),
 archive:(t:string,id:string)=>apiRequest<Notification>(t,`/notifications/${id}/archive`,{method:"PATCH"}),
 preferences:(t:string)=>apiRequest<Preference[]>(t,"/notifications/preferences"),
 savePreference:(t:string,p:unknown)=>apiRequest<Preference>(t,"/notifications/preferences",{method:"PUT",body:JSON.stringify(p)})
};
