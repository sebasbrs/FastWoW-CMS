import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';

interface ForumCategory { id:number; name:string; description:string; topics:number; }
interface Topic { id:number; title:string; author:string; replies:number; updated:string; }

@Component({
  standalone:true,
  selector:'fw-forum',
  imports:[CommonModule],
  template:`
  <div class="forum">
    <ng-container *ngIf="!viewingCategory(); else categoryView">
      <h1>Foro</h1>
      <div class="cat-list">
        <div class="cat" *ngFor="let c of categories()" (click)="openCategory(c)">
          <div class="head">
            <h3>{{ c.name }}</h3>
            <span class="badge">{{ c.topics }} temas</span>
          </div>
          <p class="desc">{{ c.description }}</p>
        </div>
      </div>
    </ng-container>
    <ng-template #categoryView>
      <button class="back" (click)="viewingCategory.set(null)">← Volver</button>
      <h2>{{ viewingCategory()?.name }}</h2>
      <p class="muted">Temas</p>
      <table class="topics">
        <thead><tr><th>Título</th><th>Autor</th><th>Respuestas</th><th>Actualizado</th></tr></thead>
        <tbody>
          <tr *ngFor="let t of topics()">
            <td>{{ t.title }}</td>
            <td>{{ t.author }}</td>
            <td>{{ t.replies }}</td>
            <td>{{ t.updated }}</td>
          </tr>
        </tbody>
      </table>
    </ng-template>
  </div>
  `,
  styles:[`
    .forum { max-width:1000px; }
    .cat-list { display:grid; gap:1rem; grid-template-columns:repeat(auto-fill,minmax(260px,1fr)); }
    .cat { background:#1d2127; border:1px solid #2a313a; padding:.9rem 1rem 1rem; border-radius:10px; cursor:pointer; transition:background .15s,border-color .15s; }
    .cat:hover { background:#232a31; border-color:#36414d; }
    .head { display:flex; align-items:center; justify-content:space-between; }
    h3 { margin:.1rem 0 .4rem; font-size:1rem; }
    .badge { background:#2d3640; color:#b3c4d4; font-size:.65rem; padding:.25rem .5rem; border-radius:20px; }
    .desc { margin:0; font-size:.75rem; line-height:1.1rem; color:#cfd5dc; }
    .back { background:none; border:none; color:#8fb5ff; cursor:pointer; padding:0; margin:0 0 .5rem; }
    table.topics { width:100%; border-collapse:collapse; font-size:.8rem; }
    table.topics th, table.topics td { padding:.5rem .6rem; border-bottom:1px solid #283037; text-align:left; }
    table.topics th { font-size:.65rem; letter-spacing:.5px; text-transform:uppercase; color:#88939d; }
    tr:hover td { background:#202830; }
    .muted { color:#8a949d; font-size:.7rem; text-transform:uppercase; letter-spacing:.5px; margin:.4rem 0 1rem; }
  `]
})
export class ForumComponent {
  categories = signal<ForumCategory[]>([
    { id:1, name:'General', description:'Discusión general sobre el servidor.', topics:42 },
    { id:2, name:'Soporte', description:'Ayuda técnica y reportes.', topics:15 },
    { id:3, name:'Eventos', description:'Anuncios y participación en eventos.', topics:8 }
  ]);
  viewingCategory = signal<ForumCategory | null>(null);
  topics = signal<Topic[]>([]);

  openCategory(c:ForumCategory){
    this.viewingCategory.set(c);
    // mock topics
    this.topics.set([
      { id:1, title:'Bienvenidos', author:'Staff', replies:5, updated:'2025-10-01' },
      { id:2, title:'Reglas del foro', author:'Moderador', replies:2, updated:'2025-10-02' },
      { id:3, title:'Sugerencias', author:'JugadorX', replies:12, updated:'2025-10-02' }
    ]);
  }
}
