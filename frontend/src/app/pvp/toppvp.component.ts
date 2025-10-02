import { Component, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TopPvpService, TopPvpRealm, TopPvpPlayer } from './toppvp.service';
import { iconFaction, labelFaction, iconRaceGender, labelRaceGender, iconClass, labelClass } from './pvp-icons';

@Component({
  standalone: true,
  selector: 'fw-top-pvp',
  imports: [CommonModule],
  template: `
  <div class="top-pvp-wrapper" *ngIf="!loading; else loadTpl">
    <h1>Top PvP (Total Kills)</h1>
    <p class="error" *ngIf="error">{{ error }}</p>

    <ng-container *ngIf="realms().length; else emptyTpl">
      <div class="realm-block" *ngFor="let realm of realms()">
        <h2>{{ realm.name }} <small *ngIf="realm.players.length" class="count">({{ realm.players.length }})</small></h2>
        <table class="rank">
          <thead>
            <tr>
              <th>#</th>
              <th>Fac</th>
              <th>Nombre</th>
              <th>Raza/Género</th>
              <th>Clase</th>
              <th>Lvl</th>
              <th>Kills</th>
              <th>Guild</th>
            </tr>
          </thead>
          <tbody>
            <tr *ngFor="let p of realm.players; index as i">
              <td>{{ i + 1 }}</td>
              <td><img class="faction" [src]="factionIcon(p.faction)" [title]="factionLabel(p.faction)" /></td>
              <td class="name">{{ p.name }}</td>
              <td><img class="avatar" [src]="raceGenderImg(p.race,p.gender)" [title]="raceGenderTitle(p)" /></td>
              <td><img class="class" [src]="classImg(p.class)" [title]="classLabel(p.class)" /></td>
              <td>{{ p.level }}</td>
              <td class="kills">{{ p.totalkill }}</td>
              <td>{{ p.guild || '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </ng-container>
  </div>
  <ng-template #loadTpl><p class="muted">Cargando Top PvP...</p></ng-template>
  <ng-template #emptyTpl><p class="muted">Sin datos de PvP.</p></ng-template>
  `,
  styles: [`
    .top-pvp-wrapper { max-width:1100px; }
    h1 { margin:.2rem 0 1rem; }
    h2 { margin:1.2rem 0 .6rem; font-size:1.2rem; }
    h2 .count { font-size:.75rem; color:#88939d; }
    table.rank { width:100%; border-collapse:collapse; font-size:.8rem; }
    table.rank th, table.rank td { padding:.45rem .55rem; border-bottom:1px solid #283037; }
    table.rank th { font-size:.65rem; text-transform:uppercase; letter-spacing:.5px; color:#88939d; }
    tr:hover td { background:#202830; }
    img.faction { width:20px; height:20px; }
    img.avatar { width:32px; height:32px; image-rendering:pixelated; }
    img.class { width:24px; height:24px; }
    .name { font-weight:600; }
    .kills { font-weight:600; color:#d9ae54; }
    .muted { color:#8a949d; }
    .error { color:#d05050; margin-bottom:.6rem; }
  `]
})
export class TopPvpComponent {
  constructor(private svc: TopPvpService){
    if(!this.svc.realms().length) this.svc.fetch(100);
  }

  get loading(){ return this.svc.loading(); }
  get error(){ return this.svc.error(); }
  realms = computed(() => this.svc.realms());

  factionIcon = iconFaction;
  factionLabel = labelFaction;
  raceGenderImg = iconRaceGender;
  raceGenderTitle(p:TopPvpPlayer){ return labelRaceGender(p.race, p.gender); }
  classImg = iconClass;
  classLabel = labelClass;
}
