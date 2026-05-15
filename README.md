# Productivity Back

Backend API para gestión de tareas y usuarios, desarrollado con Django y PostgreSQL.

## Resumen

Este proyecto expone una API REST base para:

- Crear, consultar, actualizar y eliminar tareas.
- Asociar tareas a un usuario propietario.
- Sentar la base para registro y autenticación de usuarios con modelo personalizado.

Actualmente, el módulo de tareas está publicado en rutas API. El módulo de usuarios está en desarrollo y aún no está habilitado en el enrutamiento principal.

## Stack Tecnológico

- Python 3.x
- Django 6.x
- PostgreSQL

## Arquitectura

El proyecto usa una estructura modular por aplicación de Django:

- productivity_back: configuración global del proyecto.
- task: dominio de tareas (modelo, serialización, servicio y vistas).
- users: dominio de usuarios (modelo personalizado y capa de servicios en construcción).

### Patrón aplicado en task

El módulo task ya separa responsabilidades:

- task_serializer.py: serialización de entidades a diccionario JSON.
- task_service.py: lógica de negocio y operaciones CRUD.
- views.py: control HTTP y manejo de métodos.

Este patrón facilita pruebas, mantenimiento y escalabilidad.

## Estructura del proyecto

```text
manage.py
productivity_back/
  __init__.py
  asgi.py
  settings.py
  urls.py
  wsgi.py
task/
  admin.py
  apps.py
  models.py
  task_serializer.py
  task_service.py
  urls.py
  views.py
  migrations/
users/
  admin.py
  apps.py
  models.py
  users_serializer.py
  users_service.py
  views.py
  migrations/
```

## Configuración del entorno

### 1) Clonar e instalar dependencias

```bash
git clone <tu-repo>
cd productivity_back
python -m venv .venv
```

Activar entorno virtual:

- Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

- Linux/macOS:

```bash
source .venv/bin/activate
```

Instalar paquetes:

```bash
pip install django psycopg2-binary
```

### 2) Configurar base de datos PostgreSQL

En settings.py está configurada una base PostgreSQL local. Asegura que exista:

- Base de datos: Productividad
- Usuario: postgres
- Puerto: 5432

### 3) Migraciones

```bash
python manage.py makemigrations
python manage.py migrate
```

### 4) Ejecutar servidor

```bash
python manage.py runserver
```

Servidor local por defecto:

- http://127.0.0.1:8000/

## API disponible

Base URL:

- /api/

### Tareas

Rutas activas:

- GET /api/tasks/
- POST /api/tasks/
- GET /api/tasks/{task_id}/
- PUT /api/tasks/{task_id}/
- PATCH /api/tasks/{task_id}/
- DELETE /api/tasks/{task_id}/

#### Ejemplo de creación de tarea

```bash
curl -X POST http://127.0.0.1:8000/api/tasks/ \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Preparar demo",
    "description": "Demo semanal del equipo",
    "status": "PENDING",
    "priority": "IMPORTANT_URGENT",
    "owner_id": 1
  }'
```

#### Valores válidos para status

- PENDING
- IN_PROGRESS
- COMPLETED

#### Valores válidos para priority

- IMPORTANT_URGENT
- IMPORTANT_NOT_URGENT
- NOT_IMPORTANT_URGENT
- NOT_IMPORTANT_NOT_URGENT

## Modelos principales

### Task

Campos relevantes:

- title
- description
- status
- priority
- due_date
- completed_at
- owner (FK a AUTH_USER_MODEL)
- created_at
- updated_at

### User (módulo users)

El módulo users define:

- Person abstracto con información personal y tipo de documento (choices).
- User heredando de AbstractUser y Person.

Nota: aunque la base del modelo existe, esta app aún no está registrada en INSTALLED_APPS ni conectada en urls.py del proyecto principal.

## Estado actual y próximos pasos

### Completado

- API CRUD de tareas operativa.
- Separación básica por capas en task.
- Modelo de usuario personalizado en construcción.

### Recomendado para continuar

1. Registrar la app users en INSTALLED_APPS.
2. Definir AUTH_USER_MODEL con el modelo de usuario personalizado.
3. Crear users/urls.py e incluirlo en el enrutador principal.
4. Implementar endpoints de registro y login.
5. Agregar pruebas para task y users.
6. Mover credenciales de base de datos a variables de entorno.

## Seguridad y buenas prácticas

- No usar credenciales hardcodeadas en producción.
- Desactivar DEBUG en entornos productivos.
- Configurar ALLOWED_HOSTS.
- Usar variables de entorno para SECRET_KEY y DATABASES.

## Licencia

Define aquí la licencia del proyecto, por ejemplo MIT.
