# 🤖 Chatbot Fullstack con RAG

Backend desarrollado con **Django 4.2** y frontend con **React 19 + Vite** que proporciona una aplicación de chat inteligente con capacidades de memoria conversacional, búsqueda semántica mediante vectores (RAG) y procesamiento de documentos — todo con modelos locales vía **Ollama**.

---

## 🚀 Características Principales

- ✅ API REST construida con Django REST Framework
- ⚛️ Frontend moderno con React 19, Tailwind CSS y TanStack Query
- 🐘 Base de datos PostgreSQL con extensión `pgvector` para embeddings y búsqueda vectorial
- ⚡ Caché y gestión de contexto conversacional con Redis
- 📄 **RAG (Retrieval-Augmented Generation):** sube archivos de texto y el chatbot responde basándose en su contenido
- 🦙 Motor LLM local con Ollama (modelo `llama3`, embeddings `nomic-embed-text`)
- 🔒 CORS configurado para desarrollo frontend
- 📦 Servido de archivos estáticos en producción con Whitenoise
- 🌍 Configuración basada en variables de entorno (`python-dotenv`)

---

## 🛠️ Stack Tecnológico

### Backend

| Componente     | Tecnología                         |
| -------------- | ---------------------------------- |
| 🎯 Framework      | Django 4.2 + Django REST Framework |
| 🐘 Base de datos  | PostgreSQL + pgvector              |
| ⚡ Caché/Memoria  | Redis (django-redis)               |
| 🦙 LLM/Embeddings | Ollama (llama3, nomic-embed-text)  |
| 📦 Estáticos      | Whitenoise                         |
| 🔐 Autenticación  | AllowAny (por defecto, configurable) |

### Frontend

| Componente | Tecnología               |
| ---------- | ------------------------ |
| ⚛️ Framework  | React 19                 |
| ⚡ Build tool | Vite 8                   |
| 🎨 Estilos    | Tailwind CSS 4           |
| 🔄 Estado     | TanStack Query           |
| 🐛 DevTools   | React Query DevTools     |

---

## 📋 Requisitos Previos

- 🐍 Python 3.9+
- 🟢 Node.js 18+
- 🐘 PostgreSQL 12+ (o Docker)
- 🔴 Redis Server (o Docker)
- 🦙 [Ollama](https://ollama.com) instalado y corriendo localmente
- 📦 `pip` o `uv`/`poetry` para dependencias Python
- 📦 `npm` para dependencias del frontend

---

## 🐳 Infraestructura Rápida con Docker

El proyecto incluye un `docker-compose.yml` que levanta PostgreSQL (con pgvector) y Redis automáticamente:

```bash
docker-compose up -d
```

Esto expone:

- 🐘 PostgreSQL en `localhost:5432`
- 🔴 Redis en `localhost:6379`

---

## 📦 Instalación y Configuración

### 1️⃣ Clonar el repositorio

```bash
git clone <tu-repo-url>
cd Chatbot
```

### 2️⃣ Backend

#### a. 🐍 Crear entorno virtual e instalar dependencias

```bash
python -m venv .venv
source .venv/bin/activate  # En Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

#### b. ⚙️ Configurar variables de entorno

Crea un archivo `.env` en `chatbot_project/` con el siguiente contenido:

```env
SECRET_KEY=tu_clave_secreta_segura
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

DB_NAME=chatbot_db
DB_USER=chatbot_user
DB_PASSWORD=tu_password
DB_HOST=localhost
DB_PORT=5432

REDIS_URL=redis://127.0.0.1:6379/0

CONVERSATION_MEMORY_TTL=1800
CONVERSATION_MEMORY_WINDOW=20

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=1000
```

#### c. 🐘 Preparar base de datos

Si no usas Docker, asegúrate de crear la base de datos y la extensión vectorial:

```sql
CREATE DATABASE chatbot_db;
CREATE USER chatbot_user WITH PASSWORD 'tu_password';
GRANT ALL PRIVILEGES ON DATABASE chatbot_db TO chatbot_user;
`
\c chatbot_db
CREATE EXTENSION IF NOT EXISTS vector;
```

#### d. 🔄 Migraciones y recolección de estáticos

```bash
cd chatbot_project
python manage.py migrate
python manage.py collectstatic --noinput
```

### 3️⃣ Frontend

```bash
cd frontend
npm install
npm run dev
```

El frontend estará disponible en `http://localhost:5173/`

### 4️⃣ 🦙 Ollama

Asegúrate de tener Ollama corriendo y los modelos descargados:

```bash
ollama pull llama3
ollama pull nomic-embed-text
```

---

## ▶️ Ejecución del Proyecto

### 🚀 Opción A: Inicialización automática

Usa el script incluido:

```bash
chmod +x init_project.sh
./init_project.sh
```

### 🖥️ Opción B: Manual

**Terminal 1 — Backend:**

```bash
cd chatbot_project
python manage.py runserver
```

La API estará en `http://localhost:8000/`

**Terminal 2 — Frontend:**

```bash
cd frontend
npm run dev
```

---

## 🧪 Tests

El proyecto incluye tests con pytest. Para ejecutarlos:

```bash
cd chatbot_project
pytest
```

Con cobertura:

```bash
pytest --cov=chatbot_app --cov-report=html
```

---

## 📁 Estructura del Proyecto

```
Chatbot/
├── chatbot_project/         # Backend Django
│   ├── chatbot_app/         # Aplicación principal (models, views, services)
│   ├── chatbot_project/     # Configuración (settings, urls)
│   ├── manage.py
│   └── pytest.ini
├── frontend/                # Frontend React + Vite
│   ├── src/
│   │   ├── components/      # Componentes React (Spinner, etc.)
│   │   ├── hooks/           # Custom hooks (useChat)
│   │   ├── main.jsx
│   │   └── index.css
│   ├── package.json
│   └── vite.config.js
├── docker-compose.yml       # PostgreSQL + Redis
├── requirements.txt         # Dependencias Python
├── init_project.sh          # Script de inicialización
└── .clinerules              # Reglas del proyecto para asistentes
```

---

## ⚠️ Notas de Configuración Importantes

| Configuración            | Detalle                                                                 |
| ------------------------ | ----------------------------------------------------------------------- |
| 🔐 Permisos por defecto     | `AllowAny`. Se recomienda cambiar a autenticación JWT/session antes de producción. |
| 🌐 CORS                     | `CORS_ALLOW_ALL_ORIGINS = True` permite cualquier origen. En producción, restringe a `CORS_ALLOWED_ORIGINS`. |
| 💬 Memoria conversacional   | TTL: 1800s (30 min). Ventana máxima: 20 mensajes por conversación. Ajustable en `.env`. |
| 📊 pgvector                 | Requiere la extensión `vector` habilitada en PostgreSQL para campos de tipo `VectorField`. |
| 🦙 Ollama                   | El backend se conecta a Ollama vía HTTP. Verifica que el servicio esté activo antes de iniciar el backend. |

---

## 📄 Licencia

Este proyecto se distribuye bajo la licencia [MIT/Apache 2.0/Personal] – reemplaza con tu elección.

---

💡 **¿Necesitas ayuda para configurar autenticación, endpoints o despliegue en producción?** ¡Avísame y te guío paso a paso!
