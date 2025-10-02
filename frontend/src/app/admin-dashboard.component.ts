import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AuthService } from './auth.service';
import { HttpClient } from '@angular/common/http';
import { environment } from './environments';
import { AdminService } from './admin.service';

interface StatBox { label:string; value:number|string; loading?:boolean; }

@Component({
  standalone:true,
  selector:'fw-admin-dashboard',
  imports:[CommonModule, FormsModule],
  template:`
  <div class="admin-wrapper">
    <h1>Dashboard Admin</h1>
    <nav class="admin-tabs">
      <button *ngFor="let t of tabs" (click)="activeTab=t.key" [class.active]="activeTab===t.key">{{ t.label }}</button>
    </nav>

    <!-- OVERVIEW -->
    <div *ngIf="activeTab==='overview'">
      <div class="stats-grid">
        <div class="stat" *ngFor="let s of stats()">
          <div class="label">{{ s.label }}</div>
          <div class="value" [class.loading]="s.loading">{{ s.loading ? '...' : s.value }}</div>
        </div>
      </div>
      <section class="panels">
        <div class="panel">
          <h2>Últimas Noticias</h2>
          <ul class="mini-list">
            <li *ngFor="let n of news()">{{ n.title }} <span class="meta">#{{ n.id }} · {{ n.author }}</span></li>
            <li *ngIf="!news().length && !loadingNews()" class="empty">Sin noticias</li>
            <li *ngIf="loadingNews()" class="loading">Cargando...</li>
          </ul>
        </div>
        <div class="panel">
          <h2>Últimos Usuarios</h2>
            <ul class="mini-list">
              <li *ngFor="let u of users()">{{ u.username }} <span class="meta">CR {{ u.credits }}</span></li>
              <li *ngIf="!users().length && !loadingUsers()" class="empty">Sin datos</li>
              <li *ngIf="loadingUsers()" class="loading">Cargando...</li>
            </ul>
        </div>
      </section>
    </div>

    <!-- NEWS MANAGEMENT -->
    <section class="news-mgmt" *ngIf="activeTab==='news'">
      <div class="flex-row">
        <div class="panel grow">
          <h2>Noticias <small *ngIf="newsPagination.total">({{ newsPagination.total }})</small></h2>
          <div class="toolbar">
            <button (click)="refreshAdminNews()" [disabled]="newsLoading()">Recargar</button>
            <button (click)="startCreateNews()">Nueva</button>
          </div>
          <table class="table">
            <thead><tr><th>ID</th><th>Título</th><th>Autor</th><th>Pub</th><th>Prioridad</th><th>Fecha</th><th></th></tr></thead>
            <tbody>
              <tr *ngFor="let n of adminNews()" [class.unpub]="!n.is_published" (click)="editNews(n); $event.stopPropagation();">
                <td>{{ n.id }}</td>
                <td>{{ n.title }}</td>
                <td>{{ n.author }}</td>
                <td>{{ n.is_published ? '✔' : '—' }}</td>
                <td>{{ n.priority }}</td>
                <td>{{ formatDate(n.created_at) }}</td>
                <td><button (click)="togglePublish(n); $event.stopPropagation();">{{ n.is_published ? 'Ocultar' : 'Publicar' }}</button></td>
              </tr>
              <tr *ngIf="!adminNews().length && !newsLoading()"><td colspan="7" class="empty">Sin noticias</td></tr>
              <tr *ngIf="newsLoading()"><td colspan="7">Cargando...</td></tr>
            </tbody>
          </table>
          <div class="pager" *ngIf="newsPagination.total > newsPagination.page_size">
            <button (click)="changeNewsPage(newsPagination.page-1)" [disabled]="newsPagination.page===1">«</button>
            <span>{{ newsPagination.page }} / {{ newsTotalPages() }}</span>
            <button (click)="changeNewsPage(newsPagination.page+1)" [disabled]="newsPagination.page===newsTotalPages()">»</button>
          </div>
        </div>
        <div class="panel side" *ngIf="editingNews()">
          <h2>{{ editingNews()?.id ? 'Editar' : 'Crear' }} Noticia</h2>
          <form (ngSubmit)="saveNews(); $event.preventDefault();" class="news-form">
            <label>Título<input [(ngModel)]="newsForm.title" name="title" required /></label>
            <label>Resumen<textarea rows="2" [(ngModel)]="newsForm.summary" name="summary"></textarea></label>
            <label>Contenido<textarea rows="8" [(ngModel)]="newsForm.content" name="content" required></textarea></label>
            <label>Prioridad<input type="number" [(ngModel)]="newsForm.priority" name="priority" /></label>
            <label class="chk"><input type="checkbox" [(ngModel)]="newsForm.publish" name="publish"/> Publicar</label>
            <div class="actions"><button type="submit" [disabled]="savingNews()">{{ savingNews() ? 'Guardando...' : 'Guardar' }}</button><button type="button" (click)="cancelNewsEdit()">Cancelar</button></div>
            <p class="err" *ngIf="newsError()">{{ newsError() }}</p>
          </form>
        </div>
      </div>
      <div class="panel" *ngIf="selectedNewsComments().length">
        <h3>Comentarios ({{ selectedNewsComments().length }})</h3>
        <div class="comment-row" *ngFor="let c of selectedNewsComments()">
          <div class="c-meta">{{ c.author }} • {{ formatDate(c.created_at) }}</div>
            <div class="c-body">{{ c.content }}</div>
          <button class="danger" (click)="deleteComment(c)">Eliminar</button>
        </div>
      </div>
    </section>

    <!-- FORUM MANAGEMENT -->
    <section class="forum-mgmt" *ngIf="activeTab==='forum'">
      <div class="flex-row">
        <div class="panel grow">
          <h2>Categorías</h2>
          <div class="toolbar"><button (click)="startCreateCategory()">Nueva categoría</button></div>
          <ul class="cat-list">
            <li *ngFor="let c of forumCategories()" (click)="selectCategory(c)" [class.active]="selectedCategory()?.id===c.id">{{ c.name }} <span class="meta">#{{ c.id }}</span></li>
            <li *ngIf="!forumCategories().length" class="empty">Sin categorías</li>
          </ul>
        </div>
        <div class="panel side" *ngIf="editingCategory()">
          <h2>{{ editingCategory()?.id ? 'Editar' : 'Crear' }} Categoría</h2>
          <form (ngSubmit)="saveCategory(); $event.preventDefault();" class="cat-form">
            <label>Nombre<input [(ngModel)]="categoryForm.name" name="cname" required /></label>
            <label>Descripción<textarea rows="2" [(ngModel)]="categoryForm.description" name="cdesc"></textarea></label>
            <label>Posición<input type="number" [(ngModel)]="categoryForm.position" name="cpos" /></label>
            <div class="actions"><button type="submit" [disabled]="savingCategory()">{{ savingCategory() ? 'Guardando...' : 'Guardar' }}</button><button type="button" (click)="cancelCategoryEdit()">Cancelar</button></div>
            <p class="err" *ngIf="categoryError()">{{ categoryError() }}</p>
          </form>
        </div>
        <div class="panel grow" *ngIf="selectedCategory()">
          <h2>Temas en {{ selectedCategory()?.name }}</h2>
          <div class="toolbar">
            <button (click)="startCreateTopic()" [disabled]="!selectedCategory()">Nuevo tema</button>
            <button (click)="refreshTopics()" [disabled]="!selectedCategory()">Refrescar</button>
          </div>
          <table class="table" *ngIf="forumTopics().length">
            <thead><tr><th>ID</th><th>Título</th><th>Autor</th><th>Posts</th><th>Lock</th><th>Pin</th><th></th></tr></thead>
            <tbody>
              <tr *ngFor="let t of forumTopics()">
                <td>{{ t.id }}</td><td>{{ t.title }}</td><td>{{ t.author_username }}</td><td>{{ t.posts_count }}</td><td>{{ t.is_locked? '🔒':'' }}</td><td>{{ t.is_pinned? '📌':'' }}</td>
                <td class="actions-cell">
                  <button (click)="toggleLock(t); $event.stopPropagation();">{{ t.is_locked? 'Unlock':'Lock' }}</button>
                  <button (click)="togglePin(t); $event.stopPropagation();">{{ t.is_pinned? 'Unpin':'Pin' }}</button>
                  <button (click)="deleteTopic(t); $event.stopPropagation();" class="danger">Del</button>
                </td>
              </tr>
            </tbody>
          </table>
          <p class="empty" *ngIf="!forumTopics().length">Sin temas</p>
        </div>
        <div class="panel side" *ngIf="editingTopic()">
          <h2>Nuevo Tema</h2>
          <form (ngSubmit)="saveTopic(); $event.preventDefault();" class="topic-form">
            <label>Título<input [(ngModel)]="topicForm.title" name="ttitle" required /></label>
            <label>Contenido<textarea rows="6" [(ngModel)]="topicForm.content" name="tcontent" required></textarea></label>
            <div class="actions"><button type="submit" [disabled]="savingTopic()">{{ savingTopic()? 'Creando...':'Crear' }}</button><button type="button" (click)="cancelTopicEdit()">Cancelar</button></div>
            <p class="err" *ngIf="topicError()">{{ topicError() }}</p>
          </form>
        </div>
      </div>
    </section>

    <!-- VOTE SITES MANAGEMENT -->
    <section class="votes-mgmt" *ngIf="activeTab==='votes'">
      <div class="flex-row">
        <div class="panel grow">
          <h2>Sitios de Voto</h2>
          <div class="toolbar">
            <button (click)="loadVoteSites()" [disabled]="loadingVoteSites()">Recargar</button>
            <button (click)="startCreateVote()">Nuevo</button>
          </div>
          <table class="table" *ngIf="voteSites().length">
            <thead><tr><th>ID</th><th>Pos</th><th>Nombre</th><th>Cooldown</th><th>Puntos</th><th>Enabled</th><th>Imagen</th><th></th></tr></thead>
            <tbody>
              <tr *ngFor="let v of voteSites()" (click)="editVote(v)">
                <td>{{ v.id }}</td>
                <td>{{ v.position }}</td>
                <td>{{ v.name }}</td>
                <td>{{ v.cooldown_minutes }}m</td>
                <td>{{ v.points_reward }}</td>
                <td>{{ v.is_enabled? '✔':'—' }}</td>
                <td>
                  <img *ngIf="v.image_url" [src]="v.image_url" alt="logo" style="width:46px;height:46px;object-fit:cover;border-radius:4px; border:1px solid #2d3a45;" />
                </td>
                <td class="actions-cell">
                  <button (click)="toggleVoteEnabled(v); $event.stopPropagation();">{{ v.is_enabled? 'Desactivar':'Activar' }}</button>
                  <button class="danger" (click)="deleteVote(v); $event.stopPropagation();">Del</button>
                </td>
              </tr>
            </tbody>
          </table>
          <p class="empty" *ngIf="!voteSites().length && !loadingVoteSites()">Sin sitios</p>
          <p *ngIf="loadingVoteSites()">Cargando...</p>
        </div>
        <div class="panel side" *ngIf="editingVote()">
          <h2>{{ editingVote()?.id ? 'Editar' : 'Crear' }} Sitio</h2>
          <form (ngSubmit)="saveVote(); $event.preventDefault();" class="vote-form">
            <label>Nombre<input [(ngModel)]="voteForm.name" name="vname" required /></label>
            <label>URL<input [(ngModel)]="voteForm.url" name="vurl" required /></label>
            <label>Imagen URL<input [(ngModel)]="voteForm.image_url" name="vimg" placeholder="https://..." /></label>
            <label>Cooldown (min)<input type="number" [(ngModel)]="voteForm.cooldown_minutes" name="vcool" min="1" /></label>
            <label>Recompensa (pts)<input type="number" [(ngModel)]="voteForm.points_reward" name="vpts" min="1" /></label>
            <label>Posición<input type="number" [(ngModel)]="voteForm.position" name="vpos" /></label>
            <label class="chk"><input type="checkbox" [(ngModel)]="voteForm.is_enabled" name="ven" /> Activo</label>
            <div class="actions"><button type="submit" [disabled]="savingVote()">{{ savingVote()? 'Guardando...':'Guardar' }}</button><button type="button" (click)="cancelVoteEdit()">Cancelar</button></div>
            <p class="err" *ngIf="voteError()">{{ voteError() }}</p>
          </form>
          <p class="hint" style="font-size:.6rem; line-height:1.1rem; color:#7a8893;">Las imágenes se muestran 46x46 recortadas (object-fit:cover). Usa mismo tamaño o cuadradas para mejor consistencia.</p>
        </div>
      </div>
    </section>
  </div>
  `,
  styles:[`
    .admin-wrapper { max-width:1300px; }
    h1 { margin:.2rem 0 1rem; }
    .admin-tabs { display:flex; gap:.5rem; margin:0 0 1rem; }
    .admin-tabs button { background:#232b33; border:1px solid #303a45; padding:.45rem .9rem; border-radius:6px; color:#cfd7de; cursor:pointer; font-size:.75rem; }
    .admin-tabs button.active { background:#3a4a5a; border-color:#4d6174; }
    .stats-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(160px,1fr)); gap:1rem; margin-bottom:1.2rem; }
    .stat { background:#1d232a; border:1px solid #2a323c; padding:.75rem .85rem .85rem; border-radius:8px; }
    .stat .label { font-size:.65rem; text-transform:uppercase; letter-spacing:.6px; color:#7f8a95; margin-bottom:.3rem; }
    .stat .value { font-size:1.3rem; font-weight:600; color:#e8edf2; min-height:1.6rem; }
    .stat .value.loading { color:#5d6a75; }
    .panels { display:grid; gap:1rem; grid-template-columns:repeat(auto-fit,minmax(340px,1fr)); }
    .panel { background:#1b2026; border:1px solid #252d35; padding:.9rem 1rem 1.1rem; border-radius:10px; position:relative; }
    .panel h2 { margin:.1rem 0 .8rem; font-size:1rem; }
    .mini-list { list-style:none; margin:0; padding:0; font-size:.8rem; }
    .mini-list li { padding:.35rem 0; border-bottom:1px solid #232b33; display:flex; justify-content:space-between; gap:.6rem; }
    .mini-list li:last-child { border-bottom:none; }
    .mini-list .meta { font-size:.65rem; color:#6f7d89; }
    .mini-list .empty { color:#56626d; font-style:italic; }
    .loading { color:#73808c; }
    /* News / Forum mgmt */
    .flex-row { display:flex; gap:1rem; align-items:flex-start; }
    .panel.side { width:360px; flex:0 0 auto; }
    .panel.grow { flex:1 1 auto; }
    .toolbar { display:flex; gap:.5rem; margin-bottom:.6rem; }
    table.table { width:100%; border-collapse:collapse; font-size:.7rem; }
    table.table th, table.table td { border-bottom:1px solid #263038; padding:.4rem .5rem; text-align:left; }
    table.table th { text-transform:uppercase; letter-spacing:.5px; font-size:.6rem; color:#7b8893; }
    tr.unpub td { opacity:.6; }
    .pager { margin-top:.5rem; display:flex; gap:.5rem; align-items:center; font-size:.7rem; }
    form.news-form, form.cat-form, form.topic-form { display:flex; flex-direction:column; gap:.6rem; }
    form label { display:flex; flex-direction:column; gap:.25rem; font-size:.65rem; text-transform:uppercase; letter-spacing:.5px; color:#8a97a2; }
    input, textarea { background:#1f262c; border:1px solid #2a333c; padding:.5rem .55rem; border-radius:6px; color:#e3e9ef; font-size:.75rem; font-family:inherit; }
    input:focus, textarea:focus { outline:none; border-color:#4d6fff; }
    .chk { flex-direction:row; align-items:center; gap:.4rem; font-size:.65rem; }
    .actions { display:flex; gap:.5rem; }
    .actions button { background:#2f3b47; border:1px solid #3c4a58; color:#d4dde5; padding:.45rem .8rem; border-radius:5px; font-size:.65rem; cursor:pointer; }
    .actions button:hover { background:#374552; }
    .err { color:#ff6d6d; font-size:.65rem; margin:0; }
    .comment-row { border-top:1px solid #24303a; padding:.55rem 0; font-size:.7rem; }
    .comment-row:first-child { border-top:none; }
    .comment-row .c-meta { color:#6e7c88; font-size:.6rem; text-transform:uppercase; letter-spacing:.5px; }
    .comment-row .c-body { margin:.25rem 0 .4rem; white-space:pre-line; }
    .comment-row button.danger { background:#4c2020; border:1px solid #6b2b2b; color:#f2c9c9; }
    .cat-list { list-style:none; margin:0; padding:0; font-size:.7rem; }
    .cat-list li { padding:.4rem .5rem; border:1px solid #26313a; margin:.25rem 0; border-radius:5px; cursor:pointer; display:flex; justify-content:space-between; }
    .cat-list li.active { background:#28333d; border-color:#3b4b58; }
    .cat-list .meta { color:#6e7b87; }
    .empty { color:#66727d; font-style:italic; }
    .actions-cell { display:flex; gap:.4rem; }
    button.danger { background:#512424; border:1px solid #693030; color:#efc9c9; }
  `]
})
export class AdminDashboardComponent {
  tabs = [
    { key:'overview', label:'Resumen' },
    { key:'news', label:'Noticias' },
    { key:'forum', label:'Foro' },
    { key:'votes', label:'Votos' }
  ];
  activeTab = 'overview';
  stats = signal<StatBox[]>([
    { label:'Usuarios', value:0, loading:true },
    { label:'Noticias', value:0, loading:true },
    { label:'Comentarios', value:0, loading:true },
    { label:'Puntos Voto Totales', value:0, loading:true },
    { label:'Créditos Totales', value:0, loading:true },
  ]);
  news = signal<any[]>([]);
  users = signal<any[]>([]);
  loadingNews = signal(true);
  loadingUsers = signal(true);

