import { Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { environment } from '../environments';

export interface ArenaTeam {
  id: number;
  name: string;
  captainGuid: number;
  type: number; // 2,3,5
  rating: number;
  seasonGames: number;
  seasonWins: number;
  seasonWinRatio: number;
  weekGames: number;
  weekWins: number;
  weekWinRatio: number;
  rank: number;
}

export interface ArenaRealmLadders {
  realm_id: number;
  name: string;
  status: string; // ok/offline/no_connection_info
  teams: {
    '2v2': ArenaTeam[];
    '3v3': ArenaTeam[];
    '5v5': ArenaTeam[];
  };
}

@Injectable({ providedIn: 'root' })
export class ArenaService {
  private realmsSig = signal<ArenaRealmLadders[]>([]);
  loading = signal(false);
  error = signal<string | null>(null);

  constructor(private http: HttpClient) {}

  realms(){ return this.realmsSig(); }

  async fetch(){
    if(this.loading()) return; // evita spam
    this.loading.set(true);
    this.error.set(null);
    try {
      const data: any = await firstValueFrom(this.http.get(environment.apiBase + '/arena_top'));
      this.realmsSig.set(data?.realms || []);
    } catch(e: any){
      this.error.set(e?.message || 'Error cargando arena');
    } finally {
      this.loading.set(false);
    }
  }
}
