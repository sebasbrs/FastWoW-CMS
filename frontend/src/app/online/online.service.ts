import { Injectable, signal } from '@angular/core';
import { environment } from '../environments';

export interface OnlineCharacter {
  guid:number; name:string; race:number; class:number; gender:number; level:number; guild?:string; faction:number;
}
export interface OnlineRealm {
  realm_id:number; name:string; status:string; pagination:{page:number;page_size:number;total:number}; characters:OnlineCharacter[];
}

const API = environment.apiBase + '/online';

@Injectable({ providedIn:'root' })
export class OnlineService {
  realms = signal<OnlineRealm[] | null>(null);
  loading = signal(false);

  async fetch(page=1, pageSize=50){
    this.loading.set(true);
    try {
      const url = API + `?page=${page}&page_size=${pageSize}`;
      const data = await fetch(url).then(r => r.json());
      this.realms.set(data?.realms || []);
    } finally { this.loading.set(false); }
  }
}
