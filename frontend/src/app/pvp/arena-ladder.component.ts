import { Component, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { ArenaService, ArenaRealmLadders, ArenaTeam } from './arena.service';

@Component({
  standalone: true,
  selector: 'fw-arena-ladder',
  imports: [CommonModule],
  template: `
  <div class="arena-wrapper" *ngIf="!loading; else loadTpl">
    <h1>Arena Ladder</h1>
    <p class="error" *ngIf="error">{{ error }}</p>

    <div class="tab-bar">
      <button *ngFor="let t of brackets" (click)="activeBracket.set(t)" [class.active]="activeBracket()==t">{{ t }}</button>
    </div>

    <ng-container *ngIf="realms().length; else emptyTpl">
      <div class="realm-block" *ngFor="let realm of realms()">
        <h2>{{ realm.name }}</h2>
        <table class="ladder">
          <thead>
            <tr>
              <th>#</th>
              <th>Equipo</th>
              <th>Rating</th>
              <th>Rank</th>
              <th>Season (W/L)</th>
              <th>Season Win %</th>
              <th>Week (W/L)</th>
              <th>Week Win %</th>
            </tr>
          </thead>
          <tbody>
            <tr *ngFor="let team of teamsFor(realm); index as i" (click)="openTeam(team)" class="row-link">
              <td>{{ i+1 }}</td>
              <td class="name">{{ team.name }}</td>
              <td>{{ team.rating }}</td>
              <td>{{ team.rank }}</td>
              <td>{{ team.seasonWins }}/{{ team.seasonGames }}</td>
              <td>{{ (team.seasonWinRatio*100) | number:'1.0-2' }}%</td>
              <td>{{ team.weekWins }}/{{ team.weekGames }}</td>
              <td>{{ (team.weekWinRatio*100) | number:'1.0-2' }}%</td>
            </tr>
          </tbody>
        </table>
      </div>
    </ng-container>
  </div>
  <ng-template #loadTpl><p class="muted">Cargando ladder...</p></ng-template>
  <ng-template #emptyTpl><p class="muted">Sin datos de arena.</p></ng-template>
  `,
  styles: [`
    .arena-wrapper { max-width:1100px; }
    h1 { margin:.2rem 0 1rem; }
    h2 { margin:1.2rem 0 .6rem; font-size:1.1rem; }
    .tab-bar { display:flex; gap:.5rem; margin-bottom:1rem; }
    .tab-bar button { background:#222b32; border:1px solid #2f3941; padding:.4rem .8rem; cursor:pointer; color:#cbd2d7; font-size:.75rem; letter-spacing:.5px; text-transform:uppercase; }
    .tab-bar button.active { background:#2f3941; color:#fff; box-shadow:0 0 0 1px #3d4952 inset; }
    table.ladder { width:100%; border-collapse:collapse; font-size:.75rem; }
    table.ladder th, table.ladder td { padding:.45rem .55rem; border-bottom:1px solid #283037; }
    table.ladder th { font-size:.6rem; text-transform:uppercase; letter-spacing:.5px; color:#88939d; }
    tr:hover td { background:#202830; }
    .name { font-weight:600; }
    .muted { color:#8a949d; }
    .error { color:#d05050; }
  `]
})
export class ArenaLadderComponent {
  brackets: Array<'2v2'|'3v3'|'5v5'> = ['2v2','3v3','5v5'];
  activeBracket = signal<'2v2'|'3v3'|'5v5'>('2v2');

  constructor(private arena: ArenaService, private router: Router){
    if(!this.arena.realms().length) this.arena.fetch();
  }

  get loading(){ return this.arena.loading(); }
  get error(){ return this.arena.error(); }
  realms = computed(() => this.arena.realms());

  teamsFor(realm: ArenaRealmLadders){
    const b = this.activeBracket();
    return realm.teams[b] || [];
  }

  openTeam(team: ArenaTeam){
    this.router.navigate(['/pvp/arena/team', team.id]);
  }
}
