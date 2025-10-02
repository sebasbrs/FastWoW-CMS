import { Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { environment } from '../environments';

export interface ArenaTeamMember {
  guid: number;
  name: string;
  race: number;
  class: number;
  gender?: number; // agregado: backend no lo retorna actualmente; se puede extender si se añade
  level: number;
  seasonGames: number;
  seasonWins: number;
  seasonWinRatio: number;
  weekGames: number;
  weekWins: number;
  weekWinRatio: number;
  personalRating: number;
}

export interface ArenaTeamDetailRawRealm {
  realm_id: number;
  name: string;
  status: string; // ok/offline/not_found/no_connection_info
  team: any | null;
  members: ArenaTeamMember[];
}

@Injectable({ providedIn: 'root' })
export class ArenaTeamService {
  loading = signal(false);
  error = signal<string | null>(null);
  data = signal<ArenaTeamDetailRawRealm[] | null>(null);

  constructor(private http: HttpClient) {}

  async fetch(teamId: number){
    this.loading.set(true);
    this.error.set(null);
    try {
      const raw: any = await firstValueFrom(this.http.get(environment.apiBase + '/arena_team/' + teamId));
      this.data.set(raw?.realms || []);
    } catch(e: any){
      this.error.set(e?.message || 'Error cargando equipo');
    } finally {
      this.loading.set(false);
    }
  }
}
