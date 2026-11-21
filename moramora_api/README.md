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

## WebSocket de détection

Démarrez Redis avant le serveur (par exemple avec Docker) :

```powershell
docker run --rm -p 6379:6379 redis:7-alpine
python manage.py runserver
```

Le WebSocket est disponible à `ws://localhost:8000/ws/detection/`. Dans un
navigateur, transmettez le JWT obtenu au login comme second sous-protocole
(`bearer` est le sous-protocole sélectionné par le serveur) :

```javascript
const socket = new WebSocket(
  "ws://localhost:8000/ws/detection/",
  ["bearer", accessToken]
);
socket.onopen = () => {
  socket.send(JSON.stringify({
    type: "image",
    image: base64JpegOrPng
  }));
};
socket.onmessage = ({ data }) => console.log(JSON.parse(data));
```

Un client non navigateur peut également envoyer le JWT dans
`Authorization: Bearer <JWT>`. Les deux modes vérifient la signature, le compte
actif et le registre de révocation existant. Les connexions sans origine ou
dont l'origine n'est pas dans `WEBSOCKET_ALLOWED_ORIGINS` sont refusées. En
production, utilisez `wss://` et limitez cette liste aux origines de confiance.
Seuls les JWT transmis par sous-protocole ou par l'en-tête Authorization sont
acceptés ; un JWT placé dans l'URL n'est pas accepté.

Envoyez soit une trame binaire JPEG/PNG, soit un message JSON
`{"type":"image","image":"<base64>"}`. Une URL de données `data:image/jpeg;base64,...`
ou `data:image/png;base64,...` est également acceptée. La limite par défaut est
5 Mio et 20 mégapixels. Daphne applique également une limite de trame et de
message calculée à partir de `WEBSOCKET_MAX_IMAGE_SIZE`. Chaque image valide
reçoit un message
`detection_result` comprenant l'image annotée (JPEG Base64) et les boîtes,
classes et confiances produites par YOLO. Si le modèle a détecté au moins une
boîte, un message `alert` suit le résultat. Les erreurs sont transmises comme
messages `error`; une image n'est pas mise en file si le modèle traite déjà une
autre requête, le client peut réessayer.

Le moteur existant `violation/inference.py` charge une seule fois les mêmes
poids Hugging Face que le prototype. Le script `violation/main.py` continue de
lancer ses démonstrations d'image et de vidéo lorsqu'il est exécuté directement ;
il ne démarre plus de téléchargement ou de prédiction lorsqu'il est importé.

Pour tester :

```powershell
python manage.py test detection_ws authentication
```

Le test ci-dessous exerce le vrai modèle YOLO avec l'image du prototype
(télécharge les poids Hugging Face s'ils ne sont pas déjà en cache) :

```powershell
$env:RUN_MODEL_INTEGRATION_TESTS = "1"
python manage.py test detection_ws.tests.DetectionWebSocketTests.test_real_model_through_websocket
Remove-Item Env:RUN_MODEL_INTEGRATION_TESTS
```
