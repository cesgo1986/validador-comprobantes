"""
Script de diagnostico extendido. Correr con:
    python diagnostico.py

Borrar este archivo despues de usarlo (no es parte del proyecto).
"""
import os
from dotenv import load_dotenv

load_dotenv()

db_url = os.getenv("DATABASE_URL")

print("=" * 60)
print("PASO 1: Verificando si DATABASE_URL se lee del .env")
print("=" * 60)

if db_url is None:
    print("ERROR: DATABASE_URL no se encontro en el entorno.")
    print("Revisa que tu archivo .env tenga una linea exacta:")
    print("DATABASE_URL=postgresql://...")
    print("Y que el .env este en la misma carpeta donde corres este script.")
else:
    safe = db_url
    if "@" in safe and "://" in safe:
        try:
            scheme, rest = safe.split("://", 1)
            creds, hostpart = rest.split("@", 1)
            user = creds.split(":")[0]
            safe = scheme + "://" + user + ":***@" + hostpart
        except Exception:
            pass
    print("OK: DATABASE_URL encontrada:")
    print(safe)

print()
print("=" * 60)
print("PASO 2: Intentando inicializar la base de datos (crear tablas)")
print("=" * 60)

try:
    from database import init_db
    resultado = init_db()
    print("init_db() devolvio:", resultado)
    if resultado:
        print("EXITO: las tablas deberian existir ahora en Supabase.")
    else:
        print("init_db() devolvio False -> DATABASE_URL no configurada o engine es None.")
except Exception as e:
    print("ERROR al ejecutar init_db():")
    print(type(e).__name__, "-", str(e))

print()
print("=" * 60)
print("PASO 3: Probando guardar un hash de prueba")
print("=" * 60)

try:
    from services.hash_service import registrar_y_consultar_hash
    resultado_hash = registrar_y_consultar_hash(b"contenido de prueba diagnostico")
    print("registrar_y_consultar_hash() devolvio:")
    print(resultado_hash)
    if resultado_hash.get("primer_analisis") is None:
        print("AVISO: primer_analisis es None -> probablemente NO se guardo en la DB (degradacion sin DB).")
    else:
        print("EXITO: parece haberse guardado correctamente.")
except Exception as e:
    print("ERROR al ejecutar registrar_y_consultar_hash():")
    print(type(e).__name__, "-", str(e))

print()
print("=" * 60)
print("PASO 4: Probando guardar un registro de auditoria de prueba")
print("=" * 60)

try:
    from services.auditoria_service import guardar_analisis
    audit_id = guardar_analisis(
        hash_sha256="hash_de_prueba_diagnostico",
        score_claude=10.0,
        score_iat=20.0,
        score_final=15.0,
        riesgo="BAJO",
        resultado={"diagnostico": True},
    )
    print("guardar_analisis() devolvio audit_id:", audit_id)
    if audit_id is None:
        print("AVISO: audit_id es None -> probablemente NO se guardo en la DB.")
    else:
        print("EXITO: el registro deberia existir en la tabla 'analisis' de Supabase ahora.")
        print("Ve a Supabase -> Table Editor -> analisis -> busca hash_sha256 = 'hash_de_prueba_diagnostico'")
except Exception as e:
    print("ERROR al ejecutar guardar_analisis():")
    print(type(e).__name__, "-", str(e))

print()
print("=" * 60)
print("Diagnostico completo.")
print("=" * 60)