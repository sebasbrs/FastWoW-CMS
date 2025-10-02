import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AuthService } from './auth.service';

@Component({
  standalone: true,
  selector: 'fw-password-recovery-request',
  imports: [CommonModule, FormsModule],
  template: `
  <div class="card">
    <h2>Recuperar contraseña</h2>
    <form (ngSubmit)="submit()" *ngIf="!sent()">
      <div class="field">
        <label>Usuario</label>
        <input [(ngModel)]="username" name="username" required />
      </div>
      <div class="actions"><button [disabled]="loading()">Solicitar</button></div>
      <p class="hint">Se enviará (si corresponde) un token al email registrado. No se indicará si el usuario existe.</p>
      <p class="error" *ngIf="error()">{{error()}}</p>
    </form>
    <div *ngIf="sent()" class="success">
      Si el usuario existe y tiene email, se envió un token. Revisa tu correo y continúa con el formulario de restablecer.
    </div>
  </div>
  `,
  styles:[`
    .card { max-width:460px; margin:1rem auto; padding:1rem; background:#1d2228; border:1px solid #333; border-radius:6px; }
    .hint { font-size:0.8rem; color:#888; }
    input { width:100%; padding:6px 8px; margin-bottom:8px; background:#111; color:#eee; border:1px solid #333; border-radius:4px; }
    .error { color:#ff6666; }
    .success { color:#59d98c; }
  `]
})
export class PasswordRecoveryRequestComponent {
  username = '';
  loading = signal(false);
  error = signal('');
  sent = signal(false);
  constructor(private auth: AuthService){}
  async submit(){
    this.error.set('');
    if (!this.username) return;
    this.loading.set(true);
    try {
      await this.auth.requestPasswordRecovery(this.username);
      this.sent.set(true);
    } catch(e:any){
      this.error.set(e?.error?.detail || 'Error solicitando recuperación');
    } finally { this.loading.set(false); }
  }
}
