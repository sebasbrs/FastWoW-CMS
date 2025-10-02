import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { environment } from './environments';

const BASE = environment.apiBase;

@Injectable({ providedIn: 'root' })
export class AdminService {
  constructor(private http: HttpClient){}

  // ---- News ----
  listNews(page=1, page_size=20){
    return firstValueFrom(this.http.get<any>(`${BASE}/news/admin?page=${page}&page_size=${page_size}`));
  }
  createNews(data: { title:string; content:string; summary?:string; realm_id?:number; publish?:boolean; priority?:number; }){
    return firstValueFrom(this.http.post(`${BASE}/news`, data));
  }
  updateNews(id:number, data: Partial<{ title:string; content:string; summary:string; realm_id:number; publish:boolean; priority:number; }>){
    return firstValueFrom(this.http.patch(`${BASE}/news/${id}`, data));
  }
  deleteNews(id:number){
    return firstValueFrom(this.http.delete(`${BASE}/news/${id}`));
  }
  deleteNewsComment(newsId:number, commentId:number){
    return firstValueFrom(this.http.delete(`${BASE}/news/${newsId}/comments/${commentId}`));
  }

  // ---- Forum Categories ----
  listCategories(){ return firstValueFrom(this.http.get<any[]>(`${BASE}/forum/categories`)); }
  createCategory(data:{ name:string; description?:string; position?:number; }){ return firstValueFrom(this.http.post(`${BASE}/forum/categories`, data)); }
  updateCategory(id:number, data:Partial<{ name:string; description:string; position:number; }>) { return firstValueFrom(this.http.patch(`${BASE}/forum/categories/${id}`, data)); }
  deleteCategory(id:number){ return firstValueFrom(this.http.delete(`${BASE}/forum/categories/${id}`)); }

  // ---- Forum Topics ----
  listTopics(categoryId:number, page=1, page_size=50){ return firstValueFrom(this.http.get(`${BASE}/forum/categories/${categoryId}/topics?page=${page}&page_size=${page_size}`)); }
  createTopic(categoryId:number, data:{ title:string; content:string; }){ return firstValueFrom(this.http.post(`${BASE}/forum/categories/${categoryId}/topics`, data)); }
  getTopic(topicId:number){ return firstValueFrom(this.http.get(`${BASE}/forum/topics/${topicId}`)); }
  editTopic(topicId:number, data:Partial<{ title:string; }>) { return firstValueFrom(this.http.patch(`${BASE}/forum/topics/${topicId}`, data)); }
  deleteTopic(topicId:number){ return firstValueFrom(this.http.delete(`${BASE}/forum/topics/${topicId}`)); }
  lockTopic(topicId:number){ return firstValueFrom(this.http.post(`${BASE}/forum/topics/${topicId}/lock`, {})); }
  unlockTopic(topicId:number){ return firstValueFrom(this.http.post(`${BASE}/forum/topics/${topicId}/unlock`, {})); }
  pinTopic(topicId:number){ return firstValueFrom(this.http.post(`${BASE}/forum/topics/${topicId}/pin`, {})); }
  unpinTopic(topicId:number){ return firstValueFrom(this.http.post(`${BASE}/forum/topics/${topicId}/unpin`, {})); }
  moveTopic(topicId:number, newCategoryId:number){ return firstValueFrom(this.http.post(`${BASE}/forum/topics/${topicId}/move/${newCategoryId}`, {})); }
  deletePost(postId:number){ return firstValueFrom(this.http.delete(`${BASE}/forum/posts/${postId}`)); }

  // ---- Vote Sites ----
  listVoteSites(include_disabled=true){ return firstValueFrom(this.http.get<any[]>(`${BASE}/vote/sites?include_disabled=${include_disabled}`)); }
  createVoteSite(data:{ name:string; url:string; image_url?:string; cooldown_minutes:number; points_reward:number; position?:number; }){ return firstValueFrom(this.http.post(`${BASE}/vote/sites`, data)); }
  updateVoteSite(id:number, data:Partial<{ name:string; url:string; image_url:string; cooldown_minutes:number; points_reward:number; position:number; is_enabled:boolean; }>){ return firstValueFrom(this.http.patch(`${BASE}/vote/sites/${id}`, data)); }
  deleteVoteSite(id:number){ return firstValueFrom(this.http.delete(`${BASE}/vote/sites/${id}`)); }
  clickVoteSite(id:number){ return firstValueFrom(this.http.post(`${BASE}/vote/sites/${id}/click`, {})); }
}