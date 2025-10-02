import { Routes, CanActivateFn, Router } from '@angular/router';
import { inject } from '@angular/core';
import { AuthService } from './auth.service';

export const authGuard: CanActivateFn = () => {
	const auth = inject(AuthService);
	if (auth.isLogged()) return true;
	const router = inject(Router);
	router.navigate(['/login']);
	return false;
};
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
	{ path: 'login', loadComponent: () => import('./login.component').then(m => m.LoginComponent), data: { title: 'Login' } },
	{ path: 'auth/change-password', canActivate: [authGuard], loadComponent: () => import('./auth-change-password.component').then(m => m.ChangePasswordComponent), data: { title: 'Cambiar contraseña' } },
	{ path: 'auth/change-email', canActivate: [authGuard], loadComponent: () => import('./auth-change-email.component').then(m => m.ChangeEmailComponent), data: { title: 'Cambiar email' } },
	{ path: 'auth/password-recovery', loadComponent: () => import('./auth-password-recovery-request.component').then(m => m.PasswordRecoveryRequestComponent), data: { title: 'Recuperar contraseña' } },
	{ path: 'auth/password-recovery/confirm', loadComponent: () => import('./auth-password-recovery-confirm.component').then(m => m.PasswordRecoveryConfirmComponent), data: { title: 'Confirmar recuperación' } },
	{ path: 'auth/email-verification', loadComponent: () => import('./auth-email-verification-request.component').then(m => m.EmailVerificationRequestComponent), data: { title: 'Verificar email' } },
	{ path: 'auth/email-verification/confirm', loadComponent: () => import('./auth-email-verification-confirm.component').then(m => m.EmailVerificationConfirmComponent), data: { title: 'Confirmar verificación email' } },
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
