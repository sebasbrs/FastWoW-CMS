import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ForumCategoriesComponent } from './forum-categories.component';
import { ForumTopicsComponent } from './forum-topics.component';

@Component({
  standalone:true,
  selector:'fw-forum-root',
  imports:[CommonModule, ForumCategoriesComponent, ForumTopicsComponent],
  template:`
    <div class="forum-wrapper">
      <fw-forum-categories *ngIf="view() === 'cats'" ></fw-forum-categories>
      <fw-forum-topics *ngIf="view() === 'topics'" [categoryId]="activeCatId()"></fw-forum-topics>
    </div>
  `,
  styles:[`
    .forum-wrapper { width:100%; }
  `]
})
export class ForumComponent {
  view = signal<'cats' | 'topics'>('cats');
  activeCatId = signal<number | null>(null);
}
