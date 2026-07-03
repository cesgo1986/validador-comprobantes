"""
services/dashboard_service.py — Queries que alimentan los endpoints /api/v1/dashboard/*.

Todos los queries filtran por empresa_id. En este MVP siempre es
DEFAULT_EMPRESA_ID, pero la firma de cada funcion ya recibe empresa_id
como parametro para no requerir cambios cuando se active multiempresa
real con autenticacion.
"""
import datetime
from sqlalchemy import select, func, desc, or_
from models.analisis import Analisis
from models.hash_documento import HashDocumento
from database import get_db_session, DEFAULT_EMPRESA_ID


def obtener_stats(empresa_id: str = DEFAULT_EMPRESA_ID, fecha_desde: str | None = None, fecha_hasta: str | None = None) -> dict:
    """
    Metricas generales: total de analisis, analisis de hoy, score
    promedio, y distribucion por nivel de riesgo.
    """
    with get_db_session() as db:
        if db is None:
            return {
                "total_analisis": 0, "analisis_hoy": 0, "score_promedio": None,
                "distribucion_riesgo": [], "documentos_unicos": 0, "documentos_reutilizados": 0,
            }

        base_filtro = [Analisis.empresa_id == empresa_id, Analisis.deleted_at.is_(None)]
        if fecha_desde:
            base_filtro.append(Analisis.fecha >= fecha_desde)
        if fecha_hasta:
            base_filtro.append(Analisis.fecha <= fecha_hasta)

        total = db.execute(select(func.count(Analisis.id)).where(*base_filtro)).scalar() or 0

        hoy = datetime.date.today()
        analisis_hoy = db.execute(
            select(func.count(Analisis.id)).where(
                Analisis.empresa_id == empresa_id,
                Analisis.deleted_at.is_(None),
                func.date(Analisis.fecha) == hoy,
            )
        ).scalar() or 0

        score_promedio = db.execute(select(func.avg(Analisis.score_final)).where(*base_filtro)).scalar()

        distribucion_rows = db.execute(
            select(Analisis.riesgo, func.count(Analisis.id))
            .where(*base_filtro)
            .group_by(Analisis.riesgo)
        ).all()
        distribucion_riesgo = [{"riesgo": r or "INDETERMINADO", "total": c} for r, c in distribucion_rows]

        documentos_unicos = db.execute(
            select(func.count(HashDocumento.id)).where(
                HashDocumento.empresa_id == empresa_id,
                HashDocumento.deleted_at.is_(None),
            )
        ).scalar() or 0

        documentos_reutilizados = db.execute(
            select(func.count(HashDocumento.id)).where(
                HashDocumento.empresa_id == empresa_id,
                HashDocumento.deleted_at.is_(None),
                HashDocumento.veces_visto > 1,
            )
        ).scalar() or 0

        return {
            "total_analisis": total,
            "analisis_hoy": analisis_hoy,
            "score_promedio": round(float(score_promedio), 2) if score_promedio is not None else None,
            "distribucion_riesgo": distribucion_riesgo,
            "documentos_unicos": documentos_unicos,
            "documentos_reutilizados": documentos_reutilizados,
        }


def _parsear_monto_busqueda(texto: str) -> float | None:
    """
    Si el texto de búsqueda es interpretable como un monto (ej. '1234.56'
    o '1,234.56'), lo devuelve como float. Si no, devuelve None -- no es
    un error, simplemente significa que esta búsqueda no aplica al campo
    monto_detectado.
    """
    try:
        return float(texto.replace(",", "").replace("$", "").strip())
    except (ValueError, AttributeError):
        return None


