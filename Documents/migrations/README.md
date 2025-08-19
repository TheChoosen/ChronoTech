Migration instructions — ChronoTech

Purpose
-------
This folder contains schema changes required by recent application updates (technician fields, schedule JSON column, etc.).

Recommended procedure (production-safe)
--------------------------------------
1. Backup your database before applying any migration. Example (mysqldump):

   mysqldump -h <host> -u <user> -p<password> --databases bdm > bdm-backup.sql

2. Review migration file(s) in this folder. Important files:
   - 2025-08-18_add_technicians_columns.sql  (adds technician fields)
   - 2025-08-18_convert_schedule_json_to_json.sql  (converts schedule_json to JSON type)

3. Run the provided safe conversion script on the application host (it will create a backup column and fix invalid JSON then ALTER to JSON type):

   # run from repo root using the project's virtualenv
   PYTHONPATH=. ./venv/bin/python scripts/convert_schedule_json.py

   This script:
   - creates `schedule_json_bkp` if not present
   - copies existing `schedule_json` into the backup column
   - normalizes or replaces invalid JSON values
   - alters `schedule_json` to JSON NULL

4. If you prefer to run SQL manually, inspect the migration SQL and execute it with a DBA user with ALTER privileges:

   mysql -h <host> -u <user> -p
   USE bdm;
   -- inspect the migration file and run the ALTER statements

5. After applying migrations, restart the application process to pick up schema changes.

Notes & rollback
----------------
- The script creates `schedule_json_bkp` so you can inspect original values and restore if needed.
- If something goes wrong, restore from your mysqldump backup.

Why we removed runtime DDL
-------------------------
Performing DDL at runtime is risky in production (locks, permission needs, schema drift). Prefer explicit migrations run by operators with appropriate privileges and backup procedures.

Contact
-------
If you want, I can prepare a smaller migration PR that your ops team can review and apply.
