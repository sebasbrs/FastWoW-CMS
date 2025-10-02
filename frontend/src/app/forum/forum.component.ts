import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ForumCategoriesComponent } from './forum-categories.component';
import { ForumTopicsComponent } from './forum-topics.component';
import { ForumTopicDetailComponent } from './forum-topic-detail.component';
import { ForumCategory, ForumTopic } from './forum.service';

@Component({
  standalone:true,
  selector:'fw-forum-root',
  imports:[CommonModule, ForumCategoriesComponent, ForumTopicsComponent, ForumTopicDetailComponent],
  template:`
    <div class="forum-wrapper">
      <fw-forum-categories *ngIf="view() === 'cats'" (selectCategory)="enterCategory($event)"></fw-forum-categories>
      <fw-forum-topics *ngIf="view() === 'topics'" [categoryId]="activeCatId()" (backToCategories)="backToCategories()" (open)="openTopic($event)"></fw-forum-topics>
      <fw-forum-topic-detail *ngIf="view()==='topic'" [topicId]="activeTopicId()" [categoryId]="activeCatId()" [back]="{emit: backFromTopic}" ></fw-forum-topic-detail>
    </div>
  `,
  styles:[`
    .forum-wrapper { width:100%; }
  `]
})
export class ForumComponent {
  view = signal<'cats' | 'topics' | 'topic'>('cats');
  activeCatId = signal<number | null>(null);
  activeTopicId = signal<number | null>(null);

  enterCategory(cat:ForumCategory){ this.activeCatId.set(cat.id); this.view.set('topics'); this.activeTopicId.set(null); }
  backToCategories(){ this.view.set('cats'); this.activeCatId.set(null); this.activeTopicId.set(null); }
  openTopic(t:ForumTopic){ this.activeTopicId.set(t.id); this.view.set('topic'); }
  backFromTopic = () => { this.view.set('topics'); this.activeTopicId.set(null); };
}
