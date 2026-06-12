"""
IAT — Índice de Autenticidad Transaccional
Motor matemático independiente de Claude.
Calcula score de autenticidad basado en:
  - Entropía de clave de rastreo
  - Z-score de longitud de campos
  - Rareza estadística por banco
  - Coherencia temporal
  - Patrones combinados
"""

import math
import re
from datetime import datetime, time
from typing import Optional


# ─────────────────────────────────────────────
# ESTADÍSTICAS BASE POR BANCO
# Longitudes esperadas de campos SPEI reales
# (media y desviación estándar)
# ─────────────────────────────────────────────
BANK_STATS = {
    "BBVA": {
        "referencia": {"mean": 7.0, "std": 1.5},
        "clave_rastreo": {"mean": 18.0, "std": 2.0},
        "folio": {"mean": 8.0, "std": 2.0},
        "entropia_min": 2.5,
    },
    "SANTANDER": {
        "referencia": {"mean": 7.0, "std": 1.5},
        "clave_rastreo": {"mean": 18.0, "std": 2.0},
        "folio": {"mean": 7.0, "std": 1.5},
        "entropia_min": 2.5,
    },
    "BANORTE": {
        "referencia": {"mean": 6.0, "std": 1.5},
        "clave_rastreo": {"mean": 18.0, "std": 2.0},
        "folio": {"mean": 8.0, "std": 2.0},
        "entropia_min": 2.5,
    },
    "HSBC": {
        "referencia": {"mean": 7.0, "std": 1.5},
        "clave_rastreo": {"mean": 18.0, "std": 2.0},
        "folio": {"mean": 7.0, "std": 1.5},
        "entropia_min": 2.5,
    },
    "AZTECA": {
        "referencia": {"mean": 6.0, "std": 1.5},
        "clave_rastreo": {"mean": 18.0, "std": 2.0},
        "folio": {"mean": 7.0, "std": 2.0},
        "entropia_min": 2.0,
    },
    "MERCADO PAGO": {
        "referencia": {"mean": 8.0, "std": 2.0},
        "clave_rastreo": {"mean": 18.0, "std": 2.0},
        "folio": {"mean": 8.0, "std": 2.0},
        "entropia_min": 2.5,
    },
    "DEFAULT": {
        "referencia": {"mean": 7.0, "std": 2.0},
        "clave_rastreo": {"mean": 18.0, "std": 2.5},
        "folio": {"mean": 7.0, "std": 2.0},
        "entropia_min": 2.0,
    },
}

# Horarios SPEI en México (hora local CST/CDT)
SPEI_START = time(0, 0)   # 00:00
SPEI_END   = time(23, 59) # 23:59
SPEI_MAINTENANCE_START = time(22, 0)  # mantenimiento domingos
SPEI_MAINTENANCE_END   = time(23, 59)

# Días de semana (0=lunes, 6=domingo)
WEEKEND_DAYS = {5, 6}  # sábado y domingo


# ─────────────────────────────────────────────
# FUNCIONES MATEMÁTICAS CORE
# ─────────────────────────────────────────────

def entropy(s: str) -> float:
    """Calcula la entropía de Shannon de un string."""
    if not s:
        return 0.0
    freq: dict = {}
    for c in s:
        freq[c] = freq.get(c, 0) + 1
    return -sum(
        (f / len(s)) * math.log2(f / len(s))
        for f in freq.values()
    )


def z_score(x: float, mean: float, std: float) -> float:
    """Calcula el Z-score normalizado."""
    if std == 0:
        return 0.0
    return (x - mean) / std


def normalize_bank_name(banco: Optional[str]) -> str:
    """Normaliza el nombre del banco para buscar en BANK_STATS."""
    if not banco:
        return "DEFAULT"
    banco_upper = banco.upper()
    for key in BANK_STATS:
        if key in banco_upper:
            return key
    return "DEFAULT"


def clean_field(value: Optional[str]) -> str:
    """Limpia un campo extraído."""
    if not value:
        return ""
    return re.sub(r"\s+", "", str(value)).strip()