  private base = environment.apiBase;

  // News admin state
  adminNews = signal<any[]>([]);
  newsPagination = { page:1, page_size:20, total:0 };
  newsLoading = signal(false);
  editingNews = signal<any|null>(null);
  newsForm: any = { title:'', summary:'', content:'', priority:0, publish:false };
  savingNews = signal(false);
  newsError = signal('');
  selectedNewsComments = signal<any[]>([]);

  // Forum admin state
  forumCategories = signal<any[]>([]);
  editingCategory = signal<any|null>(null);
  categoryForm: any = { name:'', description:'', position:0 };
  savingCategory = signal(false);
  categoryError = signal('');
  selectedCategory = signal<any|null>(null);
  forumTopics = signal<any[]>([]);
  editingTopic = signal<boolean>(false);
  topicForm: any = { title:'', content:'' };
  savingTopic = signal(false);
  topicError = signal('');

  // Vote sites state
  voteSites = signal<any[]>([]);
  loadingVoteSites = signal(false);
  editingVote = signal<any|null>(null);
  voteForm: any = { name:'', url:'', image_url:'', cooldown_minutes:720, points_reward:1, position:0, is_enabled:true };
  savingVote = signal(false);
  voteError = signal('');

  constructor(private http: HttpClient, private auth: AuthService, private admin: AdminService){
    this.load();
  }

