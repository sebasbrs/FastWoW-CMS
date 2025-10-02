import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AuthService } from './auth.service';

@Component({
  standalone: true,
  selector: 'fw-email-verification-confirm',
  imports: [CommonModule, FormsModule],
  template: `
  <div class="card">
    <h2>Confirmar verificación email</h2>
    <form (ngSubmit)="submit()" *ngIf="!done()">
      <div class="field"><label>Usuario</label><input [(ngModel)]="username" name="username" required /></div>
      <div class="field"><label>Token</label><input [(ngModel)]="token" name="token" required /></div>
      <div class="actions"><button [disabled]="loading()">Verificar</button></div>
      <p class="error" *ngIf="error()">{{error()}}</p>
    </form>
    <div *ngIf="done()" class="success">Email verificado.</div>
  </div>
  `,
  styles:[`
    .card { max-width:460px; margin:1rem auto; padding:1rem; background:#1d2228; border:1px solid #333; border-radius:6px; }
    input { width:100%; padding:6px 8px; margin-bottom:8px; background:#111; color:#eee; border:1px solid #333; border-radius:4px; }
    .error { color:#ff6666; }
    .success { color:#59d98c; }
  `]
})
export class EmailVerificationConfirmComponent {
  username=''; token=''; loading = signal(false); error = signal(''); done = signal(false);
  constructor(private auth: AuthService){}
  async submit(){
    this.error.set('');
    if (!this.username || !this.token) return;
    this.loading.set(true);
    try {
      await this.auth.confirmEmailVerification(this.username, this.token);
      this.done.set(true);
    } catch(e:any){
      this.error.set(e?.error?.detail || 'Error verificando');
    } finally { this.loading.set(false); }
  }
}
