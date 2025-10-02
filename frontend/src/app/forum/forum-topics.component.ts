import { Component, signal, computed, Input, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ForumService, ForumTopic } from './forum.service';

@Component({
  standalone:true,
  selector:'fw-forum-topics',
  imports:[CommonModule],
  template:`
  <div class="topics-view" *ngIf="categoryId; else pick">
    <div class="toolbar">
      <button (click)="goBack()" class="link">← Categorías</button>
      <h2>Temas</h2>
    </div>
    <table class="topics">
      <thead><tr><th>Título</th><th>Autor</th><th>Posts</th><th>Último</th></tr></thead>
      <tbody>
        <tr *ngFor="let t of topics()" (click)="openTopic(t)">
          <td><span class="pin" *ngIf="t.is_pinned">📌</span>{{ t.title }}</td>
          <td>{{ t.author_username }}</td>
          <td>{{ t.posts_count }}</td>
          <td>{{ t.last_post_at || t.created_at }}</td>
        </tr>
      </tbody>
    </table>
    <div class="pager" *ngIf="pagination() as p">
      <button (click)="changePage(p.page-1)" [disabled]="p.page<=1">«</button>
      <span>{{ p.page }} / {{ totalPages() }}</span>
      <button (click)="changePage(p.page+1)" [disabled]="p.page>= totalPages()">»</button>
    </div>
  </div>
  <ng-template #pick><p class="muted">Selecciona una categoría...</p></ng-template>
  `,
  styles:[`
    .topics-view { max-width:1000px; }
    table { width:100%; border-collapse:collapse; font-size:.8rem; }
    th, td { padding:.55rem .6rem; border-bottom:1px solid #283037; text-align:left; }
    th { font-size:.65rem; text-transform:uppercase; letter-spacing:.5px; color:#88939d; }
    tr { cursor:pointer; }
    tr:hover td { background:#202830; }
    .toolbar { display:flex; align-items:center; gap:1rem; margin-bottom:.75rem; }
    .link { background:none; border:none; color:#8fb5ff; padding:0; cursor:pointer; }
    .pager { margin-top:.7rem; display:flex; gap:.5rem; align-items:center; }
    .pager button { background:#1f262d; border:1px solid #2b353f; color:#d0d5da; padding:.3rem .6rem; border-radius:4px; cursor:pointer; }
    .pager button:disabled { opacity:.4; cursor:default; }
    .pin { margin-right:.3rem; }
    .muted { color:#8a949d; }
  `]
})
export class ForumTopicsComponent implements OnChanges {
  @Input() categoryId!: number | null;
  topics = signal<ForumTopic[]>([]);
  pagination = signal<{page:number; page_size:number; total:number} | null>(null);
  loading = signal(false);

  constructor(private forum: ForumService){}

  async load(page=1){
    if(!this.categoryId) return;
    this.loading.set(true);
    try {
      const data = await this.forum.fetchTopics(this.categoryId, page);
      this.topics.set(data.items);
      this.pagination.set(data.pagination);
    } finally { this.loading.set(false); }
  }

  ngOnChanges(ch:SimpleChanges){
    if(ch['categoryId'] && this.categoryId){
      this.load(1);
    }
  }

  totalPages(){
    const p = this.pagination();
    if(!p) return 1;
    return Math.max(1, Math.ceil(p.total / p.page_size));
  }

  changePage(p:number){
    const total = this.totalPages();
    if(p<1 || p>total) return;
    this.load(p);
  }

  goBack(){
    this.categoryId = null;
    this.topics.set([]);
    this.pagination.set(null);
  }

  openTopic(t:ForumTopic){
    // TODO: navigate to topic detail component
  }
}
