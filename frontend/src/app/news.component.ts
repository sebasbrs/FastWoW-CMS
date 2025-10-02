import { Component, signal, effect } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { NewsService, NewsItem, NewsComment } from './news.service';
import { AuthService } from './auth.service';

@Component({
  standalone:true,
  selector:'fw-news',
  imports:[CommonModule, FormsModule],
  template:`
  <div class="news-wrapper">
    <h1>Noticias</h1>
    <div class="list" *ngIf="!current()">
      <div class="loading" *ngIf="loading()">Cargando...</div>
      <div class="grid" *ngIf="!loading()">
        <article *ngFor="let n of items()" class="card" (click)="open(n)">
          <h3>{{ n.title }}</h3>
          <p class="meta">{{ n.author }} • {{ formatDate(n.published_at || n.created_at) }}</p>
          <p class="excerpt" *ngIf="n.summary; else noSummary">{{ n.summary }}</p>
          <ng-template #noSummary><p class="excerpt">{{ (n.content||'') | slice:0:140 }}...</p></ng-template>
          <p class="comments-count" *ngIf="n.comments_count">💬 {{ n.comments_count }}</p>
        </article>
      </div>
      <div class="pager" *ngIf="pagination().total > pagination().page_size">
        <button (click)="prevPage()" [disabled]="pagination().page===1">«</button>
        <span>Página {{ pagination().page }} / {{ totalPages() }}</span>
        <button (click)="nextPage()" [disabled]="pagination().page===totalPages()">»</button>
      </div>
    </div>

    <div class="detail" *ngIf="current() as c">
      <button class="back" (click)="closeDetail()">← Volver</button>
      <h2>{{ c.title }}</h2>
      <p class="meta">{{ c.author }} • {{ formatDate(c.published_at || c.created_at) }}</p>
      <div class="body" [innerHTML]="renderContent(c.content)"></div>
      <section class="comments">
        <h3>Comentarios ({{ comments().length }})</h3>
        <div class="comment" *ngFor="let cm of comments()">
          <div class="c-head">
            <span class="c-author">{{ cm.author }}</span>
            <span class="c-date">{{ formatDate(cm.created_at) }}</span>
          </div>
            <div class="c-body">{{ cm.content }}</div>
        </div>
        <div *ngIf="isLogged()" class="comment-form">
          <textarea [(ngModel)]="newComment" rows="3" placeholder="Escribe un comentario..." ></textarea>
          <div class="c-actions">
            <button (click)="submitComment()" [disabled]="commentLoading() || !newComment.trim()">{{ commentLoading() ? 'Enviando...' : 'Comentar' }}</button>
          </div>
          <p class="c-error" *ngIf="commentError()">{{ commentError() }}</p>
        </div>
        <div *ngIf="!isLogged()" class="login-hint">Debes iniciar sesión para comentar.</div>
      </section>
    </div>
  </div>
  `,
  styles:[`
    .news-wrapper { max-width:980px; }
    .grid { display:grid; gap:1rem; grid-template-columns:repeat(auto-fill,minmax(250px,1fr)); }
    .card { background:#1d2127; border:1px solid #2a313a; padding:.85rem 1rem 1rem; border-radius:10px; cursor:pointer; transition:background .15s,border-color .15s; position:relative; }
    .card:hover { background:#232a31; border-color:#36414d; }
    h3 { margin:.1rem 0 .4rem; font-size:1.05rem; }
    .meta { margin:0 0 .4rem; font-size:.6rem; letter-spacing:.5px; text-transform:uppercase; color:#7d8a96; }
    .excerpt { margin:0; font-size:.8rem; line-height:1.15rem; color:#cfd5dc; }
    .comments-count { position:absolute; top:.5rem; right:.6rem; font-size:.65rem; color:#9fb2c3; }
    .loading { padding:1rem 0; color:#9da8b5; }
    .pager { margin:1.2rem 0 .4rem; display:flex; gap:.8rem; align-items:center; font-size:.8rem; }
    .pager button { background:#262f3a; border:1px solid #394552; padding:.3rem .7rem; border-radius:4px; cursor:pointer; color:#cfd8e0; }
    .detail { margin-top:1.5rem; background:#1a2026; border:1px solid #273039; padding:1.1rem 1.25rem 1.4rem; border-radius:12px; }
    .detail h2 { margin:.2rem 0 .6rem; }
    .back { background:none; border:none; color:#8fb5ff; cursor:pointer; padding:0; margin:0 0 .65rem; font-size:.85rem; }
    .body { white-space:pre-line; line-height:1.3rem; font-size:.9rem; }
    .comments { margin-top:1.5rem; }
    .comments h3 { margin:0 0 .8rem; font-size:1rem; }
    .comment { border-top:1px solid #2a333c; padding:.55rem 0 .6rem; }
    .comment:first-of-type { border-top:none; }
    .c-head { display:flex; gap:.6rem; font-size:.65rem; letter-spacing:.5px; text-transform:uppercase; color:#6f7c88; }
    .c-body { font-size:.8rem; line-height:1.15rem; color:#d2d9df; margin-top:.25rem; white-space:pre-line; }
    .comment-form { margin-top:1rem; display:flex; flex-direction:column; gap:.5rem; }
    textarea { resize:vertical; background:#1f252b; border:1px solid #2d3741; padding:.55rem .6rem; color:#e4ebf3; font-family:inherit; border-radius:6px; font-size:.8rem; }
    textarea:focus { outline:none; border-color:#4d6fff; }
    .c-actions { display:flex; justify-content:flex-end; }
    .c-actions button { background:linear-gradient(90deg,#4e65ff,#914dff); border:none; padding:.45rem .95rem; cursor:pointer; border-radius:5px; color:#fff; font-size:.75rem; font-weight:600; }
    .login-hint { margin-top:.5rem; font-size:.7rem; color:#8897a3; }
    .c-error { color:#ff6d6d; font-size:.7rem; margin:0; }
    @media (max-width:700px){ .grid { grid-template-columns:repeat(auto-fill,minmax(180px,1fr)); } }
  `]
})
export class NewsComponent {
  items = signal<NewsItem[]>([]);
  pagination = signal({ page:1, page_size:10, total:0 });
  loading = signal(false);
  current = signal<NewsItem | null>(null);
  comments = signal<NewsComment[]>([]);
  commentLoading = signal(false);
  commentError = signal('');
  newComment = '';