def listar_analisis(
    empresa_id: str = DEFAULT_EMPRESA_ID,
    limit: int = 50,
    offset: int = 0,
    riesgo: str | None = None,
    estado_operacion: str | None = None,
    hash_sha256: str | None = None,
    banco: str | None = None,
    fecha_desde: str | None = None,
    fecha_hasta: str | None = None,
    q: str | None = None,
) -> dict:
    """
    Listado paginado de analisis, mas reciente primero.

    Item 2.2 (ROADMAP.md, Etapa 2): `q` es la búsqueda unificada -- el
    usuario escribe una sola cosa (banco, clave de rastreo, referencia,
    CLABE, o un monto) y el backend decide dónde buscarlo, en vez de que
    el usuario tenga que elegir el campo. Se combina con OR entre
    banco_detectado, clave_rastreo, referencia y clabe_detectada
    (coincidencia parcial), y adicionalmente compara contra
    monto_detectado si el texto es interpretable como número.

    `banco` se mantiene por separado como filtro exacto/avanzado --
    no se elimina para no romper consumidores que ya lo usan.
    """
    with get_db_session() as db:
        if db is None:
            return {"items": [], "total": 0}

        filtros = [Analisis.empresa_id == empresa_id, Analisis.deleted_at.is_(None)]
        if riesgo:
            filtros.append(Analisis.riesgo == riesgo)
        if estado_operacion:
            filtros.append(Analisis.estado_operacion == estado_operacion)
        if hash_sha256:
            filtros.append(Analisis.hash_sha256 == hash_sha256)
        if banco:
            filtros.append(Analisis.banco_detectado.ilike(f"%{banco}%"))
        if fecha_desde:
            filtros.append(Analisis.fecha >= fecha_desde)
        if fecha_hasta:
            filtros.append(Analisis.fecha <= fecha_hasta)

        if q and q.strip():
            texto = q.strip()
            condiciones_q = [
                Analisis.banco_detectado.ilike(f"%{texto}%"),
                Analisis.clave_rastreo.ilike(f"%{texto}%"),
                Analisis.referencia.ilike(f"%{texto}%"),
                Analisis.clabe_detectada.ilike(f"%{texto}%"),
            ]
            monto_interpretado = _parsear_monto_busqueda(texto)
            if monto_interpretado is not None:
                condiciones_q.append(Analisis.monto_detectado == monto_interpretado)
            filtros.append(or_(*condiciones_q))

        total = db.execute(select(func.count(Analisis.id)).where(*filtros)).scalar() or 0

        rows = db.execute(
            select(Analisis, HashDocumento.veces_visto)
            .outerjoin(
                HashDocumento,
                (HashDocumento.hash_sha256 == Analisis.hash_sha256)
                & (HashDocumento.empresa_id == Analisis.empresa_id),
            )
            .where(*filtros)
            .order_by(desc(Analisis.fecha))
            .limit(limit)
            .offset(offset)
        ).all()

        items = [
            {
                "id": str(r.id),
                "fecha": r.fecha.isoformat() if r.fecha else None,
                "hash_sha256": r.hash_sha256,
                "score_claude": float(r.score_claude) if r.score_claude is not None else None,
                "score_iat": float(r.score_iat) if r.score_iat is not None else None,
                "score_final": float(r.score_final) if r.score_final is not None else None,
                "riesgo": r.riesgo,
                "estado_operacion": r.estado_operacion,
                "fuente_estado": r.fuente_estado,
                "nivel_evidencia": r.nivel_evidencia,
                "clave_rastreo": r.clave_rastreo,
                "referencia": r.referencia,
                "tipo_transferencia": r.tipo_transferencia,
                "archivo_nombre": r.archivo_nombre,
                "banco_detectado": r.banco_detectado,
                "monto_detectado": float(r.monto_detectado) if r.monto_detectado is not None else None,
                "veces_visto": veces_visto if veces_visto else 1,
            }
            for r, veces_visto in rows
        ]
        return {"items": items, "total": total}


def obtener_analisis_detalle(analisis_id: str, empresa_id: str = DEFAULT_EMPRESA_ID) -> dict | None:
    """Detalle completo de un analisis, incluyendo el JSONB resultado y el historial del hash."""
    with get_db_session() as db:
        if db is None:
            return None

        registro = db.execute(
            select(Analisis).where(
                Analisis.id == analisis_id,
                Analisis.empresa_id == empresa_id,
                Analisis.deleted_at.is_(None),
            )
        ).scalar_one_or_none()

        if registro is None:
            return None

        historial_hash = None
        if registro.hash_sha256:
            hash_row = db.execute(
                select(HashDocumento).where(
                    HashDocumento.empresa_id == empresa_id,
                    HashDocumento.hash_sha256 == registro.hash_sha256,
                )
            ).scalar_one_or_none()
            if hash_row:
                historial_hash = {
                    "veces_visto": hash_row.veces_visto,
                    "primer_analisis": hash_row.primer_analisis.isoformat(),
                    "ultimo_analisis": hash_row.ultimo_analisis.isoformat(),
                }

        return {
            "id": str(registro.id),
            "fecha": registro.fecha.isoformat() if registro.fecha else None,
            "hash_sha256": registro.hash_sha256,
            "score_claude": float(registro.score_claude) if registro.score_claude is not None else None,
            "score_iat": float(registro.score_iat) if registro.score_iat is not None else None,
            "score_final": float(registro.score_final) if registro.score_final is not None else None,
            "riesgo": registro.riesgo,
            "estado_operacion": registro.estado_operacion,
            "fuente_estado": registro.fuente_estado,
            "nivel_evidencia": registro.nivel_evidencia,
            "clave_rastreo": registro.clave_rastreo,
            "referencia": registro.referencia,
            "tipo_transferencia": registro.tipo_transferencia,
            "archivo_nombre": registro.archivo_nombre,
            "archivo_tipo": registro.archivo_tipo,
            "monto_detectado": float(registro.monto_detectado) if registro.monto_detectado is not None else None,
            "banco_detectado": registro.banco_detectado,
            "clabe_detectada": registro.clabe_detectada,
            "resultado": registro.resultado,
            "historial_hash": historial_hash,
        }


