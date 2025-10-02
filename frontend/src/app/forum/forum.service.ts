import { Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../environments';

export interface ForumCategory { id:number; name:string; description:string; position:number; }
export interface ForumTopic { id:number; title:string; author_username:string; created_at:string; updated_at:string; last_post_at:string; posts_count:number; is_locked:number; is_pinned:number; }
export interface ForumTopicsResponse { items:ForumTopic[]; pagination:{ page:number; page_size:number; total:number; }; }
export interface ForumPost { id:number; topic_id:number; author_username:string; content:string; created_at:string; }

const API = environment.apiBase + '/forum';

@Injectable({ providedIn:'root' })
export class ForumService {
  categories = signal<ForumCategory[] | null>(null);
  loadingCategories = signal(false);

  constructor(private http: HttpClient){}

  async fetchCategories(){
    this.loadingCategories.set(true);
    try {
      const data = await this.http.get(API + '/categories').toPromise();
      this.categories.set(data as any);
    } finally { this.loadingCategories.set(false); }
  }

  async fetchTopics(categoryId:number, page=1):Promise<ForumTopicsResponse>{
    const url = `${API}/categories/${categoryId}/topics?page=${page}`;
    return this.http.get<ForumTopicsResponse>(url).toPromise() as any;
  }

  async fetchTopic(topicId:number):Promise<any>{
    return this.http.get(`${API}/topics/${topicId}`).toPromise();
  }

  async createTopic(categoryId:number, title:string, content:string){
    return this.http.post(`${API}/categories/${categoryId}/topics`, { title, content }).toPromise();
  }

  async createPost(topicId:number, content:string){
    return this.http.post(`${API}/topics/${topicId}/posts`, { content }).toPromise();
  }
}
