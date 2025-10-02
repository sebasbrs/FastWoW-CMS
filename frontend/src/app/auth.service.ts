import { Injectable, signal, computed, effect } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { environment } from './environments';

interface LoginResponse { access_token: string; token_type: string; }
interface UserMe { username: string; credits: number; vote_points: number; gravatar: string; }

const TOKEN_KEY = 'fw_token';
const API_BASE = environment.apiBase + '/auth';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private _user = signal<UserMe | null>(null);
  user = computed(() => this._user());
  isLogged = computed(() => !!this._user());

  constructor(private http: HttpClient){
    const token = localStorage.getItem(TOKEN_KEY);
    if (token) this.refreshMe().catch(()=> this.logout());
    // efecto debug (removible)
    effect(() => {
      if (this._user()) {
        // console.log('Usuario cargado', this._user());
      }
    });
  }

  async login(username: string, password: string){
    const res = await firstValueFrom(this.http.post<LoginResponse>(`${API_BASE}/login`, { username, password }));
    if (res?.access_token){
      localStorage.setItem(TOKEN_KEY, res.access_token);
      await this.refreshMe();
    }
    return res;
  }

  async register(username: string, password: string, email?: string){
    await firstValueFrom(this.http.post(`${API_BASE}/register`, { username, password, email }));
    await this.login(username, password);
  }

  async refreshMe(){
    const me = await firstValueFrom(this.http.get<UserMe>(`${API_BASE}/me`));
    this._user.set(me || null);
    return me;
  }

  logout(){
    localStorage.removeItem(TOKEN_KEY);
    this._user.set(null);
  }
}