def parse_hour(hora: Optional[str]) -> Optional[int]:
    """Extrae la hora de un string de tiempo."""
    if not hora:
        return None
    match = re.search(r"(\d{1,2}):", hora)
    if match:
        return int(match.group(1))
    return None


def parse_date(fecha: Optional[str]) -> Optional[datetime]:
    """Intenta parsear una fecha en varios formatos."""
    if not fecha:
        return None
    formats = [
        "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y",
        "%d/%b/%Y", "%d de %B de %Y",
        "%d/%m/%y", "%Y/%m/%d",
    ]
    meses = {
        "enero": "January", "febrero": "February", "marzo": "March",
        "abril": "April", "mayo": "May", "junio": "June",
        "julio": "July", "agosto": "August", "septiembre": "September",
        "octubre": "October", "noviembre": "November", "diciembre": "December",
        "ene": "Jan", "feb": "Feb", "mar": "Mar", "abr": "Apr",
        "may": "May", "jun": "Jun", "jul": "Jul", "ago": "Aug",
        "sep": "Sep", "oct": "Oct", "nov": "Nov", "dic": "Dec",
    }
    fecha_norm = fecha.lower()
    for es, en in meses.items():
        fecha_norm = fecha_norm.replace(es, en)
    for fmt in formats:
        try:
            return datetime.strptime(fecha_norm.strip(), fmt)
        except ValueError:
            continue
    return None


# ─────────────────────────────────────────────
# MÓDULOS DE ANÁLISIS
# ─────────────────────────────────────────────

def analyze_entropy(clave_rastreo: str, bank_stats: dict) -> dict:
    """Analiza la entropía de la clave de rastreo."""
    e = entropy(clave_rastreo)
    min_entropy = bank_stats.get("entropia_min", 2.0)
    penalty = 0.0
    anomalia = None

    if e < min_entropy and clave_rastreo:
        penalty = (min_entropy - e) * 10
        anomalia = {
            "tipo": "entropia_baja",
            "descripcion": f"Clave de rastreo con baja entropía ({e:.2f} bits). Patrón repetitivo o generado artificialmente.",
            "severidad": "alta" if e < 1.5 else "media"
        }

    return {
        "entropia": round(e, 4),
        "penalty": round(penalty, 2),
        "anomalia": anomalia
    }


def analyze_field_lengths(campos: dict, bank_stats: dict) -> dict:
    """Calcula Z-scores de longitud de campos clave."""
    fields = ["referencia", "clave_rastreo", "folio"]
    z_scores = {}
    penalties = {}
    anomalias = []

    for field in fields:
        valor = clean_field(campos.get(field))
        if not valor:
            continue
        stats = bank_stats.get(field, {"mean": 7.0, "std": 2.0})
        z = z_score(len(valor), stats["mean"], stats["std"])
        z_scores[field] = round(z, 4)
        penalty = max(0, abs(z) - 1.5) * 8
        penalties[field] = round(penalty, 2)

        if abs(z) > 2.5:
            anomalias.append({
                "tipo": f"longitud_anomala_{field}",
                "descripcion": f"Campo '{field}' con longitud inusual (z={z:.2f}). Valor: '{valor}' ({len(valor)} caracteres).",
                "severidad": "alta" if abs(z) > 3.5 else "media"
            })

    return {
        "z_scores": z_scores,
        "penalties": penalties,
        "anomalias": anomalias
    }


