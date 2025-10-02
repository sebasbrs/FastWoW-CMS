import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AuthService } from './auth.service';

@Component({
  standalone: true,
  selector: 'fw-change-password',
  imports: [CommonModule, FormsModule],
  template: `
  <div class="card">
    <h2>Cambiar contraseña</h2>
    <form (ngSubmit)="submit()" *ngIf="!done()">
      <div class="field">
        <label>Contraseña actual</label>
        <input type="password" [(ngModel)]="current" name="current" required />
      </div>
      <div class="field">
        <label>Nueva contraseña</label>
        <input type="password" [(ngModel)]="next" name="next" required minlength="4" />
      </div>
      <div class="actions">
        <button [disabled]="loading()">Guardar</button>
      </div>
      <p class="error" *ngIf="error()">{{error()}}</p>
    </form>
    <div *ngIf="done()" class="success">Contraseña cambiada correctamente.</div>
  </div>
  `,
  styles: [`
    .card { max-width:420px; margin:1rem auto; padding:1rem; background:#1d2228; border:1px solid #333; border-radius:6px; }
    label { display:block; font-weight:600; margin-bottom:2px; }
    input { width:100%; padding:6px 8px; margin-bottom:8px; background:#111; color:#eee; border:1px solid #333; border-radius:4px; }
    button { padding:6px 14px; }
    .error { color:#ff6666; }
    .success { color:#59d98c; }
  `]
})
export class ChangePasswordComponent {
  current = '';
  next = '';
  loading = signal(false);
  error = signal('');
  done = signal(false);
  constructor(private auth: AuthService){}
  async submit(){
    this.error.set('');
    if (!this.current || !this.next) return;
    this.loading.set(true);
    try {
      await this.auth.changePassword(this.current, this.next);
      this.done.set(true);
      this.current=''; this.next='';
    } catch(e:any){
      this.error.set(e?.error?.detail || 'Error cambiando contraseña');
    } finally { this.loading.set(false); }
  }
}
