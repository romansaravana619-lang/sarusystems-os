export type CalendarReminder={id:string;event_id:string;minutes_before:number;remind_at:string;status:string;delivered_at?:string|null};
export type CalendarEvent={id:string;company_id:string;event_type:string;title:string;description?:string|null;start_at:string;end_at:string;all_day:boolean;status:string;timezone:string;location?:string|null;meeting_url?:string|null;owner_user_id:string;attendees:string[];client_id?:string|null;contact_id?:string|null;prospect_id?:string|null;opportunity_id?:string|null;project_id?:string|null;freelancer_id?:string|null;task_id?:string|null;entity_type?:string|null;entity_id?:string|null;notes?:string|null;reminders:CalendarReminder[]};
export type CalendarDashboard={total_upcoming:number;today:number;discovery_calls:number;client_meetings:number;freelancer_meetings:number;deadlines:number;content_schedule:number;follow_ups:number;founder_reminders:number;overdue:number};
const request=async<T>(token:string,path:string,options?:RequestInit):Promise<T>=>{const response=await fetch(path,{...options,headers:{Authorization:`Bearer ${token}`,"Content-Type":"application/json",...(options?.headers??{})}});if(!response.ok)throw new Error(await response.text());return response.status===204?undefined as T:response.json()};
export const calendarApi={
 dashboard:(token:string)=>request<CalendarDashboard>(token,"/calendar/dashboard"),
 events:(token:string,params?:string)=>request<CalendarEvent[]>(token,`/calendar/events${params?`?${params}`:""}`),
 create:(token:string,payload:unknown)=>request<CalendarEvent>(token,"/calendar/events",{method:"POST",body:JSON.stringify(payload)}),
 update:(token:string,id:string,payload:unknown)=>request<CalendarEvent>(token,`/calendar/events/${id}`,{method:"PATCH",body:JSON.stringify(payload)}),
 addReminder:(token:string,id:string,payload:unknown)=>request<CalendarReminder>(token,`/calendar/events/${id}/reminders`,{method:"POST",body:JSON.stringify(payload)}),
 cancel:(token:string,id:string)=>request<void>(token,`/calendar/events/${id}`,{method:"DELETE"}),
};
