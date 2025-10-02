import { Component, signal } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AuthService } from './auth.service';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, RouterLink, RouterLinkActive, CommonModule, FormsModule],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App {
  protected readonly title = signal('frontend');
  sidebarOpen = false;
  get user(){ return this.auth.user; }
  get isLogged(){ return this.auth.isLogged; }
  

  constructor(public auth: AuthService){}

  // Realm status widget state
  realmStatuses = signal<any[]>([]);
  private realmTimer: any;

  ngOnInit(){
    this.loadRealmStatus();
    this.realmTimer = setInterval(()=> this.loadRealmStatus(), 30000); // refresh cada 30s
  }

  ngOnDestroy(){
    if(this.realmTimer) clearInterval(this.realmTimer);
  }

  async loadRealmStatus(){
    try {
      const res = await fetch('http://localhost:8000/realm_status').then(r => r.json());
      const realms = res?.realms || [];
      // añadir campo expansion mock (futuro: provendrá de DB)
      this.realmStatuses.set(realms.map((r:any) => ({ expansion:3, ...r })));
    } catch {
      // fallback offline mock
      if(!this.realmStatuses().length){
        this.realmStatuses.set([]);
      }
    }
  }

  factionPercent(r:any, side:'alliance'|'horde'){
    const a = r.alliance || 0; const h = r.horde || 0; const total = a + h;
    if(total === 0) return side==='alliance'? 50 : 50; // repartir
    return side==='alliance'? Math.round((a/total)*100) : Math.round((h/total)*100);
  }


  logout(){
    this.auth.logout();
  }
}
