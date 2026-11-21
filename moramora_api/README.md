# API d'authentification

API REST Django REST Framework exposant quatre endpoints : inscription, connexion,
déconnexion et consultation du profil. Les tokens d'accès JWT sont signés avec
HS256 et n'ont pas de date d'expiration. Chaque token émis est enregistré en base
et vérifié à chaque requête authentifiée. La révocation à la déconnexion ou la
révocation de tous les tokens d'un utilisateur invalide donc immédiatement le
token, malgré l'absence d'expiration.

## Installation

Depuis le dossier `moramora_api` :

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python manage.py migrate
python manage.py runserver
```

Le projet utilise SQLite par défaut. Pour PostgreSQL, créez une base et
renseignez dans `.env` `DB_ENGINE=postgresql`, `DB_NAME`, `DB_USER`,
`DB_PASSWORD`, `DB_HOST` et `DB_PORT`.

En production, définissez une valeur `DJANGO_SECRET_KEY` longue et aléatoire,
`DJANGO_DEBUG=false`, et limitez `DJANGO_ALLOWED_HOSTS` et
`CORS_ALLOWED_ORIGINS` aux hôtes réellement utilisés. Le frontend envoie le JWT
dans l'en-tête `Authorization: Bearer <token>`. La limitation de connexion est
configurée par `LOGIN_RATE_LIMIT` (par défaut `5/min`) ; déployez un cache partagé
pour appliquer cette limite de façon cohérente sur plusieurs instances.

## Endpoints

Les erreurs ont le format `{"success": false, "message": "...", "errors": ...}`
et conservent les codes HTTP appropriés.

### Inscription

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/auth/signup/ `
  -H "Content-Type: application/json" `
  -d "{\"username\":\"john\",\"email\":\"john@example.com\",\"password\":\"A-strong-password-123!\",\"password_confirmation\":\"A-strong-password-123!\"}"
```

Renvoie `201 Created` avec les champs publics `id`, `username` et `email`.
L'email et le nom d'utilisateur sont uniques ; les mots de passe doivent passer
les validateurs Django et sont hashés par `create_user`.

### Connexion

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/auth/login/ `
  -H "Content-Type: application/json" `
  -d "{\"email\":\"john@example.com\",\"password\":\"A-strong-password-123!\"}"
```

Renvoie `200 OK` avec `data.access` et les informations essentielles de
l'utilisateur. Les identifiants invalides ou un compte inactif renvoient
`401 Unauthorized`.

### Profil

```powershell
curl.exe http://127.0.0.1:8000/api/auth/profile/ `
  -H "Authorization: Bearer <JWT>"
```

Renvoie l'ID, le nom d'utilisateur, l'email, `date_joined` et `last_login`.

### Déconnexion

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/auth/logout/ `
  -H "Authorization: Bearer <JWT>"
```

Renvoie `200 OK` et révoque le JWT courant. Toute réutilisation ultérieure
renvoie `401 Unauthorized`.

## Révoquer les sessions d'un compte compromis

Dans le code applicatif, appelez le service suivant après avoir identifié le
compte compromis :

```python
from authentication.services import revoke_all_tokens_for_user

revoke_all_tokens_for_user(user)
```

Le service révoque en base tous les tokens actifs de cet utilisateur. Aucun
endpoint supplémentaire n'est exposé.

## Tests

```powershell
python manage.py test authentication
```

Les tests couvrent les quatre fonctionnalités, les mots de passe, les comptes
inactifs, l'absence d'expiration des JWT et les révocations individuelle et
globale.
