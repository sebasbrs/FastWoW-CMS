import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AuthService } from './auth.service';

@Component({
  standalone: true,
  selector: 'fw-email-verification-request',
  imports: [CommonModule, FormsModule],
  template: `
  <div class="card">
    <h2>Verificar email</h2>
    <form (ngSubmit)="submit()" *ngIf="!sent()">
      <div class="field"><label>Usuario</label><input [(ngModel)]="username" name="username" required /></div>
      <div class="actions"><button [disabled]="loading()">Solicitar token</button></div>
      <p class="hint">Se enviará un token al email registrado (si existe).</p>
      <p class="error" *ngIf="error()">{{error()}}</p>
    </form>
    <div *ngIf="sent()" class="success">Si el email existe se envió un token. Continúa con la confirmación.</div>
  </div>
  `,
  styles:[`
    .card { max-width:460px; margin:1rem auto; padding:1rem; background:#1d2228; border:1px solid #333; border-radius:6px; }
    input { width:100%; padding:6px 8px; margin-bottom:8px; background:#111; color:#eee; border:1px solid #333; border-radius:4px; }
    .hint { font-size:0.8rem; color:#888; }
    .error { color:#ff6666; }
    .success { color:#59d98c; }
  `]
})
export class EmailVerificationRequestComponent {
  username=''; loading = signal(false); error = signal(''); sent = signal(false);
  constructor(private auth: AuthService){}
  async submit(){
    this.error.set('');
    if (!this.username) return;
    this.loading.set(true);
    try {
      await this.auth.requestEmailVerification(this.username);
      this.sent.set(true);
    } catch(e:any){
      this.error.set(e?.error?.detail || 'Error solicitando verificación');
    } finally { this.loading.set(false); }
  }
}
