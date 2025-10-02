import { Component, signal, Input, OnChanges, SimpleChanges, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ForumService, ForumTopic } from './forum.service';
import { AuthService } from '../auth.service';
import { AdminService } from '../admin.service';

@Component({
  standalone:true,
  selector:'fw-forum-topics',
  imports:[CommonModule, FormsModule],
  template:`
  <div class="topics-view" *ngIf="categoryId; else pick">
    <div class="toolbar">
      <button (click)="goBack()" class="link">← Categorías</button>
      <h2>Temas</h2>
      <button class="new-btn" (click)="toggleCreate()" *ngIf="!creating()">Nuevo</button>
      <button class="new-btn" (click)="toggleCreate()" *ngIf="creating()">Cancelar</button>
    </div>
    <form class="create-form" *ngIf="creating()" (ngSubmit)="createTopic(); $event.preventDefault();">
      <input type="text" placeholder="Título" [(ngModel)]="newTitle" name="title" required />
      <textarea rows="4" placeholder="Contenido inicial" [(ngModel)]="newContent" name="content" required></textarea>
      <div class="actions">
        <button type="submit" [disabled]="creatingTopic() || !newTitle.trim() || !newContent.trim()">{{ creatingTopic()? 'Creando...' : 'Crear' }}</button>
      </div>
      <p class="err" *ngIf="error()">{{ error() }}</p>
    </form>
    <table class="topics">
      <thead><tr><th>Título</th><th>Autor</th><th>Posts</th><th>Último</th><th *ngIf="isAdmin()" class="mod-col">Mod</th></tr></thead>
      <tbody>
        <tr *ngFor="let t of topics()">
          <td (click)="openTopic(t)"><span class="pin" *ngIf="t.is_pinned">📌</span>{{ t.title }}</td>
            <td (click)="openTopic(t)">{{ t.author_username }}</td>
            <td (click)="openTopic(t)">{{ t.posts_count }}</td>
            <td (click)="openTopic(t)">{{ t.last_post_at || t.created_at }}</td>
            <td *ngIf="isAdmin()" class="mod">
              <button (click)="toggleLock(t); $event.stopPropagation();" [title]="t.is_locked? 'Desbloquear':'Bloquear'">{{ t.is_locked? '🔓':'🔒' }}</button>
              <button (click)="togglePin(t); $event.stopPropagation();" [title]="t.is_pinned? 'Desfijar':'Fijar'">{{ t.is_pinned? '📌✖':'📌' }}</button>
              <button (click)="prepareMove(t); $event.stopPropagation();" title="Mover">↔</button>
              <button (click)="deleteTopic(t); $event.stopPropagation();" title="Eliminar" class="danger">✖</button>
            </td>
        </tr>
      </tbody>
    </table>
    <div class="move-box" *ngIf="movingTopic() && isAdmin()">
      <div class="inner">
        <p>Mover: <strong>{{ movingTopic()?.title }}</strong></p>
        <select [(ngModel)]="moveTarget" name="moveTarget">
          <option [ngValue]="null">-- destino --</option>
          <option *ngFor="let c of allCategories()" [ngValue]="c.id">{{ c.name }}</option>
        </select>
        <div class="actions">
          <button (click)="confirmMove()" [disabled]="!moveTarget || moving()">{{ moving()? 'Moviendo...':'Mover' }}</button>
          <button type="button" (click)="cancelMove()">Cancelar</button>
        </div>
        <p class="err" *ngIf="moveError()">{{ moveError() }}</p>
      </div>
    </div>
    <div class="pager" *ngIf="pagination() as p">
      <button (click)="changePage(p.page-1)" [disabled]="p.page<=1">«</button>
      <span>{{ p.page }} / {{ totalPages() }}</span>
      <button (click)="changePage(p.page+1)" [disabled]="p.page>= totalPages()">»</button>
    </div>
  </div>
  <ng-template #pick><p class="muted">Selecciona una categoría...</p></ng-template>
  `,
  styles:[`
    .topics-view { max-width:1000px; position:relative; }
    table { width:100%; border-collapse:collapse; font-size:.8rem; }
    th, td { padding:.55rem .6rem; border-bottom:1px solid #283037; text-align:left; }
    th { font-size:.65rem; text-transform:uppercase; letter-spacing:.5px; color:#88939d; }
    tr { cursor:pointer; }
    tr:hover td { background:#202830; }
    .toolbar { display:flex; align-items:center; gap:1rem; margin-bottom:.75rem; }
    .link { background:none; border:none; color:#8fb5ff; padding:0; cursor:pointer; }
    .new-btn { background:#2f3b47; border:1px solid #3c4a58; padding:.35rem .7rem; border-radius:5px; color:#d4dde5; font-size:.65rem; cursor:pointer; }
    .create-form { display:flex; flex-direction:column; gap:.5rem; background:#1d2329; border:1px solid #28323b; padding:.7rem .8rem .9rem; border-radius:8px; margin-bottom:.9rem; }
    .create-form input, .create-form textarea { background:#1f262c; border:1px solid #2a333c; padding:.45rem .55rem; border-radius:6px; font-size:.75rem; color:#e4eaef; }
    .create-form textarea { resize:vertical; }
    .create-form input:focus, .create-form textarea:focus { outline:none; border-color:#4d6fff; }
    .actions { display:flex; justify-content:flex-end; }
    .actions button { background:#374656; border:1px solid #455564; color:#e1e7ec; padding:.45rem .8rem; border-radius:6px; font-size:.7rem; cursor:pointer; }
    .err { color:#ff6e6e; font-size:.65rem; margin:0; }
    .pager { margin-top:.7rem; display:flex; gap:.5rem; align-items:center; }
    .pager button { background:#1f262d; border:1px solid #2b353f; color:#d0d5da; padding:.3rem .6rem; border-radius:4px; cursor:pointer; }
    .pager button:disabled { opacity:.4; cursor:default; }
    .pin { margin-right:.3rem; }
    .mod-col { width:130px; }
    .mod { display:flex; gap:.3rem; }
    .mod button { background:#242c34; border:1px solid #303a44; padding:.3rem .45rem; font-size:.6rem; border-radius:4px; cursor:pointer; }
    .mod button.danger { background:#4d2323; border-color:#6a3131; }
    .move-box { position:absolute; top:3.1rem; right:0; background:#1d2329; border:1px solid #2c3640; border-radius:8px; padding:.8rem .9rem 1rem; width:260px; box-shadow:0 4px 14px rgba(0,0,0,.4); }
    .move-box p { margin:.1rem 0 .6rem; font-size:.7rem; }
    .move-box select { width:100%; background:#1f262c; border:1px solid #2a333c; color:#d9e2e9; padding:.4rem .45rem; border-radius:6px; font-size:.7rem; margin-bottom:.6rem; }
    .move-box .actions { display:flex; gap:.5rem; }
    .move-box button { background:#2f3b47; border:1px solid #3c4a58; color:#d4dde5; padding:.4rem .7rem; border-radius:5px; font-size:.65rem; cursor:pointer; }
    .move-box .err { color:#ff6d6d; font-size:.6rem; margin:.4rem 0 0; }
    .muted { color:#8a949d; }
  `]
})
export class ForumTopicsComponent implements OnChanges {
  @Input() categoryId!: number | null;
  @Output() backToCategories = new EventEmitter<void>();
  @Output() open = new EventEmitter<ForumTopic>();
  topics = signal<ForumTopic[]>([]);
  pagination = signal<{page:number; page_size:number; total:number} | null>(null);
  loading = signal(false);
  creating = signal(false);
  newTitle = '';
  newContent = '';
  creatingTopic = signal(false);
  error = signal('');
  movingTopic = signal<ForumTopic|null>(null);
  moveTarget: number | null = null;
  moving = signal(false);
  moveError = signal('');

