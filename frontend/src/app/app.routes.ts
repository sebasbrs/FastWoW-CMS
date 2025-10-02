import { Routes } from '@angular/router';
import { Component } from '@angular/core';

@Component({
	selector: 'fw-placeholder',
	template: `<div class="placeholder"><h2>{{title}}</h2><p class="text-muted">Contenido en construcción...</p></div>`,
	standalone: true
})
class PlaceholderComponent {
	title = 'Placeholder';
	constructor(){
		// dynamic title via router data using global document title could be handled later
	}
}

export const routes: Routes = [
	{ path: '', pathMatch: 'full', redirectTo: 'news' },
	{ path: 'register', loadComponent: () => import('./index').then(m => m.RegisterComponent), data: { title: 'Registro' } },
	{ path: 'news', loadComponent: () => import('./index').then(m => m.NewsComponent), data: { title: 'Noticias' } },
	{ path: 'online', loadComponent: () => import('./online/online.component').then(m => m.OnlineComponent), data: { title: 'Online' } },
	{ path: 'forum', loadComponent: () => import('./forum/forum.component').then(m => m.ForumComponent), data: { title: 'Foro' } },
	{ path: 'shop', component: PlaceholderComponent, data: { title: 'Tienda' } },
	{ path: 'pvp', loadComponent: () => import('./pvp/toppvp.component').then(m => m.TopPvpComponent), data: { title: 'Top PvP' } },
	{ path: 'pvp/arena', loadComponent: () => import('./pvp/arena-ladder.component').then(m => m.ArenaLadderComponent), data: { title: 'Arena Ladder' } },
	{ path: 'pvp/arena/team/:teamId', loadComponent: () => import('./pvp/arena-team.component').then(m => m.ArenaTeamComponent), data: { title: 'Equipo Arena' } },
	{ path: 'profile', component: PlaceholderComponent, data: { title: 'Perfil' } },
	{ path: 'profile/:username', loadComponent: () => import('./profile/profile.component').then(m => m.ProfileComponent), data: { title: 'Perfil' } },
	{ path: '**', component: PlaceholderComponent, data: { title: 'No encontrado' } }
];
