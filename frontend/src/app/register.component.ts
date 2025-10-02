import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AuthService } from './auth.service';
import { Router } from '@angular/router';

@Component({
  standalone: true,
  selector: 'fw-register',
  imports: [CommonModule, FormsModule],
  template: `
  <div class="register-wrapper">
    <h1>Crear cuenta</h1>
    <p class="subtitle">Completa el formulario para comenzar a jugar.</p>
    <form (submit)="submit(); $event.preventDefault();" class="card">
      <div class="field">
        <label>Usuario</label>
        <input type="text" name="username" [(ngModel)]="form.username" required minlength="3" />
      </div>
      <div class="field">
        <label>Email (opcional)</label>
        <input type="email" name="email" [(ngModel)]="form.email" />
      </div>
      <div class="field">
        <label>Contraseña</label>
        <input type="password" name="password" [(ngModel)]="form.password" required minlength="4" />
      </div>
      <div class="actions">
        <button type="submit" [disabled]="loading()">{{ loading() ? 'Creando...' : 'Registrarse' }}</button>
      </div>
      <p class="msg ok" *ngIf="done()">Cuenta creada, iniciando sesión...</p>
      <p class="msg error" *ngIf="error()">{{ error() }}</p>
    </form>
  </div>
  `,
  styles: [`
    .register-wrapper { max-width:460px; margin:0 auto; }
    h1 { margin:.2rem 0 .4rem; font-size:1.9rem; }
    .subtitle { margin:0 0 1.2rem; color:#888; }
    form.card { background:#1d2127; padding:1.25rem 1.35rem 1.6rem; border:1px solid #2a313a; border-radius:10px; display:flex; flex-direction:column; gap:1rem; }
    .field { display:flex; flex-direction:column; gap:.35rem; }
    label { font-size:.75rem; text-transform:uppercase; letter-spacing:.7px; color:#a8b4c2; font-weight:600; }
    input { background:#262c34; border:1px solid #333b46; border-radius:6px; padding:.55rem .7rem; color:#e8ecf1; font-size:.9rem; font-family:inherit; outline:none; transition:border-color .15s, background .15s; }
    input:focus { border-color:#546dff; background:#2d343e; }
    button { background:linear-gradient(90deg,#546dff,#874bff); border:none; color:#fff; padding:.65rem 1.1rem; border-radius:6px; cursor:pointer; font-size:.9rem; font-weight:600; letter-spacing:.5px; }
    button[disabled] { opacity:.55; cursor:default; }
    .actions { display:flex; justify-content:flex-end; }
    .msg { font-size:.8rem; margin:0; }
    .msg.ok { color:#4fc287; }
    .msg.error { color:#f06262; }
    @media (max-width:600px){ .register-wrapper { padding:0 .5rem; } }
  `]
})
export class RegisterComponent {
  form = { username: '', email: '', password: '' };
  loading = signal(false);
  error = signal('');
  done = signal(false);

  constructor(private auth: AuthService, private router: Router){}

  async submit(){
    if(this.loading()) return;
    this.error.set('');
    this.done.set(false);
    if(!this.form.username || !this.form.password){
      this.error.set('Completa los campos obligatorios');
      return;
    }
    this.loading.set(true);
    try {
      await this.auth.register(this.form.username.trim(), this.form.password, this.form.email?.trim() || undefined);
      this.done.set(true);
      setTimeout(()=> this.router.navigate(['/profile']), 800);
    } catch (e:any) {
      const detail = e?.error?.detail || e?.message || 'Error registrando';
      this.error.set(detail);
    } finally {
      this.loading.set(false);
    }
  }
}