  constructor(private forum: ForumService, private auth: AuthService, private admin: AdminService){}

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
    this.backToCategories.emit();
  }

  openTopic(t:ForumTopic){ this.open.emit(t); }

  isAdmin(){ return this.auth.isAdmin(); }

  toggleCreate(){ this.creating.set(!this.creating()); this.error.set(''); if(!this.creating()){ this.newTitle=''; this.newContent=''; } }
  async createTopic(){
    if(!this.categoryId) return;
    if(!this.newTitle.trim() || !this.newContent.trim()) return;
    this.creatingTopic.set(true); this.error.set('');
    try {
      const created:any = await this.forum.createTopic(this.categoryId, this.newTitle.trim(), this.newContent.trim());
      this.creating.set(false); this.newTitle=''; this.newContent='';
      await this.load(1); // refresh page 1 (new pinned ordering)
      // auto-open the topic
      this.open.emit(created);
    } catch(e:any){ this.error.set(e?.error?.detail || 'Error creando topic'); }
    finally { this.creatingTopic.set(false); }
  }

  async toggleLock(t:ForumTopic){ if(!this.isAdmin()) return; try { if(t.is_locked) await this.admin.unlockTopic(t.id); else await this.admin.lockTopic(t.id); await this.load(this.pagination()?.page || 1); } catch{} }
  async togglePin(t:ForumTopic){ if(!this.isAdmin()) return; try { if(t.is_pinned) await this.admin.unpinTopic(t.id); else await this.admin.pinTopic(t.id); await this.load(this.pagination()?.page || 1); } catch{} }
  deleteTopic(t:ForumTopic){ if(!this.isAdmin()) return; if(!confirm('Eliminar tema?')) return; this.admin.deleteTopic(t.id).then(()=> this.load(this.pagination()?.page || 1)).catch(()=>{}); }
  prepareMove(t:ForumTopic){ if(!this.isAdmin()) return; this.movingTopic.set(t); this.moveTarget=null; this.moveError.set(''); }
  cancelMove(){ this.movingTopic.set(null); this.moveTarget=null; }
  allCategories(){ return this.forum.categories() || []; }
  async confirmMove(){
    if(!this.isAdmin() || !this.movingTopic() || !this.moveTarget) return;
    if(this.moveTarget === this.movingTopic()!.id) return;
    this.moving.set(true); this.moveError.set('');
    try { await this.admin.moveTopic(this.movingTopic()!.id, this.moveTarget); this.cancelMove(); await this.load(this.pagination()?.page || 1); }
    catch(e:any){ this.moveError.set(e?.error?.detail || 'Error moviendo'); }
    finally { this.moving.set(false); }
  }
}
