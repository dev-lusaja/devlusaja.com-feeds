# Deploy a Netlify

Este documento explica cómo desplegar los feeds JSON estáticos en Netlify.

## Configuración

Este proyecto está configurado para publicar **únicamente** la carpeta `assets/` que contiene los archivos JSON generados.

### Archivos de Configuración

- `netlify.toml`: Configuración principal de Netlify
- `assets/_headers`: Headers HTTP (CORS, Cache, Security)
- `.netlifyignore`: Archivos a excluir del deploy

## Método 1: Netlify CLI (Recomendado)

### 1. Instalar Netlify CLI

```bash
npm install -g netlify-cli
```

### 2. Autenticarse

```bash
netlify login
```

### 3. Deploy Manual

**Primera vez (crear sitio):**
```bash
netlify deploy --prod
```

**Deploys posteriores:**
```bash
netlify deploy --prod
```

### 4. Automatizar con Script

Puedes crear un script que ejecute:

```bash
#!/bin/bash
# deploy.sh

echo "🚀 Generando feeds..."
./run.sh  # O el comando que uses para generar los feeds

echo "📤 Desplegando a Netlify..."
netlify deploy --prod

echo "✅ Deploy completado!"
```

Hazlo ejecutable:
```bash
chmod +x deploy.sh
```

## Método 2: Conectar Repositorio GitHub

### 1. Subir código a GitHub

```bash
git add .
git commit -m "Add Netlify configuration"
git push origin main
```

### 2. Conectar en Netlify Dashboard

1. Ve a [Netlify](https://app.netlify.com/)
2. Click en "Add new site" > "Import an existing project"
3. Conecta tu repositorio de GitHub
4. Netlify detectará automáticamente el `netlify.toml`
5. Click en "Deploy site"

### 3. Deploy Automático

Cada vez que hagas push a GitHub, Netlify redesplegará automáticamente.

Para actualizar feeds:
```bash
# Genera los feeds localmente
./run.sh

# Sube los cambios
git add assets/
git commit -m "Update feeds"
git push

# Netlify redesplegará automáticamente
```

## Método 3: Deploy Manual desde Dashboard

1. Genera los feeds localmente
2. Ve a [Netlify](https://app.netlify.com/)
3. Arrastra y suelta la carpeta `assets/` en el dashboard

⚠️ **Nota:** Este método es menos práctico para actualizaciones frecuentes.

## Flujo de Trabajo Recomendado

### Opción A: Manual Local
```bash
# 1. Generar feeds
./run.sh

# 2. Deploy a Netlify
netlify deploy --prod
```

### Opción B: Con Git
```bash
# 1. Generar feeds
./run.sh

# 2. Commit y push
git add assets/
git commit -m "Update feeds $(date +%Y-%m-%d)"
git push

# Netlify redespliega automáticamente
```

## Verificar el Deploy

Una vez desplegado, tus feeds estarán disponibles en:

```
https://tu-sitio.netlify.app/notice-all-chunk-0.json
https://tu-sitio.netlify.app/forum-all-chunk-0.json
https://tu-sitio.netlify.app/metadata.json
```

## Configurar Dominio Personalizado (Opcional)

1. En Netlify Dashboard, ve a "Domain settings"
2. Click en "Add custom domain"
3. Sigue las instrucciones para configurar tu DNS

Ejemplo: `feeds.devlusaja.com`

## Headers Configurados

Los siguientes headers están configurados automáticamente:

- **CORS:** Permite acceso desde cualquier dominio (`*`)
- **Cache:** 5 minutos en navegador, 1 hora en CDN
- **Security:** XSS Protection, Content Sniffing Protection, etc.

## Estructura de URLs

```
https://tu-sitio.netlify.app/
├── notice-all-chunk-0.json
├── notice-all-chunk-1.json
├── forum-all-chunk-0.json
├── youtube-all-chunk-0.json
├── pappers-arXiv_AI-chunk-0.json
└── metadata.json
```

## Consumir desde Frontend

```javascript
// Ejemplo en JavaScript
const FEEDS_URL = 'https://tu-sitio.netlify.app';

async function fetchFeeds() {
  const response = await fetch(`${FEEDS_URL}/notice-all-chunk-0.json`);
  const data = await response.json();
  return data;
}
```

## Troubleshooting

### El sitio no se actualiza
- Verifica que los archivos JSON estén en `assets/`
- Limpia el cache de Netlify: Dashboard > Deploys > Clear cache and deploy

### Error 404 en algunos archivos
- Verifica que los archivos existan en `assets/`
- Revisa el `.netlifyignore` para asegurarte de que no estés excluyendo archivos necesarios

### CORS no funciona
- Verifica que `assets/_headers` esté presente
- Limpia el cache del navegador

## Monitoreo

- **Build logs:** Dashboard > Deploys > [último deploy] > Deploy log
- **Function logs:** Dashboard > Functions (si usas Functions)
- **Analytics:** Dashboard > Analytics (plan Pro)

## Costos

- **Free tier:** 100GB bandwidth/mes, builds ilimitados
- Para tu caso de uso (JSON estáticos): probablemente gratis
- [Ver planes](https://www.netlify.com/pricing/)
