import { Component, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { OnlineService, OnlineCharacter, OnlineRealm } from './online.service';

@Component({
  standalone:true,
  selector:'fw-online',
  imports:[CommonModule],
  template:`
  <div class="online-wrapper" *ngIf="!loading; else loadTpl">
    <h1>Jugadores Online</h1>
    <ng-container *ngIf="realms().length; else emptyTpl">
      <div *ngFor="let r of realms()" class="realm-block">
        <h2>{{ r.name }} <small class="count">({{ r.pagination.total }})</small></h2>
        <table class="chars">
          <thead>
            <tr>
              <th>Fac</th>
              <th>Nombre</th>
              <th>Raza/Género</th>
              <th>Clase</th>
              <th>Lvl</th>
              <th>Guild</th>
            </tr>
          </thead>
          <tbody>
            <tr *ngFor="let c of r.characters">
              <td><img class="faction" [src]="factionIcon(c.faction)" [title]="factionLabel(c.faction)" /></td>
              <td class="name">{{ c.name }}</td>
              <td><img class="avatar" [src]="raceGenderImg(c.race,c.gender)" [title]="raceGenderTitle(c)" /></td>
              <td><img class="class" [src]="classImg(c.class)" [title]="classLabel(c.class)" /></td>
              <td>{{ c.level }}</td>
              <td>{{ c.guild || '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </ng-container>
  </div>
  <ng-template #loadTpl><p class="muted">Cargando...</p></ng-template>
  <ng-template #emptyTpl><p class="muted">No hay jugadores online.</p></ng-template>
  `,
  styles:[`
    .online-wrapper { max-width:1100px; }
    h1 { margin:.2rem 0 1rem; }
    .realm-block { margin-bottom:2rem; }
    h2 { margin:1.2rem 0 .6rem; font-size:1.2rem; }
    h2 .count { font-size:.8rem; color:#8a939c; }
    table.chars { width:100%; border-collapse:collapse; font-size:.8rem; }
    table.chars th, table.chars td { padding:.45rem .55rem; border-bottom:1px solid #283037; }
    table.chars th { font-size:.65rem; text-transform:uppercase; letter-spacing:.5px; color:#88939d; }
    img.faction { width:20px; height:20px; }
    img.avatar { width:32px; height:32px; image-rendering:pixelated; }
    img.class { width:24px; height:24px; }
    tr:hover td { background:#202830; }
    .name { font-weight:600; }
    .muted { color:#8a949d; }
  `]
})
export class OnlineComponent {
  constructor(private onlineService: OnlineService){
    if(!this.onlineService.realms()) this.onlineService.fetch();
  }

  get loading(){ return this.onlineService.loading(); }
  realms = computed(() => this.onlineService.realms() || []);

  factionIcon(f:number){
    if(f === 1) return 'images/faction/2.png'; // horde? en backend definiste 1 horde? revisar mapping
    if(f === 2) return 'images/faction/1.png';
    return 'images/faction/neutral.png';
  }
  factionLabel(f:number){
    if(f === 1) return 'Horda';
    if(f === 2) return 'Alianza';
    return 'Neutral';
  }

  raceGenderImg(race:number, gender:number){
    // formato: race-gender.gif (ej: 1-0.gif)
    return `images/race/${race}-${gender}.gif`;
  }
  raceGenderTitle(c:OnlineCharacter){
    return `Raza ${c.race} - ${c.gender === 0 ? 'Hombre' : 'Mujer'}`;
  }

  classImg(cls:number){
    return `images/class/${cls}.gif`;
  }
  classLabel(cls:number){
    const map:Record<number,string> = {1:'Warrior',2:'Paladin',3:'Hunter',4:'Rogue',5:'Priest',6:'DK',7:'Shaman',8:'Mage',9:'Warlock',10:'Monk',11:'Druid',12:'DH'};
    return map[cls] || 'Clase';
  }
}
