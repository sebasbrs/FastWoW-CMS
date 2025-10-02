import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from './auth.service';

@Component({
  standalone: true,
  selector: 'fw-login',
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
  <div class="login-wrapper">
    <h1>Iniciar sesión</h1>
    <form (submit)="submit(); $event.preventDefault();" class="card" novalidate>
      <div class="field">
        <label>Usuario</label>
        <input name="username" [(ngModel)]="form.username" required autofocus />
      </div>
      <div class="field">
        <label>Contraseña</label>
        <input name="password" type="password" [(ngModel)]="form.password" required />
      </div>
      <div class="actions">
        <button type="submit" [disabled]="loading()">{{ loading() ? 'Entrando...' : 'Entrar' }}</button>
        <a class="alt" routerLink="/register">Crear cuenta</a>
      </div>
      <p class="small-links">
        <a routerLink="/auth/password-recovery">¿Olvidaste tu contraseña?</a>
      </p>
      <p class="msg error" *ngIf="error()">{{error()}}</p>
    </form>
  </div>
  `,
  styles:[`
    .login-wrapper { max-width:420px; margin:0 auto; }
    form.card { background:#1d2127; padding:1.25rem 1.35rem 1.4rem; border:1px solid #2a313a; border-radius:10px; display:flex; flex-direction:column; gap:1rem; }
    .field { display:flex; flex-direction:column; gap:.35rem; }
    label { font-size:.75rem; text-transform:uppercase; letter-spacing:.7px; color:#a8b4c2; font-weight:600; }
    input { background:#262c34; border:1px solid #333b46; border-radius:6px; padding:.55rem .7rem; color:#e8ecf1; font-size:.9rem; }
    input:focus { outline:none; border-color:#546dff; background:#2d343e; }
    button { background:linear-gradient(90deg,#546dff,#874bff); border:none; color:#fff; padding:.6rem 1rem; border-radius:6px; cursor:pointer; font-size:.9rem; font-weight:600; }
    button[disabled]{ opacity:.55; }
    .actions { display:flex; align-items:center; gap:.75rem; }
    .alt { font-size:.75rem; color:#8ea2b5; }
    .small-links { margin:0; font-size:.7rem; }
    .small-links a { color:#8397ff; }
    .msg.error { color:#ff6d6d; font-size:.8rem; margin:0; }
  `]
})
export class LoginComponent {
  form = { username: '', password: '' };
  loading = signal(false);
  error = signal('');
  constructor(private auth: AuthService, private router: Router){}
  async submit(){
    if(this.loading()) return;
    this.error.set('');
    if(!this.form.username || !this.form.password){
      this.error.set('Completa usuario y contraseña');
      return;
    }
    this.loading.set(true);
    try {
      await this.auth.login(this.form.username.trim(), this.form.password);
      this.router.navigate(['/profile', this.auth.user()?.username || '']);
    } catch(e:any){
      this.error.set(e?.error?.detail || 'Credenciales inválidas');
    } finally { this.loading.set(false); }
  }
}