def analyze_temporal(fecha: Optional[str], hora: Optional[str]) -> dict:
    """Analiza coherencia temporal de la operación."""
    penalty = 0.0
    anomalias = []
    hoy = datetime.now()

    fecha_parsed = parse_date(fecha)
    hora_int = parse_hour(hora)

    # Validar fecha
    if fecha_parsed:
        diff_dias = (hoy - fecha_parsed).days
        if fecha_parsed > hoy:
            penalty += 30
            anomalias.append({
                "tipo": "fecha_futura",
                "descripcion": f"La fecha del comprobante ({fecha}) es posterior a hoy. Altamente sospechoso.",
                "severidad": "alta"
            })
        elif diff_dias > 90:
            penalty += 15
            anomalias.append({
                "tipo": "fecha_antigua",
                "descripcion": f"El comprobante tiene {diff_dias} días de antigüedad. Inusual para uso comercial.",
                "severidad": "media"
            })
        # Verificar fin de semana
        if fecha_parsed.weekday() == 6 and hora_int is not None and hora_int >= 22:
            penalty += 20
            anomalias.append({
                "tipo": "horario_mantenimiento",
                "descripcion": "Transferencia en horario de mantenimiento SPEI (domingos 22:00+).",
                "severidad": "alta"
            })

    # Validar hora
    if hora_int is not None:
        if hora_int < 0 or hora_int > 23:
            penalty += 20
            anomalias.append({
                "tipo": "hora_invalida",
                "descripcion": f"Hora inválida detectada: {hora}.",
                "severidad": "alta"
            })

    return {
        "penalty": round(penalty, 2),
        "anomalias": anomalias,
        "fecha_parsed": fecha_parsed.strftime("%Y-%m-%d") if fecha_parsed else None
    }


def analyze_monto(monto: Optional[str]) -> dict:
    """Analiza patrones sospechosos en el monto."""
    penalty = 0.0
    anomalias = []

    if not monto:
        return {"penalty": 0.0, "anomalias": [], "monto_numerico": None}

    # Limpiar y extraer valor numérico
    monto_clean = re.sub(r"[^\d.]", "", str(monto).replace(",", ""))
    try:
        valor = float(monto_clean)
    except ValueError:
        return {"penalty": 0.0, "anomalias": [], "monto_numerico": None}

    # Monto cero
    if valor == 0:
        penalty += 40
        anomalias.append({
            "tipo": "monto_cero",
            "descripcion": "El monto de la transferencia es $0.00.",
            "severidad": "alta"
        })

    # Monto redondo sospechoso (múltiplo exacto de 1000 mayor a 5000)
    if valor > 5000 and valor % 1000 == 0:
        penalty += 5
        anomalias.append({
            "tipo": "monto_redondo",
            "descripcion": f"Monto redondo exacto (${valor:,.0f}). Más frecuente en fraudes que en transacciones naturales.",
            "severidad": "info"
        })

    return {
        "penalty": round(penalty, 2),
        "anomalias": anomalias,
        "monto_numerico": valor
    }


def analyze_combined_patterns(campos: dict, banco: str) -> dict:
    """
    Analiza combinaciones de variables para detectar patrones
    que individualmente parecen normales pero juntos son sospechosos.
    """
    penalty = 0.0
    anomalias = []

    ref = clean_field(campos.get("referencia"))
    clave = clean_field(campos.get("clave_rastreo"))
    folio = clean_field(campos.get("folio"))

    # Patrón: referencia == folio (copia exacta)
    if ref and folio and ref == folio:
        penalty += 15
        anomalias.append({
            "tipo": "referencia_igual_folio",
            "descripcion": "La referencia y el folio son idénticos. Patrón inusual en comprobantes reales.",
            "severidad": "media"
        })

    # Patrón: campos completamente numéricos simples (111111, 123456)
    for field_name, field_val in [("referencia", ref), ("folio", folio)]:
        if field_val and len(field_val) >= 4:
            if len(set(field_val)) <= 2:
                penalty += 12
                anomalias.append({
                    "tipo": f"campo_repetitivo_{field_name}",
                    "descripcion": f"El campo '{field_name}' tiene muy poca variación de caracteres: '{field_val}'.",
                    "severidad": "media"
                })
            if field_val in ["123456", "000000", "111111", "999999", "123123"]:
                penalty += 20
                anomalias.append({
                    "tipo": f"campo_generico_{field_name}",
                    "descripcion": f"El campo '{field_name}' tiene un valor genérico o de prueba: '{field_val}'.",
                    "severidad": "alta"
                })

    # Patrón: clave de rastreo con formato SPEI válido
    # Formato real: MBAN + fecha8 + 10dígitos = 22 chars aprox
    if clave:
        spei_pattern = re.match(r"^[A-Z]{4}\d{8}\d+$", clave)
        if not spei_pattern and len(clave) > 5:
            penalty += 8
            anomalias.append({
                "tipo": "formato_clave_atipico",
                "descripcion": f"La clave de rastreo '{clave}' no sigue el patrón SPEI estándar (BANKYYYYMMDDNNNN).",
                "severidad": "media"
            })

    return {
        "penalty": round(penalty, 2),
        "anomalias": anomalias
    }


