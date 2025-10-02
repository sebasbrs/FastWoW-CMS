import { Component, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';

interface NewsItem { id:number; title:string; body:string; created:string; author:string; }

@Component({
  standalone:true,
  selector:'fw-news',
  imports:[CommonModule],
  template:`
  <div class="news-list">
    <h1>Noticias</h1>
    <div class="grid">
      <article *ngFor="let n of items()" class="card" (click)="select(n)">
        <h3>{{ n.title }}</h3>
        <p class="meta">{{ n.author }} • {{ n.created }}</p>
        <p class="excerpt">{{ n.body | slice:0:140 }}...</p>
      </article>
    </div>

    <div class="detail" *ngIf="current() as c">
      <button class="back" (click)="current.set(null)">← Volver</button>
      <h2>{{ c.title }}</h2>
      <p class="meta">{{ c.author }} • {{ c.created }}</p>
      <p class="full">{{ c.body }}</p>
    </div>
  </div>
  `,
  styles:[`
    .news-list { max-width:960px; }
    .grid { display:grid; gap:1rem; grid-template-columns:repeat(auto-fill,minmax(240px,1fr)); }
    .card { background:#1d2127; border:1px solid #2a313a; padding:.85rem 1rem 1rem; border-radius:8px; cursor:pointer; transition:background .15s,border-color .15s; }
    .card:hover { background:#232a31; border-color:#36414d; }
    h3 { margin:.1rem 0 .4rem; font-size:1.05rem; }
    .meta { margin:0 0 .4rem; font-size:.65rem; letter-spacing:.5px; text-transform:uppercase; color:#7d8a96; }
    .excerpt { margin:0; font-size:.8rem; line-height:1.15rem; color:#cfd5dc; }
    .detail { margin-top:1.5rem; background:#1a2026; border:1px solid #273039; padding:1rem 1.2rem 1.3rem; border-radius:10px; }
    .detail h2 { margin:.2rem 0 .6rem; }
    .detail .full { white-space:pre-line; line-height:1.25rem; }
    .back { background:none; border:none; color:#8fb5ff; cursor:pointer; padding:0; margin:0 0 .5rem; }
  `]
})
export class NewsComponent {
  items = signal<NewsItem[]>([
    { id:1, title:'Lanzamiento del Realms', body:'Contenido simulado de la noticia 1 con más texto para ver como se visualiza.', created:'2025-10-01', author:'GM' },
    { id:2, title:'Nuevo Evento', body:'Detalles del evento de temporada. Participa para ganar recompensas exclusivas.', created:'2025-10-02', author:'Staff' },
    { id:3, title:'Notas de Parche', body:'Lista de cambios y arreglos aplicados en el parche reciente.', created:'2025-10-02', author:'Dev Team' }
  ]);
  current = signal<NewsItem | null>(null);

  select(n:NewsItem){ this.current.set(n); }
}