def top_hashes_reutilizados(empresa_id: str = DEFAULT_EMPRESA_ID, min_veces: int = 2, limit: int = 20) -> list:
    """Hashes con mayor veces_visto -- el primer detector de fraude recurrente."""
    with get_db_session() as db:
        if db is None:
            return []

        rows = db.execute(
            select(HashDocumento)
            .where(
                HashDocumento.empresa_id == empresa_id,
                HashDocumento.deleted_at.is_(None),
                HashDocumento.veces_visto >= min_veces,
            )
            .order_by(desc(HashDocumento.veces_visto))
            .limit(limit)
        ).scalars().all()

        resultado = []
        for h in rows:
            riesgo_max_row = db.execute(
                select(Analisis.riesgo)
                .where(Analisis.empresa_id == empresa_id, Analisis.hash_sha256 == h.hash_sha256)
                .order_by(desc(Analisis.score_final))
                .limit(1)
            ).scalar_one_or_none()

            resultado.append({
                "hash_sha256": h.hash_sha256,
                "veces_visto": h.veces_visto,
                "primer_analisis": h.primer_analisis.isoformat(),
                "ultimo_analisis": h.ultimo_analisis.isoformat(),
                "riesgo_max": riesgo_max_row,
            })
        return resultado


def tendencia_diaria(empresa_id: str = DEFAULT_EMPRESA_ID, dias: int = 30) -> list:
    """Serie diaria de totales y score promedio, para graficar tendencias."""
    with get_db_session() as db:
        if db is None:
            return []

        desde = datetime.date.today() - datetime.timedelta(days=dias)

        rows = db.execute(
            select(
                func.date(Analisis.fecha).label("dia"),
                func.count(Analisis.id),
                func.avg(Analisis.score_final),
            )
            .where(
                Analisis.empresa_id == empresa_id,
                Analisis.deleted_at.is_(None),
                Analisis.fecha >= desde,
            )
            .group_by(func.date(Analisis.fecha))
            .order_by(func.date(Analisis.fecha))
        ).all()

        return [
            {
                "fecha": dia.isoformat() if hasattr(dia, "isoformat") else str(dia),
                "total": total,
                "score_promedio": round(float(score_avg), 2) if score_avg is not None else None,
            }
            for dia, total, score_avg in rows
        ]


def distribucion_scores_por_banco(empresa_id: str = DEFAULT_EMPRESA_ID, dias: int = 30, min_analisis: int = 1) -> list:
    """
    Item 1.6 (Observabilidad): distribucion de scores por banco detectado,
    de los ultimos `dias`.

    Nota de nomenclatura importante: "score_claude" es el score de riesgo
    visual/documental que devuelve Claude Vision (0=bajo riesgo,
    100=critico) -- no es una metrica de confianza de OCR en si misma.
    """
    with get_db_session() as db:
        if db is None:
            return []

        desde = datetime.date.today() - datetime.timedelta(days=dias)

        rows = db.execute(
            select(
                Analisis.banco_detectado,
                func.count(Analisis.id),
                func.avg(Analisis.score_claude),
                func.avg(Analisis.score_final),
            )
            .where(
                Analisis.empresa_id == empresa_id,
                Analisis.deleted_at.is_(None),
                Analisis.fecha >= desde,
                Analisis.banco_detectado.is_not(None),
            )
            .group_by(Analisis.banco_detectado)
            .having(func.count(Analisis.id) >= min_analisis)
            .order_by(desc(func.count(Analisis.id)))
        ).all()

        return [
            {
                "banco": banco,
                "total_analisis": total,
                "score_claude_promedio": round(float(score_claude_avg), 2) if score_claude_avg is not None else None,
                "score_final_promedio": round(float(score_final_avg), 2) if score_final_avg is not None else None,
            }
            for banco, total, score_claude_avg, score_final_avg in rows
        ]