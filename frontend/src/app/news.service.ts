import { Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { environment } from './environments';

export interface NewsListResponse { items: NewsItem[]; pagination: { page:number; page_size:number; total:number }; }
export interface NewsItem {
  id:number; title:string; slug:string; summary?:string; content:string; realm_id?:number|null; author:string; is_published:boolean; published_at?:string|null; created_at?:string|null; updated_at?:string|null; priority?:number; comments?:NewsComment[]; comments_count?:number;
}
export interface NewsComment { id:number; author:string; content:string; created_at:string; }

const BASE = environment.apiBase + '/news';

@Injectable({ providedIn:'root' })
export class NewsService {
  loading = signal(false);
  lastError = signal<string|undefined>(undefined);

  constructor(private http: HttpClient){}

  async list(page=1, page_size=10){
    this.lastError.set(undefined);
    const res = await firstValueFrom(this.http.get<NewsListResponse>(`${BASE}?page=${page}&page_size=${page_size}`));
    return res;
  }

  async get(idOrSlug: string){
    this.lastError.set(undefined);
    return await firstValueFrom(this.http.get<NewsItem>(`${BASE}/${idOrSlug}`));
  }

  async addComment(newsId: number, content: string){
    this.lastError.set(undefined);
    return await firstValueFrom(this.http.post(`${BASE}/${newsId}/comments`, { content }));
  }

  async listComments(newsId: number, page=1, page_size=30){
    this.lastError.set(undefined);
    return await firstValueFrom(this.http.get<{ items:NewsComment[]; pagination:any }>(`${BASE}/${newsId}/comments?page=${page}&page_size=${page_size}`));
  }
}
