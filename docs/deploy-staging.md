# Setup de ambiente staging — Conflur

Checklist paso a paso para crear el ambiente de staging por primera vez. Se ejecuta **una sola vez**.
Después, el flujo de deploy queda automatizado por rama de git (ver `architecture.md` §Ambientes).

**Estado inicial:** existe solo prod (Railway `conflur-backend` + Vercel `conflur` + Neon rama `main`), watcheando la rama git `main`.

**Estado final:**
- Prod queda watcheando la rama git `production` (misma DB, mismos servicios, distinto branch de git).
- Staging nuevo (Railway `conflur-backend-staging` + Vercel `conflur-staging` + Neon branch `staging`), watcheando `main`.

**Preparación previa (ya hecha):**
- Rama `production` creada localmente y pusheada a GitHub apuntando al commit actualmente en prod (`3dae895`).
- La rama `main` local tiene Fase 3 (canal web) commiteado pero **NO pusheado** todavía — no se pushea hasta terminar los pasos 1-3 acá abajo. Si se pushea antes, Railway/Vercel siguen watcheando `main` y auto-deployan Fase 3 a prod sin haber probado nada.

---

## 1) Neon — crear branch de staging

1. Ir a [console.neon.tech](https://console.neon.tech), proyecto de Conflur.
2. Sección **Branches** → **Create branch**.
3. Nombre: `staging`. Source branch: `main` (el default de prod). Include data: **sí** (schema + datos actuales — sirve para hacer QA con datos representativos).
4. Al crearse, obtener las dos connection strings del nuevo branch:
   - **Owner (`neondb_owner`)** → usar como `DATABASE_URL` en staging (para migraciones/admin).
   - **App role (`conflur_app`)** → usar como `APP_DATABASE_URL` en staging (runtime, sin bypass RLS).

   Si el rol `conflur_app` no existe en el branch nuevo, ejecutar en SQL editor del branch staging:
   ```sql
   -- copiar el mismo user creado en prod originalmente
   CREATE USER conflur_app WITH PASSWORD '<mismo password que prod o uno nuevo>';
   GRANT CONNECT ON DATABASE neondb TO conflur_app;
   GRANT USAGE ON SCHEMA public TO conflur_app;
   GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO conflur_app;
   GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO conflur_app;
   ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO conflur_app;
   ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO conflur_app;
   ```

5. Guardar ambas connection strings — se pegan en Railway staging (paso 3).

---

## 2) Railway — cambiar prod a rama `production`

Antes de crear staging, hay que sacar a prod de la rama `main` para que el próximo push a `main` no le pegue.

1. Railway → proyecto Conflur → servicio `conflur-backend` (el actual de prod).
2. **Settings** → **Source** → **Branch** → cambiar de `main` a `production`.
3. Guardar. Railway va a intentar un redeploy: no debería hacer nada porque `production` apunta al mismo commit que estaba deployado (`3dae895`). Verificar en Deployments que sigue verde y que `/health` responde OK.

---

## 3) Railway — crear servicio `conflur-backend-staging`

1. Railway → mismo proyecto → **+ New** → **GitHub Repo** → `conflur/conflur`.
2. **Name:** `conflur-backend-staging`.
3. **Root Directory:** `backend` (mismo que prod — lo pide Railpack para monorepo).
4. **Branch:** `main`.
5. **Variables** — copiar las de prod y cambiar solo las siguientes:

   | Variable | Valor staging |
   |---|---|
   | `APP_ENV` | `staging` |
   | `DATABASE_URL` | Owner de branch Neon `staging` (paso 1) |
   | `APP_DATABASE_URL` | Rol `conflur_app` de branch Neon `staging` (paso 1) |
   | `NEXTAUTH_SECRET` | Generar uno nuevo con `openssl rand -base64 32` — no reusar el de prod |
   | `NEXTAUTH_URL` | URL del Vercel staging (paso 5) — dejar placeholder por ahora |
   | `FRONTEND_URL` | URL del Vercel staging (paso 5) — dejar placeholder por ahora |
   | `ANTHROPIC_API_KEY` | mismo que prod (o key separada si preferís aislar consumo) |
   | resto | mismos valores que prod |

6. Deploy inicial va a fallar hasta que se le peguen las URLs correctas de Vercel staging (paso 5). Está esperado.

7. Anotar la URL pública que Railway asigna al servicio (ej. `conflur-backend-staging-production.up.railway.app`) — se necesita en paso 4.

---

## 4) Vercel — cambiar prod a rama `production`

1. Vercel → proyecto `conflur` (el actual de prod).
2. **Settings** → **Git** → **Production Branch** → cambiar de `main` a `production`.
3. Guardar. Vercel puede disparar un rebuild — no debería cambiar nada porque `production` apunta al mismo commit.
4. Si `NEXT_PUBLIC_API_URL` estaba apuntando al Railway prod: dejar como está — ese sigue siendo prod.

---

## 5) Vercel — crear proyecto `conflur-staging`

1. Vercel → **Add New** → **Project** → importar el repo `conflur/conflur`.
2. **Project Name:** `conflur-staging`.
3. **Root Directory:** `frontend`.
4. **Production Branch:** `main`.
5. **Environment Variables:**

   | Variable | Valor |
   |---|---|
   | `NEXT_PUBLIC_API_URL` | URL Railway staging del paso 3 (con `https://`) |
   | `NEXTAUTH_URL` | URL que Vercel asigne al proyecto staging (ver abajo) |
   | `NEXTAUTH_SECRET` | mismo que Railway staging paso 3 |
   | resto | mismos que prod |

6. Deploy inicial. Anotar la URL de Vercel (ej. `conflur-staging.vercel.app`).
7. Volver a Vercel → proyecto staging → **Settings** → **Environment Variables** → poner `NEXTAUTH_URL` = URL final (paso 6). Redeploy.
8. Volver a Railway staging (paso 3) → variables → `NEXTAUTH_URL` = URL Vercel staging + `FRONTEND_URL` = URL Vercel staging. Redeploy backend.
9. Verificar `GET https://<railway-staging>/health` → `{"status":"ok"}`.

---

## 6) Aplicar migraciones al branch de staging

Desde local, con `DATABASE_URL` = owner de Neon staging:

```bash
cd backend
DATABASE_URL="<staging_owner_url>" python -m alembic upgrade head
```

Si el branch fue creado con "Include data", ya tiene todas las migraciones aplicadas hasta el commit deployado. Igual correr `upgrade head` es idempotente y confirma el estado. Cuando pusheemos `main` con la migración 0014, se aplica acá.

Nota: la migración 0014 (discovery_sessions) **ya está aplicada en el branch main de Neon** (prod). Al crear el branch staging con "include data", ese estado se copia. Si el checklist te lleva a un branch sin 0014, aplicalo con el comando de arriba.

---

## 7) Verificación final

- [ ] `GET https://<railway-prod>/health` → OK (mismo servicio que antes, solo cambió branch git).
- [ ] `GET https://<railway-staging>/health` → OK.
- [ ] Vercel prod carga en el dominio de siempre.
- [ ] Vercel staging carga en `conflur-staging.vercel.app`.
- [ ] Confirmar en Railway que **el servicio prod watchea `production`** y **el staging watchea `main`**.
- [ ] Confirmar en Vercel lo mismo.

Cuando los 6 checks pasen: avisar y pusheo `main` (con Fase 3 canal web) — solo staging deploya. Prod queda intacto.

---

## Flujo de trabajo a partir de acá

- **Todo trabajo** commitea a `main` → auto-deploy a staging.
- **Promoción a prod** (cuando el cambio pasó QA en staging):

  ```bash
  git checkout production
  git merge --ff-only main
  git push origin production
  git checkout main
  ```

- Nunca commitear directo a `production`. Es rama de deploy, no de trabajo.
