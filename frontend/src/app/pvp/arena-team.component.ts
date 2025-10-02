import { Component, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute } from '@angular/router';
import { ArenaTeamService, ArenaTeamMember, ArenaTeamDetailRawRealm } from './arena-team.service';
import { iconRaceGender, labelRaceGender, iconClass, labelClass } from './pvp-icons';

@Component({
  standalone: true,
  selector: 'fw-arena-team',
  imports: [CommonModule],
  template: `
  <div class="team-wrapper" *ngIf="!loading; else loadTpl">
    <h1>Equipo Arena</h1>
    <p class="error" *ngIf="error">{{ error }}</p>

    <ng-container *ngIf="realms().length; else emptyTpl">
      <div class="realm-team" *ngFor="let r of realms()">
        <h2>{{ r.name }} <small *ngIf="r.status!=='ok'" class="status">({{ r.status }})</small></h2>
        <div *ngIf="r.team; else notFound">
          <div class="team-head">
            <div class="meta">
              <div class="tname">{{ r.team.name }} <span class="bracket">[{{ bracketLabel(r.team.type) }}]</span></div>
              <div class="rating">Rating: <strong>{{ r.team.rating }}</strong> (Rank {{ r.team.rank }})</div>
              <div class="season">Season: {{ r.team.seasonWins }}/{{ r.team.seasonGames }} ({{ (r.team.seasonWinRatio*100) | number:'1.0-2' }}%)</div>
              <div class="week">Week: {{ r.team.weekWins }}/{{ r.team.weekGames }} ({{ (r.team.weekWinRatio*100) | number:'1.0-2' }}%)</div>
            </div>
          </div>
          <table class="members">
            <thead>
              <tr>
                <th>Nombre</th>
                <th>Raza/Género</th>
                <th>Clase</th>
                <th>Lvl</th>
                <th>Season (W/L)</th>
                <th>Season %</th>
                <th>Week (W/L)</th>
                <th>Week %</th>
                <th>Personal</th>
              </tr>
            </thead>
            <tbody>
              <tr *ngFor="let m of r.members">
                <td class="name">{{ m.name }}</td>
                <td><img class="avatar" [src]="raceGender(m.race,m.gender)" [title]="raceGenderTitle(m)" /></td>
                <td><img class="class" [src]="classIcon(m.class)" [title]="classTitle(m.class)" /></td>
                <td>{{ m.level }}</td>
                <td>{{ m.seasonWins }}/{{ m.seasonGames }}</td>
                <td>{{ (m.seasonWinRatio*100) | number:'1.0-1' }}%</td>
                <td>{{ m.weekWins }}/{{ m.weekGames }}</td>
                <td>{{ (m.weekWinRatio*100) | number:'1.0-1' }}%</td>
                <td>{{ m.personalRating }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <ng-template #notFound>
          <p class="muted">Equipo no encontrado / offline.</p>
        </ng-template>
      </div>
    </ng-container>
  </div>
  <ng-template #loadTpl><p class="muted">Cargando equipo...</p></ng-template>
  <ng-template #emptyTpl><p class="muted">Sin datos.</p></ng-template>
  `,
  styles: [`
    .team-wrapper { max-width:900px; }
    h1 { margin:.2rem 0 1rem; }
    h2 { margin:1.2rem 0 .6rem; font-size:1.05rem; }
    h2 .status { font-size:.7rem; color:#88939d; }
    .team-head { margin-bottom:1rem; padding:.6rem .8rem; background:#222b32; border:1px solid #2f3941; }
    .tname { font-weight:600; font-size:1rem; }
    .bracket { color:#c5cdd4; font-size:.7rem; margin-left:.4rem; }
    table.members { width:100%; border-collapse:collapse; font-size:.75rem; }
    table.members th, table.members td { padding:.45rem .55rem; border-bottom:1px solid #283037; }
    table.members th { font-size:.6rem; text-transform:uppercase; letter-spacing:.5px; color:#88939d; }
    tr:hover td { background:#202830; }
    img.avatar { width:32px; height:32px; image-rendering:pixelated; }
    img.class { width:24px; height:24px; }
    .name { font-weight:600; }
    .muted { color:#8a949d; }
    .error { color:#d05050; }
  `]
})
export class ArenaTeamComponent {
  constructor(private route: ActivatedRoute, private svc: ArenaTeamService){
    const id = Number(this.route.snapshot.paramMap.get('teamId'));
    if(id) this.svc.fetch(id);
  }

  get loading(){ return this.svc.loading(); }
  get error(){ return this.svc.error(); }
  realms = computed(() => this.svc.data() || []);

  bracketLabel(t:number){
    if(t===2) return '2v2'; if(t===3) return '3v3'; if(t===5) return '5v5'; return '?';
  }

  raceGender(r:number,g:number|undefined){ return iconRaceGender(r, g ?? 0); }
  raceGenderTitle(m:any){ return labelRaceGender(m.race, m.gender ?? 0); }
  classIcon(c:number){ return iconClass(c); }
  classTitle(c:number){ return labelClass(c); }
}