  private async load(){
    this.loadStats();
    this.loadNews();
    this.loadUsers();
    this.refreshAdminNews();
    this.loadForumCategories();
    this.loadVoteSites();
  }

  private async loadStats(){
    try {
      // Requiere endpoints estadísticos reales (placeholder consultas). Ajustar cuando existan.
      // Temporales: contamos con list_news para total; usuarios: no hay endpoint -> placeholder.
      const newsRes:any = await this.http.get(this.base + '/news?page=1&page_size=1').toPromise();
      const newsTotal = newsRes?.pagination?.total || 0;
      // Placeholder para usuarios: requiere endpoint admin futuro
      const uTotal = 0;
      const cTotal = 0;
      const voteTotal = 0;
      const creditsTotal = 0;
      this.stats.set([
        { label:'Usuarios', value:uTotal },
        { label:'Noticias', value:newsTotal },
        { label:'Comentarios', value:cTotal },
        { label:'Puntos Voto Totales', value:voteTotal },
        { label:'Créditos Totales', value:creditsTotal },
      ]);
    } catch {
      this.stats.update(list => list.map(s => ({ ...s, loading:false })));
    }
  }

  private async loadNews(){
    try {
      const res:any = await this.http.get(this.base + '/news?page=1&page_size=5').toPromise();
      this.news.set(res?.items || []);
    } finally { this.loadingNews.set(false); }
  }

