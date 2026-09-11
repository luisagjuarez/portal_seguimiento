# Respaldo y restauración de la base de datos

## Respaldo diario (`backup_postgres.sh`)

Corre `pg_dump` dentro del contenedor `postgres_db` y guarda un `.sql.gz` con fecha en
`/u01/RESPALDOS_BD` (o la carpeta que indique `BACKUP_DIR`). Borra automáticamente los
respaldos con más de `BACKUP_RETENTION_DAYS` días (30 por defecto).

Instalado por cron en `t_apex` (ver `crontab -l` del usuario `analitica`), corre todos los
días a la 1:00 am.

## Restauración (`restore_postgres.sh`)

Uso: `./restore_postgres.sh /ruta/al/respaldo.sql.gz` — sobrescribe la base de datos actual,
pide confirmación explícita (`SI`). Pensado para dos escenarios:

- **El servidor sigue vivo pero la BD se corrompió/perdió datos**: basta con correr el
  script apuntando al último `.sql.gz` de `/u01/RESPALDOS_BD`.
- **Reconstruir todo el aplicativo desde cero en un servidor nuevo** (el escenario de
  desastre real): antes de correr el script hay que recrear la infraestructura alrededor de
  la BD, porque el dump solo contiene los objetos, no el rol/base de datos contenedores:
  1. Levantar un contenedor Postgres nuevo con el mismo bind mount que hoy usa `postgres_db`
     (ver `docker inspect postgres_db` en el servidor viejo o en un respaldo de
     `docker-compose`/config si existiera uno).
  2. Crear el rol y la base: `CREATE ROLE dovela_control LOGIN PASSWORD '...'; CREATE DATABASE
     dovela_control OWNER dovela_control;` (ejecutado con `psql` como superusuario dentro del
     contenedor nuevo).
  3. Correr `restore_postgres.sh` apuntando al `.sql.gz` más reciente disponible (el que se
     tenga a mano fuera del servidor perdido — de ahí la importancia de copiar los respaldos
     fuera de `t_apex`, no solo dejarlos en `/u01/RESPALDOS_BD` local).
  4. Clonar el repo, configurar `.env` (ver `README.md` de la raíz) y `docker compose up -d
     --build`.

**Los respaldos hoy solo viven en `/u01/RESPALDOS_BD` en `t_apex`** (a pedido explícito del
usuario, 2026-09-11). Esto cubre corrupción/borrado accidental de datos, pero **no** cubre la
pérdida total de ese servidor — si eso es un riesgo real a mitigar, falta copiar los
respaldos a un destino externo (otro servidor, correo, almacenamiento en la nube).
