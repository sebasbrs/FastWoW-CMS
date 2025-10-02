import { Component, signal, computed, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ForumService, ForumCategory } from './forum.service';

@Component({
  standalone:true,
  selector:'fw-forum-categories',
  imports:[CommonModule],
  template:`
  <div class="forum-cats">
    <h1>Foro</h1>
    <p class="muted" *ngIf="loading()">Cargando categorías...</p>
    <div class="grid" *ngIf="!loading()">
      <div class="cat" *ngFor="let c of cats()" (click)="open(c)">
        <div class="head"><h3>{{ c.name }}</h3><span class="badge">ID {{ c.id }}</span></div>
        <p class="desc">{{ c.description || 'Sin descripción' }}</p>
      </div>
    </div>
  </div>
  `,
  styles:[`
    .forum-cats { max-width:1000px; }
    .muted { color:#8a949d; font-size:.8rem; }
    .grid { display:grid; gap:1rem; grid-template-columns:repeat(auto-fill,minmax(260px,1fr)); }
    .cat { background:#1d2127; border:1px solid #2a313a; padding:.85rem 1rem 1rem; border-radius:10px; cursor:pointer; transition:.15s background,border-color; }
    .cat:hover { background:#232a31; border-color:#36414d; }
    .head { display:flex; justify-content:space-between; align-items:center; }
    h3 { margin:.1rem 0 .4rem; font-size:1rem; }
    .badge { background:#2d3640; color:#b3c4d4; font-size:.6rem; padding:.25rem .5rem; border-radius:20px; }
    .desc { margin:0; font-size:.75rem; line-height:1.15rem; color:#cfd5dc; }
  `]
})
export class ForumCategoriesComponent {
  loading = signal(false);
  cats = signal<ForumCategory[]>([]);
  @Output() selectCategory = new EventEmitter<ForumCategory>();

  constructor(private forum: ForumService){
    this.loading = this.forum.loadingCategories;
    this.cats = computed(() => this.forum.categories() || [] ) as any;
    if(!this.forum.categories()) this.forum.fetchCategories();
  }

  open(cat:ForumCategory){
    this.selectCategory.emit(cat);
  }
}