  private async loadUsers(){
    try {
      // No hay endpoint, dejamos vacío hasta implementarlo.
      this.users.set([]);
    } finally { this.loadingUsers.set(false); }
  }

  // Utilidades
  formatDate(d:string){ if(!d) return ''; try { return new Date(d).toLocaleString(); } catch { return d; } }

  // News admin logic
  async refreshAdminNews(){
    this.newsLoading.set(true); this.editingNews.set(null); this.selectedNewsComments.set([]);
    try {
      const res:any = await this.admin.listNews(this.newsPagination.page, this.newsPagination.page_size);
      this.adminNews.set(res.items || []);
      this.newsPagination.total = res.pagination?.total || 0;
    } finally { this.newsLoading.set(false); }
  }
  newsTotalPages(){ return Math.max(1, Math.ceil(this.newsPagination.total / this.newsPagination.page_size)); }
  changeNewsPage(p:number){ if(p<1 || p>this.newsTotalPages()) return; this.newsPagination.page=p; this.refreshAdminNews(); }
  startCreateNews(){ this.editingNews.set({}); this.newsForm = { title:'', summary:'', content:'', priority:0, publish:false }; this.selectedNewsComments.set([]); }
  editNews(n:any){ this.editingNews.set(n); this.newsForm = { title:n.title, summary:n.summary, content:n.content, priority:n.priority, publish:n.is_published }; this.selectedNewsComments.set(n.comments||[]); }
  cancelNewsEdit(){ this.editingNews.set(null); }
  async saveNews(){
    if(!this.newsForm.title?.trim() || !this.newsForm.content?.trim()) { this.newsError.set('Título y contenido requeridos'); return; }
    this.newsError.set(''); this.savingNews.set(true);
    try {
      if(this.editingNews()?.id){
        await this.admin.updateNews(this.editingNews().id, { title:this.newsForm.title, summary:this.newsForm.summary, content:this.newsForm.content, priority:this.newsForm.priority, publish:this.newsForm.publish });
      } else {
        await this.admin.createNews({ title:this.newsForm.title, summary:this.newsForm.summary, content:this.newsForm.content, priority:this.newsForm.priority, publish:this.newsForm.publish });
      }
      await this.refreshAdminNews();
    } catch(e:any){ this.newsError.set(e?.error?.detail || 'Error guardando'); }
    finally { this.savingNews.set(false); }
  }
  async togglePublish(n:any){
    try { await this.admin.updateNews(n.id, { publish: !n.is_published }); await this.refreshAdminNews(); } catch(e:any){}
  }
  async deleteComment(c:any){
    if(!this.editingNews()?.id) return;
    try { await this.admin.deleteNewsComment(this.editingNews().id, c.id); this.selectedNewsComments.update(list => list.filter(x=>x.id!==c.id)); }
    catch(e:any){}
  }

