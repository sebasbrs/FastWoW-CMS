import { Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { environment } from '../environments';

export interface TopPvpPlayer {
  guid: number;
  name: string;
  race: number;
  class: number;
  gender: number;
  level: number;
  guild?: string;
  totalkill: number;
  faction: number; // 1 horda, 2 alianza, 0 desconocido (igual que online)
}

export interface TopPvpRealm {
  realm_id: number;
  name: string;
  status: string; // online/offline/no_connection_info
  players: TopPvpPlayer[];
}

@Injectable({ providedIn: 'root' })
export class TopPvpService {
  private realmsSig = signal<TopPvpRealm[]>([]);
  loading = signal(false);
  error = signal<string | null>(null);

  constructor(private http: HttpClient) {}

  realms() { return this.realmsSig(); }

  async fetch(limit = 100){
    this.loading.set(true);
    this.error.set(null);
    try {
  const data: any = await firstValueFrom(this.http.get(environment.apiBase + '/top_pvp', { params: { limit } }));
      this.realmsSig.set(data?.realms || []);
    } catch (e: any) {
      this.error.set(e?.message || 'Error cargando top PvP');
    } finally {
      this.loading.set(false);
    }
  }
}
