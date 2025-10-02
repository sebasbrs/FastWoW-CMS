import { Injectable, signal, computed, effect } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { environment } from './environments';

interface LoginResponse { access_token: string; token_type: string; }
interface UserMe { username: string; credits: number; vote_points: number; gravatar: string; role?: number; }

const TOKEN_KEY = 'fw_token';
const API_BASE = environment.apiBase + '/auth';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private _user = signal<UserMe | null>(null);
  user = computed(() => this._user());
  isLogged = computed(() => !!this._user());
  isAdmin = computed(() => (this._user()?.role || 1) >= 2);

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

  // ---- Endpoints adicionales ----
  async changePassword(current_password: string, new_password: string){
    return await firstValueFrom(this.http.post(`${API_BASE}/change_password`, { current_password, new_password }));
  }

  async changeEmail(new_email: string){
    return await firstValueFrom(this.http.post(`${API_BASE}/change_email`, { new_email }));
  }

  async requestPasswordRecovery(username: string){
    return await firstValueFrom(this.http.post(`${API_BASE}/password_recovery/request`, { username }));
  }

  async confirmPasswordRecovery(username: string, token: string, new_password: string){
    return await firstValueFrom(this.http.post(`${API_BASE}/password_recovery/confirm`, { username, token, new_password }));
  }

  async requestEmailVerification(username: string){
    return await firstValueFrom(this.http.post(`${API_BASE}/email_verification/request`, { username }));
  }

  async confirmEmailVerification(username: string, token: string){
    return await firstValueFrom(this.http.post(`${API_BASE}/email_verification/confirm`, { username, token }));
  }
}