  // Forum admin logic
  async loadForumCategories(){ try { const cats:any = await this.admin.listCategories(); this.forumCategories.set(cats||[]); } catch(e:any){} }
  startCreateCategory(){ this.editingCategory.set({}); this.categoryForm = { name:'', description:'', position:0 }; }
  selectCategory(c:any){ this.selectedCategory.set(c); this.editingCategory.set(null); this.refreshTopics(); }
  editCategory(c:any){ this.editingCategory.set(c); this.categoryForm = { name:c.name, description:c.description, position:c.position }; }
  cancelCategoryEdit(){ this.editingCategory.set(null); }
  async saveCategory(){
    if(!this.categoryForm.name?.trim()){ this.categoryError.set('Nombre requerido'); return; }
    this.categoryError.set(''); this.savingCategory.set(true);
    try {
      if(this.editingCategory()?.id){ await this.admin.updateCategory(this.editingCategory().id, { name:this.categoryForm.name, description:this.categoryForm.description, position:this.categoryForm.position }); }
      else { await this.admin.createCategory({ name:this.categoryForm.name, description:this.categoryForm.description, position:this.categoryForm.position }); }
      await this.loadForumCategories();
      this.editingCategory.set(null);
    } catch(e:any){ this.categoryError.set(e?.error?.detail || 'Error guardando'); }
    finally { this.savingCategory.set(false); }
  }
  async refreshTopics(){ if(!this.selectedCategory()) return; try { const res:any = await this.admin.listTopics(this.selectedCategory().id,1,100); this.forumTopics.set(res.items||[]); } catch(e:any){} }
  startCreateTopic(){ if(!this.selectedCategory()) return; this.editingTopic.set(true); this.topicForm={ title:'', content:'' }; }
  cancelTopicEdit(){ this.editingTopic.set(false); }
  async saveTopic(){ if(!this.selectedCategory()) return; if(!this.topicForm.title?.trim() || !this.topicForm.content?.trim()){ this.topicError.set('Título y contenido requeridos'); return; } this.topicError.set(''); this.savingTopic.set(true); try { await this.admin.createTopic(this.selectedCategory().id, { title:this.topicForm.title, content:this.topicForm.content }); await this.refreshTopics(); this.editingTopic.set(false); } catch(e:any){ this.topicError.set(e?.error?.detail || 'Error creando tema'); } finally { this.savingTopic.set(false); } }
  async toggleLock(t:any){ try { if(t.is_locked) await this.admin.unlockTopic(t.id); else await this.admin.lockTopic(t.id); await this.refreshTopics(); } catch(e:any){} }
  async togglePin(t:any){ try { if(t.is_pinned) await this.admin.unpinTopic(t.id); else await this.admin.pinTopic(t.id); await this.refreshTopics(); } catch(e:any){} }
  async deleteTopic(t:any){ if(!confirm('Eliminar tema?')) return; try { await this.admin.deleteTopic(t.id); await this.refreshTopics(); } catch(e:any){} }

