import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AuthService } from './auth.service';

@Component({
  standalone: true,
  selector: 'fw-change-email',
  imports: [CommonModule, FormsModule],
  template: `
  <div class="card">
    <h2>Cambiar email</h2>
    <form (ngSubmit)="submit()" *ngIf="!done()">
      <div class="field">
        <label>Nuevo email</label>
        <input type="email" [(ngModel)]="email" name="email" required />
      </div>
      <div class="actions">
        <button [disabled]="loading()">Guardar</button>
      </div>
      <p class="error" *ngIf="error()">{{error()}}</p>
    </form>
    <div *ngIf="done()" class="success">Email actualizado.</div>
  </div>
  `,
  styles: [`
    .card { max-width:420px; margin:1rem auto; padding:1rem; background:#1d2228; border:1px solid #333; border-radius:6px; }
    label { display:block; font-weight:600; margin-bottom:2px; }
    input { width:100%; padding:6px 8px; margin-bottom:8px; background:#111; color:#eee; border:1px solid #333; border-radius:4px; }
    .error { color:#ff6666; }
    .success { color:#59d98c; }
  `]
})
export class ChangeEmailComponent {
  email = '';
  loading = signal(false);
  error = signal('');
  done = signal(false);
  constructor(private auth: AuthService){}
  async submit(){
    this.error.set('');
    if (!this.email) return;
    this.loading.set(true);
    try {
      await this.auth.changeEmail(this.email);
      this.done.set(true);
    } catch(e:any){
      this.error.set(e?.error?.detail || 'Error cambiando email');
    } finally { this.loading.set(false); }
  }
}