# ─────────────────────────────────────────────
# FUNCIÓN PRINCIPAL DEL MOTOR IAT
# ─────────────────────────────────────────────

def calculate_iat(campos: dict, banco_origen: Optional[str] = None) -> dict:
    """
    Calcula el IAT Score a partir de los campos extraídos.
    
    Args:
        campos: dict con campos extraídos por Claude
        banco_origen: nombre del banco emisor
    
    Returns:
        dict con iat_score, anomalias y métricas detalladas
    """
    banco_norm = normalize_bank_name(banco_origen)
    bank_stats = BANK_STATS.get(banco_norm, BANK_STATS["DEFAULT"])

    clave_rastreo = clean_field(campos.get("clave_rastreo"))

    # Ejecutar análisis por módulo
    entropy_result   = analyze_entropy(clave_rastreo, bank_stats)
    lengths_result   = analyze_field_lengths(campos, bank_stats)
    temporal_result  = analyze_temporal(campos.get("fecha"), campos.get("hora"))
    monto_result     = analyze_monto(campos.get("monto"))
    patterns_result  = analyze_combined_patterns(campos, banco_norm)

    # Calcular penalización total
    total_penalty = (
        entropy_result["penalty"] +
        sum(lengths_result["penalties"].values()) +
        temporal_result["penalty"] +
        monto_result["penalty"] +
        patterns_result["penalty"]
    )

    # IAT Score base: 100 - penalizaciones
    iat_score = max(0.0, min(100.0, 100.0 - total_penalty))

    # Recopilar todas las anomalías
    anomalias = []
    if entropy_result["anomalia"]:
        anomalias.append(entropy_result["anomalia"])
    anomalias.extend(lengths_result["anomalias"])
    anomalias.extend(temporal_result["anomalias"])
    anomalias.extend(monto_result["anomalias"])
    anomalias.extend(patterns_result["anomalias"])

    return {
        "iat_score": round(iat_score, 2),
        "banco_analizado": banco_norm,
        "anomalias": anomalias,
        "metricas": {
            "entropia_clave": entropy_result["entropia"],
            "z_scores": lengths_result["z_scores"],
            "penalizacion_total": round(total_penalty, 2),
            "desglose": {
                "entropia": entropy_result["penalty"],
                "longitudes": sum(lengths_result["penalties"].values()),
                "temporal": temporal_result["penalty"],
                "monto": monto_result["penalty"],
                "patrones": patterns_result["penalty"],
            }
        }
    }


def fuse_scores(claude_score: float, iat_score: float) -> float:
    """
    Fusiona el score de Claude con el IAT Score.
    FINAL = 0.7 * CLAUDE + 0.3 * IAT
    """
    return round(0.7 * claude_score + 0.3 * iat_score, 2)


def iat_anomalias_to_validaciones(anomalias: list) -> list:
    """Convierte anomalías IAT al formato de validaciones del frontend."""
    severidad_to_status = {
        "alta": "fail",
        "media": "warn",
        "info": "info",
    }
    result = []
    for a in anomalias:
        result.append({
            "categoria": "reputacion",
            "nombre": f"IAT: {a.get('tipo', 'anomalia').replace('_', ' ').title()}",
            "status": severidad_to_status.get(a.get("severidad", "media"), "warn"),
            "detalle": a.get("descripcion", "")
        })
    return result