  // Vote sites logic
  async loadVoteSites(){ this.loadingVoteSites.set(true); try { const list:any = await this.admin.listVoteSites(true); this.voteSites.set(list||[]); } catch(e:any){} finally { this.loadingVoteSites.set(false); } }
  startCreateVote(){ this.editingVote.set({}); this.voteForm = { name:'', url:'', image_url:'', cooldown_minutes:720, points_reward:1, position: (this.voteSites().length? (Math.max(...this.voteSites().map(s=>s.position||0))+1):0), is_enabled:true }; }
  editVote(v:any){ this.editingVote.set(v); this.voteForm = { name:v.name, url:v.url, image_url:v.image_url||'', cooldown_minutes:v.cooldown_minutes, points_reward:v.points_reward, position:v.position, is_enabled: !!v.is_enabled }; }
  cancelVoteEdit(){ this.editingVote.set(null); }
  async saveVote(){ if(!this.voteForm.name?.trim() || !this.voteForm.url?.trim()){ this.voteError.set('Nombre y URL requeridos'); return; } this.voteError.set(''); this.savingVote.set(true); try { if(this.editingVote()?.id){ await this.admin.updateVoteSite(this.editingVote().id, { name:this.voteForm.name, url:this.voteForm.url, image_url:this.voteForm.image_url||null, cooldown_minutes:this.voteForm.cooldown_minutes, points_reward:this.voteForm.points_reward, position:this.voteForm.position, is_enabled:this.voteForm.is_enabled }); } else { await this.admin.createVoteSite({ name:this.voteForm.name, url:this.voteForm.url, image_url:this.voteForm.image_url||undefined, cooldown_minutes:this.voteForm.cooldown_minutes, points_reward:this.voteForm.points_reward, position:this.voteForm.position }); } await this.loadVoteSites(); this.editingVote.set(null); } catch(e:any){ this.voteError.set(e?.error?.detail || 'Error guardando'); } finally { this.savingVote.set(false); } }
  async toggleVoteEnabled(v:any){ try { await this.admin.updateVoteSite(v.id, { is_enabled: !v.is_enabled }); await this.loadVoteSites(); } catch(e:any){} }
  async deleteVote(v:any){ if(!confirm('Eliminar sitio de voto?')) return; try { await this.admin.deleteVoteSite(v.id); await this.loadVoteSites(); } catch(e:any){} }
}
