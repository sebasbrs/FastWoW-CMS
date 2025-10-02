import { Component, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { AuthService } from '../auth.service';
import { environment } from '../environments';

interface VoteSite { id:number; name:string; url:string; image_url?:string; cooldown_minutes:number; points_reward:number; is_enabled:boolean; position:number; next_available_at?:string; }

@Component({
  standalone:true,
  selector:'fw-vote-panel',
  imports:[CommonModule],
  template:`
  <div class="vote-wrapper">
    <h1>Votar & Recompensas</h1>
    <p class="intro">Vota en los sitios para apoyar el servidor y obtén puntos. Haz clic en un sitio cuando el cooldown haya terminado. Se abrirá en una nueva pestaña y obtendrás los puntos automáticamente.</p>
    <div class="sites-grid" *ngIf="!loading() && sites().length">
      <div class="site-card" *ngFor="let s of orderedSites()">
        <div class="img-box" [class.off]="!s.is_enabled">
          <img *ngIf="s.image_url" [src]="s.image_url" alt="{{s.name}}" />
          <div class="placeholder" *ngIf="!s.image_url">{{ s.name[0] || '?' }}</div>
        </div>
        <div class="info">
          <h3>{{ s.name }}</h3>
          <p class="reward">+{{ s.points_reward }} punto{{ s.points_reward>1? 's':'' }}</p>
          <p class="cooldown" *ngIf="remainingForSite(s) as rem">
            <span *ngIf="rem>0; else ready">Disponible en {{ formatDuration(rem) }}</span>
            <ng-template #ready><span class="ready">Listo para votar</span></ng-template>
          </p>
          <button (click)="vote(s)" [disabled]="remainingForSite(s)>0 || votingId()===s.id || !s.is_enabled">
            {{ votingId()===s.id? 'Procesando...' : (remainingForSite(s)>0? 'En cooldown' : 'Votar') }}
          </button>
        </div>
      </div>
    </div>
    <p class="empty" *ngIf="!loading() && !sites().length">No hay sitios de voto configurados.</p>
    <p *ngIf="loading()">Cargando sitios...</p>
    <div class="logs" *ngIf="claims().length">
      <h2>Últimos votos</h2>
      <ul>
        <li *ngFor="let c of claims()">#{{c.site_id}} · +{{c.reward}} pts · {{ formatDate(c.next_available_at) }}</li>
      </ul>
    </div>
  </div>
  `,
  styles:[`
    .vote-wrapper { max-width:960px; margin:0 auto; }
    h1 { margin:.3rem 0 1rem; }
    .intro { font-size:.8rem; color:#88939c; margin-bottom:1.2rem; }
    .sites-grid { display:grid; gap:1rem; grid-template-columns:repeat(auto-fill,minmax(240px,1fr)); }
    .site-card { background:#1d2329; border:1px solid #28323a; padding:.8rem .85rem .9rem; border-radius:10px; display:flex; gap:.8rem; align-items:stretch; position:relative; }
    .img-box { width:64px; height:64px; background:#222b32; border:1px solid #2f3a44; border-radius:8px; display:flex; align-items:center; justify-content:center; overflow:hidden; }
    .img-box.off { filter:grayscale(1) brightness(.7); }
    .img-box img { width:100%; height:100%; object-fit:cover; }
    .img-box .placeholder { font-size:1.3rem; font-weight:600; color:#7a8792; }
    .info { flex:1 1 auto; display:flex; flex-direction:column; }
    .info h3 { margin:0 0 .35rem; font-size:.95rem; }
    .reward { margin:0 0 .4rem; font-size:.65rem; text-transform:uppercase; letter-spacing:.5px; color:#c7d4df; }
    .cooldown { font-size:.6rem; margin:0 0 .5rem; color:#87919a; }
    .cooldown .ready { color:#5bd46b; }
    button { align-self:flex-start; background:#2e3a46; border:1px solid #3d4c58; color:#dde6ed; padding:.45rem .85rem; font-size:.7rem; border-radius:6px; cursor:pointer; }
    button:disabled { opacity:.55; cursor:not-allowed; }
    .empty { color:#6d7a84; font-style:italic; }
    .logs { margin-top:2rem; }
    .logs h2 { font-size:1rem; margin:.2rem 0 .6rem; }
    .logs ul { list-style:none; font-size:.65rem; padding:0; margin:0; }
    .logs li { padding:.3rem 0; border-bottom:1px solid #252f38; }
  `]
})
export class VotePanelComponent {
  sites = signal<VoteSite[]>([]);
  loading = signal(true);
  claims = signal<any[]>([]);
  votingId = signal<number|undefined>(undefined);
  private base = environment.apiBase;

  constructor(private http: HttpClient, public auth: AuthService){
    this.load();
  }

  orderedSites = computed(() => [...this.sites()].sort((a,b)=> (a.position||0)-(b.position||0) || a.id-b.id));

  private async load(){
    try {
      const list:any = await this.http.get(this.base + '/vote/sites').toPromise();
      this.sites.set(list||[]);
      // Podríamos cargar logs para saber next_available pero backend no devuelve next directo, así que para mejorar UX se podría añadir endpoint; por ahora sólo logs recientes.
      const logs:any = await this.http.get(this.base + '/vote/logs?page=1&page_size=20').toPromise().catch(()=>null);
      if (logs?.items) this.claims.set(logs.items);
    } finally { this.loading.set(false); this.computeCooldownsFromLogs(); }
  }

  private computeCooldownsFromLogs(){
    const now = Date.now();
    const bySite = new Map<number,string>();
    for(const l of this.claims()){
      if(!bySite.has(l.site_id)) bySite.set(l.site_id, l.next_available_at);
    }
    this.sites.update(list => list.map(s => ({ ...s, next_available_at: bySite.get(s.id) } as any)));
  }

  remainingForSite(s:VoteSite){
    if(!s.next_available_at) return 0;
    const t = new Date(s.next_available_at).getTime();
    const diff = t - Date.now();
    return diff > 0 ? diff : 0;
  }

  formatDuration(ms:number){
    const totalSec = Math.floor(ms/1000);
    const h = Math.floor(totalSec/3600);
    const m = Math.floor((totalSec%3600)/60);
    const s = totalSec%60;
    if(h>0) return `${h}h ${m}m`;
    if(m>0) return `${m}m ${s}s`;
    return `${s}s`;
  }

  formatDate(d:string){ try { return new Date(d).toLocaleString(); } catch { return d; } }

  async vote(site:VoteSite){
    if(this.remainingForSite(site) > 0) return;
    this.votingId.set(site.id);
    try {
      const res:any = await this.http.post(this.base + `/vote/sites/${site.id}/click`, {}).toPromise();
      // Actualizamos cooldown y puntos usuario
      if(res?.next_available_at){
        this.sites.update(list => list.map(s => s.id===site.id? { ...s, next_available_at: res.next_available_at } : s));
        await this.auth.refreshMe().catch(()=>{});
        // Abrir nueva pestaña
        if(res.site_url) window.open(res.site_url, '_blank');
        // Insertar log al inicio
        this.claims.update(items => [{ site_id: site.id, reward: res.reward, next_available_at: res.next_available_at }, ...items.slice(0,49)]);
      }
    } catch(e:any){
      // Si cooldown -> podría mostrar mensaje; por simplicidad ignoramos aquí
    } finally { this.votingId.set(undefined); }
  }
}