  constructor(private api: NewsService, private auth: AuthService){
    this.load();
  }

  isLogged = () => this.auth.isLogged();

  totalPages(){ return Math.max(1, Math.ceil(this.pagination().total / this.pagination().page_size)); }

  async load(page=this.pagination().page){
    this.loading.set(true);
    try {
      const res = await this.api.list(page, this.pagination().page_size);
      this.items.set(res.items);
      this.pagination.set(res.pagination);
    } catch(e:any){
      // could add error signal
    } finally { this.loading.set(false); }
  }

  formatDate(dt?:string|null){ if(!dt) return ''; return dt.split('T')[0]; }
  renderContent(html:string){ return (html||'').replace(/\n/g,'<br/>'); }

  async open(n:NewsItem){
    try {
      const full = await this.api.get(n.slug || String(n.id));
      this.current.set(full);
      // comments vienen dentro (full.comments) ya, pero permitimos recarga futura
      this.comments.set(full.comments || []);
    } catch(e:any){ /* manejar error */ }
  }
  closeDetail(){ this.current.set(null); }
  prevPage(){ if(this.pagination().page>1){ this.pagination.update(p=>({...p,page:p.page-1})); this.load(); } }
  nextPage(){ if(this.pagination().page<this.totalPages()){ this.pagination.update(p=>({...p,page:p.page+1})); this.load(); } }

  async submitComment(){
    if(!this.current() || !this.newComment.trim()) return;
    this.commentError.set('');
    this.commentLoading.set(true);
    try {
      const res:any = await this.api.addComment(this.current()!.id, this.newComment.trim());
      // prepend nuevo comentario
      this.comments.update(list => [res, ...list]);
      // limpiar
      this.newComment = '';
      // actualizar contador local
      this.current.update(c => c ? { ...c, comments_count: (c.comments_count||0)+1 } : c);
    } catch(e:any){
      this.commentError.set(e?.error?.detail || 'Error al comentar');
    } finally { this.commentLoading.set(false); }
  }
}
