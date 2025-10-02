import { Component, Input, OnChanges, SimpleChanges, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ForumService, ForumPost } from './forum.service';
import { AuthService } from '../auth.service';

@Component({
  standalone:true,
  selector:'fw-forum-topic-detail',
  imports:[CommonModule, FormsModule],
  template:`
  <div *ngIf="topic() as t" class="topic-detail">
    <div class="head">
      <button class="link" (click)="back.emit()">← Volver</button>
      <h2>{{ t.title }}</h2>
      <span class="badges">
        <span class="b" *ngIf="t.is_locked">🔒 Locked</span>
        <span class="b" *ngIf="t.is_pinned">📌 Pinned</span>
      </span>
    </div>
    <div class="posts">
      <div class="post" *ngFor="let p of posts()">
        <div class="meta">{{ p.author_username }} • {{ formatDate(p.created_at) }}</div>
        <div class="content">{{ p.content }}</div>
      </div>
      <div *ngIf="!posts().length" class="empty">Sin posts todavía.</div>
    </div>
    <form *ngIf="canPost() && !t.is_locked" class="new-post" (ngSubmit)="submitPost(); $event.preventDefault();">
      <textarea rows="4" [(ngModel)]="postContent" name="content" placeholder="Escribe una respuesta..." required></textarea>
      <div class="actions">
        <button type="submit" [disabled]="posting() || !postContent.trim()">{{ posting()? 'Enviando...' : 'Responder' }}</button>
      </div>
      <p class="err" *ngIf="error()">{{ error() }}</p>
    </form>
    <p *ngIf="t.is_locked" class="locked-note">Topic bloqueado.</p>
  </div>
  <p *ngIf="loading()" class="muted">Cargando...</p>
  `,
  styles:[`
    .topic-detail { max-width:1000px; }
    .head { display:flex; align-items:center; gap:.75rem; flex-wrap:wrap; }
    .head h2 { margin:.2rem 0; font-size:1.2rem; }
    .link { background:none; border:none; color:#8fb5ff; cursor:pointer; padding:0; }
    .badges { display:flex; gap:.4rem; }
    .b { background:#2d3640; padding:.25rem .55rem; border-radius:14px; font-size:.65rem; }
    .posts { margin:1rem 0; display:flex; flex-direction:column; gap:.8rem; }
    .post { background:#1d2329; border:1px solid #273038; padding:.6rem .8rem .7rem; border-radius:8px; }
    .post .meta { font-size:.6rem; text-transform:uppercase; letter-spacing:.5px; color:#81919e; margin-bottom:.35rem; }
    .post .content { white-space:pre-line; font-size:.8rem; line-height:1.1rem; }
    .new-post { display:flex; flex-direction:column; gap:.6rem; }
    textarea { background:#1e252b; border:1px solid #2a333c; border-radius:6px; padding:.55rem .6rem; resize:vertical; color:#e4eaef; font-size:.75rem; font-family:inherit; }
    textarea:focus { outline:none; border-color:#4d6fff; }
    .actions { display:flex; justify-content:flex-end; }
    button { background:#2f3b47; border:1px solid #3c4a58; color:#d4dde5; padding:.45rem .9rem; border-radius:6px; cursor:pointer; font-size:.7rem; }
    button:disabled { opacity:.5; cursor:default; }
    .empty { color:#65727d; font-size:.75rem; font-style:italic; }
    .err { color:#ff7272; font-size:.65rem; margin:0; }
    .locked-note { font-size:.7rem; color:#c48888; }
    .muted { color:#83909b; }
  `]
})
export class ForumTopicDetailComponent implements OnChanges {
  @Input() topicId!: number | null;
  @Input() categoryId!: number | null;
  @Input() back!: { emit: () => void }; // simple event-like bridge from parent

  loading = signal(false);
  topic = signal<any|null>(null);
  posts = signal<ForumPost[]>([]);
  postContent = '';
  posting = signal(false);
  error = signal('');

  constructor(private forum: ForumService, private auth: AuthService){}

  async load(){
    if(!this.topicId) return;
    this.loading.set(true);
    this.error.set('');
    try {
      const data:any = await this.forum.fetchTopic(this.topicId);
      this.topic.set(data);
      this.posts.set(data.posts || []);
    } catch(e:any){ this.error.set(e?.error?.detail || 'Error cargando topic'); }
    finally { this.loading.set(false); }
  }

  ngOnChanges(ch:SimpleChanges){
    if(ch['topicId'] && this.topicId){ this.load(); }
  }

  canPost(){ return !!this.auth.isLogged(); }

  async submitPost(){
    if(!this.topicId) return;
    if(!this.postContent.trim()) return;
    this.posting.set(true); this.error.set('');
    try {
      const p:any = await this.forum.createPost(this.topicId, this.postContent.trim());
      this.posts.update(list => [...list, p]);
      this.postContent='';
    } catch(e:any){ this.error.set(e?.error?.detail || 'Error publicando'); }
    finally { this.posting.set(false); }
  }

  formatDate(d:string){ if(!d) return ''; try { return new Date(d).toLocaleString(); } catch { return d; } }
}
