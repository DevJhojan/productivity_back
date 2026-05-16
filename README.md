# Productivity Back

Backend API de productividad y gamificacion, construido con Django y PostgreSQL.

## Resumen

La API actualmente soporta:

- Gestion de usuarios con modelo personalizado.
- Gestion de atributos por usuario: Strength, Vitality, Agility, Intelligence, Perception.
- Gestion de tareas con asignacion de atributo y puntos por completado.
- Gestion de habitos con check diario y streak.
- Gestion de goals con subtype y puntos por tipo.
- Cambio dedicado de estado para task y goals con suma/resta de puntos al entrar/salir de COMPLETED.

## Stack

- Python 3.14+
- Django 6.x
- PostgreSQL

## Arquitectura

El proyecto sigue una estructura modular por app y una separacion por capas:

- serializer: transforma entidades a JSON.
- service: concentra logica de negocio.
- views: manejo HTTP y despacho por metodo.
- urls: exposicion de endpoints.

Apps principales:

- users
- task
- habits
- goals

## Configuracion local

1. Crear y activar entorno virtual.

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Linux/macOS:

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Instalar dependencias.

```bash
pip install django psycopg2-binary
```

3. Verificar base de datos PostgreSQL.

- DB: Productividad
- Puerto: 5432

4. Ejecutar migraciones.

```bash
py manage.py makemigrations
py manage.py migrate
```

5. Levantar servidor.

```bash
py manage.py runserver
```

Base local:

- http://127.0.0.1:8000/

## Endpoints API

### Users

- GET /api/users/
- POST /api/users/
- GET /api/users/{user_id}/
- PUT /api/users/{user_id}/
- PATCH /api/users/{user_id}/
- DELETE /api/users/{user_id}/

### Tasks

- GET /api/tasks/
- POST /api/tasks/
- GET /api/tasks/{task_id}/
- PUT /api/tasks/{task_id}/
- PATCH /api/tasks/{task_id}/
- DELETE /api/tasks/{task_id}/
- POST /api/tasks/{task_id}/status/

`POST /api/tasks/{task_id}/status/` recibe:

```json
{
  "status": "PENDING | IN_PROGRESS | COMPLETED"
}
```

Regla de puntos para status:

- No COMPLETED -> COMPLETED: suma 0.10 al atributo asociado.
- COMPLETED -> no COMPLETED: resta 0.10 al atributo asociado.
- Entre PENDING e IN_PROGRESS: no modifica puntos.

### Habits

- GET /api/habits/
- POST /api/habits/
- GET /api/habits/{habit_id}/
- PATCH /api/habits/{habit_id}/
- DELETE /api/habits/{habit_id}/
- POST /api/habits/{habit_id}/check/
- DELETE /api/habits/{habit_id}/check/

### Goals

- GET /api/goals/
- POST /api/goals/
- GET /api/goals/{goal_id}/
- PATCH /api/goals/{goal_id}/
- DELETE /api/goals/{goal_id}/
- POST /api/goals/{goal_id}/status/

`POST /api/goals/{goal_id}/status/` recibe:

```json
{
  "status": "PENDING | IN_PROGRESS | COMPLETED"
}
```

Regla de puntos para status:

- No COMPLETED -> COMPLETED: suma segun goal_subtype.
- COMPLETED -> no COMPLETED: resta esos mismos puntos.
- Entre PENDING e IN_PROGRESS: no modifica puntos.

Puntos por goal_subtype:

- weekly_goal: 1.00
- monthly_project: 5.00
- annual_project: 15.00
- five_year_project: 30.00

## Valores validos

Status:

- PENDING
- IN_PROGRESS
- COMPLETED

Priority (task y goals):

- IMPORTANT_URGENT
- IMPORTANT_NOT_URGENT
- NOT_IMPORTANT_URGENT
- NOT_IMPORTANT_NOT_URGENT

Goal subtype:

- weekly_goal
- monthly_project
- annual_project
- five_year_project

## Pruebas

Ejecutar suite completa:

```bash
py manage.py test --verbosity=1
```

Ejecutar modulos puntuales:

```bash
py manage.py test task goals habits users --verbosity=2
```

## Notas de seguridad

- No usar credenciales hardcodeadas en produccion.
- Desactivar DEBUG en produccion.
- Configurar ALLOWED_HOSTS.
- Mover SECRET_KEY y DATABASES a variables de entorno.
