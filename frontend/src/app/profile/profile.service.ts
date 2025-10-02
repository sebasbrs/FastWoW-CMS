import { Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { environment } from '../environments';

export interface ProfileCharacter {
  realm_id: number;
  realm_name: string;
  name: string;
  level: number;
  race: number;
  class: number;
  gender: number;
}

export interface UserProfile {
  username: string;
  gravatar: string;
  avatar_fallback: string;
  has_email: boolean;
  characters: ProfileCharacter[];
}

@Injectable({ providedIn: 'root' })
export class ProfileService {
  loading = signal(false);
  error = signal<string | null>(null);
  data = signal<UserProfile | null>(null);

  constructor(private http: HttpClient) {}

  async fetch(username: string){
    this.loading.set(true);
    this.error.set(null);
    try {
      const profile = await firstValueFrom(this.http.get<UserProfile>(environment.apiBase + '/profile/' + encodeURIComponent(username)));
      this.data.set(profile);
    } catch(e: any){
      this.error.set(e?.message || 'Error cargando perfil');
    } finally {
      this.loading.set(false);
    }
  }
}
