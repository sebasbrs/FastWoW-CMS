import { Component, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { ProfileService, ProfileCharacter } from './profile.service';
import { iconRaceGender, iconClass, labelClass, labelRaceGender } from '../pvp/pvp-icons';

@Component({
  standalone: true,
  selector: 'fw-profile',
  imports: [CommonModule],
  template: `
  <div class="profile-wrapper" *ngIf="!loading; else loadTpl">
    <h1>Perfil</h1>
    <p class="error" *ngIf="error">{{ error }}</p>

    <ng-container *ngIf="profile() as p; else emptyTpl">
      <div class="user-block">
        <div class="avatar-box">
          <img class="avatar" [src]="p.gravatar" alt="avatar" />
        </div>
        <div class="info">
          <h2 class="username">{{ p.username }}</h2>
          <p class="email-status" [class.missing]="!p.has_email">Email {{ p.has_email ? 'verificado' : 'no proporcionado' }}</p>
        </div>
      </div>

      <div class="chars-section" *ngIf="p.characters?.length; else noChars">
        <h3>Personajes ({{ p.characters.length }})</h3>
        <table class="chars">
          <thead>
            <tr>
              <th>Realm</th>
              <th>Avatar</th>
              <th>Nombre</th>
              <th>Raza/Clase/Género</th>
              <th>Lvl</th>
            </tr>
          </thead>
          <tbody>
            <tr *ngFor="let c of p.characters" (click)="openArmory(c)" class="row-link">
              <td>{{ c.realm_name }}</td>
              <td><img class="char-avatar" [src]="charAvatar(c)" [title]="charTitle(c)" /></td>
              <td class="cname">{{ c.name }}</td>
              <td>{{ raceGender(c) }} / {{ className(c.class) }}</td>
              <td>{{ c.level }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <ng-template #noChars><p class="muted">Sin personajes aún.</p></ng-template>
    </ng-container>
  </div>
  <ng-template #loadTpl><p class="muted">Cargando perfil...</p></ng-template>
  <ng-template #emptyTpl><p class="muted">Perfil no encontrado.</p></ng-template>
  `,
  styles: [`
    .profile-wrapper { max-width:1000px; }
    h1 { margin:.2rem 0 1rem; }
    .user-block { display:flex; gap:1rem; padding:.8rem 1rem; background:#222b32; border:1px solid #2f3941; border-radius:4px; margin-bottom:1.5rem; }
    .avatar-box { width:96px; }
    img.avatar { width:96px; height:96px; border-radius:6px; }
    .username { margin:0 0 .3rem; }
    .email-status { font-size:.75rem; color:#90a0ad; }
    .email-status.missing { color:#c66; }
    table.chars { width:100%; border-collapse:collapse; font-size:.8rem; }
    table.chars th, table.chars td { padding:.5rem .6rem; border-bottom:1px solid #283037; }
    table.chars th { font-size:.65rem; text-transform:uppercase; letter-spacing:.5px; color:#88939d; }
    tr:hover td { background:#202830; }
    .cname { font-weight:600; }
    img.char-avatar { width:48px; height:48px; image-rendering:pixelated; }
    .muted { color:#8a949d; }
    .error { color:#d05050; }
    .row-link { cursor:pointer; }
  `]
})
export class ProfileComponent {
  constructor(private route: ActivatedRoute, private router: Router, private svc: ProfileService){
    const username = this.route.snapshot.paramMap.get('username');
    if(username) this.svc.fetch(username);
  }

  get loading(){ return this.svc.loading(); }
  get error(){ return this.svc.error(); }
  profile = computed(() => this.svc.data());

  charAvatar(c: ProfileCharacter){
    // formato images/avatars/{race}-{class}-{gender}.gif
    return `images/avatars/${c.race}-${c.class}-${c.gender}.gif`;
  }
  charTitle(c: ProfileCharacter){
    return `${c.name} - ${labelRaceGender(c.race,c.gender)} ${labelClass(c.class)}`;
  }
  raceGender(c: ProfileCharacter){ return labelRaceGender(c.race, c.gender); }
  className(cls:number){ return labelClass(cls); }

  openArmory(c: ProfileCharacter){
    // placeholder futuro: navegar a /armory/realmId/characterName
    // this.router.navigate(['/armory', c.realm_id, c.name]);
  }
}
