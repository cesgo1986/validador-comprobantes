"""
IAT — Indice de Autenticidad Transaccional v2
Motor matematico independiente de Claude.
"""

import math
import re
from datetime import datetime
from typing import Optional


# ─────────────────────────────────────────────
# ESTADISTICAS BASE POR BANCO
# ─────────────────────────────────────────────
BANK_STATS = {
    "BBVA": {
        "referencia": {"mean": 7.0, "std": 1.5},
        "clave_rastreo": {"mean": 19.0, "std": 3.0},
        "folio": {"mean": 8.0, "std": 2.0},
        "entropia_min": 2.5,
    },
    "SANTANDER": {
        "referencia": {"mean": 7.0, "std": 1.5},
        "clave_rastreo": {"mean": 19.0, "std": 3.0},
        "folio": {"mean": 7.0, "std": 1.5},
        "entropia_min": 2.5,
    },
    "BANORTE": {
        "referencia": {"mean": 6.0, "std": 1.5},
        "clave_rastreo": {"mean": 19.0, "std": 3.0},
        "folio": {"mean": 8.0, "std": 2.0},
        "entropia_min": 2.5,
    },
    "HSBC": {
        "referencia": {"mean": 7.0, "std": 1.5},
        "clave_rastreo": {"mean": 19.0, "std": 3.0},
        "folio": {"mean": 7.0, "std": 1.5},
        "entropia_min": 2.5,
    },
    "AZTECA": {
        "referencia": {"mean": 6.0, "std": 2.0},
        "clave_rastreo": {"mean": 19.0, "std": 3.0},
        "folio": {"mean": 7.0, "std": 2.0},
        "entropia_min": 2.0,
    },
    "MERCADO PAGO": {
        "referencia": {"mean": 8.0, "std": 2.0},
        "clave_rastreo": {"mean": 19.0, "std": 3.0},
        "folio": {"mean": 8.0, "std": 2.0},
        "entropia_min": 2.5,
    },
    "DEFAULT": {
        "referencia": {"mean": 7.0, "std": 2.0},
        "clave_rastreo": {"mean": 19.0, "std": 3.0},
        "folio": {"mean": 7.0, "std": 2.0},
        "entropia_min": 2.0,
    },
}

# Leyendas estandar bancarias — NO son señal de fraude
LEYENDAS_NORMALES = [
    "datos no verificados por esta institucion",
    "datos no verificados",
    "no verificado por",
    "informacion no verificada",
    "pendiente de verificacion",
    "este vinculo se activara",
    "consulta el estatus en",
    "transferencia liquidada",
    "operacion liquidada",
]

# Formato valido de clave de rastreo SPEI
CLAVE_RASTREO_PATTERN = re.compile(r'^[A-Z]{3,4}\d{6,}[A-Z0-9]*$', re.IGNORECASE)


# ─────────────────────────────────────────────
# FUNCIONES MATEMATICAS CORE
# ─────────────────────────────────────────────

def entropy(s: str) -> float:
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
    if std == 0:
        return 0.0
    return (x - mean) / std


def normalize_bank_name(banco: Optional[str]) -> str:
    if not banco:
        return "DEFAULT"
    banco_upper = banco.upper()
    for key in BANK_STATS:
        if key in banco_upper:
            return key
    return "DEFAULT"


def clean_field(value: Optional[str]) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", "", str(value)).strip()


def parse_hour(hora: Optional[str]) -> Optional[int]:
    if not hora:
        return None
    match = re.search(r"(\d{1,2}):", hora)
    if match:
        return int(match.group(1))
    return None


def parse_date(fecha: Optional[str]) -> Optional[datetime]:
    if not fecha:
        return None
    formats = [
        "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y",
        "%d/%b/%Y", "%d de %B de %Y",
        "%d/%m/%y", "%Y/%m/%d",
        "%d/%b/%y",
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


def normalize_monto(monto_str: str) -> float:
    """Normaliza un monto a float. 180 == 180.00"""
    if not monto_str:
        return 0.0
    clean = re.sub(r"[^\d.]", "", str(monto_str).replace(",", ""))
    try:
        return round(float(clean), 2)
    except ValueError:
        return 0.0


# ─────────────────────────────────────────────
# MODULOS DE ANALISIS
# ─────────────────────────────────────────────

def analyze_entropy(clave_rastreo: str, bank_stats: dict) -> dict:
    """Analiza la entropia de la clave de rastreo."""
    e = entropy(clave_rastreo)
    min_entropy = bank_stats.get("entropia_min", 2.0)
    penalty = 0.0
    anomalia = None

    if e < min_entropy and clave_rastreo:
        penalty = (min_entropy - e) * 8
        anomalia = {
            "tipo": "entropia_baja",
            "descripcion": "Clave de rastreo con baja entropia (" + str(round(e, 2)) + " bits). Patron repetitivo o generado artificialmente.",
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
    z_scores_result = {}
    penalties = {}
    anomalias = []

    for field in fields:
        valor = clean_field(campos.get(field))
        if not valor:
            continue

        stats = bank_stats.get(field, {"mean": 7.0, "std": 2.0})
        z = z_score(len(valor), stats["mean"], stats["std"])
        z_scores_result[field] = round(z, 4)

        threshold = 3.5 if field == "clave_rastreo" else 2.5
        penalty = max(0, abs(z) - threshold) * 6
        penalties[field] = round(penalty, 2)

        if abs(z) > threshold + 1:
            anomalias.append({
                "tipo": "longitud_anomala_" + field,
                "descripcion": "Campo '" + field + "' con longitud inusual (z=" + str(round(z, 2)) + "). Valor: '" + valor + "' (" + str(len(valor)) + " caracteres).",
                "severidad": "media"
            })

    return {
        "z_scores": z_scores_result,
        "penalties": penalties,
        "anomalias": anomalias
    }


def validate_clave_rastreo_format(clave: str) -> dict:
    """
    Valida el formato de la clave de rastreo SPEI.
    Formatos validos:
    - Alfanumerico con prefijo banco: MBAN20260608123456789
    - Solo numerico de 16-25 digitos: 085900660340316466
    - Alfanumerico terminando en letra: 260608077756961262I
    """
    if not clave:
        return {"valid": True, "penalty": 0, "anomalia": None}

    # Formato 1: prefijo letras + digitos + letra opcional (SPEI clasico)
    spei_alpha = bool(re.match(r'^[A-Za-z]{3,4}\d{8,}[A-Za-z0-9]*$', clave))

    # Formato 2: solo numerico de longitud razonable
    spei_numeric = bool(re.match(r'^\d{16,25}$', clave))

    # Formato 3: alfanumerico mixto terminando en letra (ej: ...262I)
    spei_mixed = bool(re.match(r'^\d{15,24}[A-Za-z]$', clave))

    if spei_alpha or spei_numeric or spei_mixed:
        return {"valid": True, "penalty": 0, "anomalia": None}

    # Si no cumple ningun patron pero tiene longitud razonable, solo info menor
    if 10 <= len(clave) <= 30:
        return {
            "valid": True,
            "penalty": 2,
            "anomalia": {
                "tipo": "formato_clave_atipico",
                "descripcion": "La clave de rastreo '" + clave + "' no sigue el patron SPEI estandar, pero la longitud es aceptable.",
                "severidad": "info"
            }
        }

    return {
        "valid": False,
        "penalty": 8,
        "anomalia": {
            "tipo": "formato_clave_invalido",
            "descripcion": "La clave de rastreo '" + clave + "' tiene longitud muy inusual (" + str(len(clave)) + " caracteres).",
            "severidad": "media"
        }
    }


def analyze_temporal(fecha: Optional[str], hora: Optional[str]) -> dict:
    """
    Analiza coherencia temporal.
    Comprobantes pasados son NORMALES — solo penalizar si son muy antiguos (>180 dias)
    o si la fecha es futura.
    """
    penalty = 0.0
    anomalias = []
    hoy = datetime.now()

    fecha_parsed = parse_date(fecha)
    hora_int = parse_hour(hora)

    if fecha_parsed:
        diff_dias = (hoy - fecha_parsed).days

        if fecha_parsed.date() > hoy.date():
            penalty += 30
            anomalias.append({
                "tipo": "fecha_futura",
                "descripcion": "La fecha del comprobante (" + str(fecha) + ") es posterior a hoy. Altamente sospechoso.",
                "severidad": "alta"
            })
        elif diff_dias > 180:
            penalty += 8
            anomalias.append({
                "tipo": "fecha_antigua",
                "descripcion": "El comprobante tiene " + str(diff_dias) + " dias de antiguedad. Inusual para uso comercial inmediato.",
                "severidad": "info"
            })
        elif diff_dias > 90:
            penalty += 3
            anomalias.append({
                "tipo": "fecha_reciente_pero_pasada",
                "descripcion": "El comprobante tiene " + str(diff_dias) + " dias. Verifica que corresponda a la operacion actual.",
                "severidad": "info"
            })

        # Horario de mantenimiento SPEI: domingos despues de las 22:00
        if fecha_parsed.weekday() == 6 and hora_int is not None and hora_int >= 22:
            penalty += 20
            anomalias.append({
                "tipo": "horario_mantenimiento",
                "descripcion": "Transferencia en horario de mantenimiento SPEI (domingos 22:00+).",
                "severidad": "alta"
            })

    if hora_int is not None and (hora_int < 0 or hora_int > 23):
        penalty += 20
        anomalias.append({
            "tipo": "hora_invalida",
            "descripcion": "Hora invalida detectada: " + str(hora),
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

    valor = normalize_monto(str(monto))

    if valor == 0:
        penalty += 40
        anomalias.append({
            "tipo": "monto_cero",
            "descripcion": "El monto de la transferencia es $0.00.",
            "severidad": "alta"
        })

    # Monto redondo: solo informativo, no penalizar
    if valor > 5000 and valor % 1000 == 0:
        anomalias.append({
            "tipo": "monto_redondo",
            "descripcion": "Monto redondo exacto ($" + str(int(valor)) + "). Es mas frecuente en fraudes, pero tambien en pagos normales.",
            "severidad": "info"
        })

    return {
        "penalty": round(penalty, 2),
        "anomalias": anomalias,
        "monto_numerico": valor
    }


def analyze_combined_patterns(campos: dict, banco: str) -> dict:
    """
    Analiza combinaciones de variables para detectar patrones sospechosos.
    NO penaliza por concepto libre, tipo de cuenta vs concepto, ni leyendas bancarias estandar.
    """
    penalty = 0.0
    anomalias = []

    ref = clean_field(campos.get("referencia"))
    clave = clean_field(campos.get("clave_rastreo"))
    folio = clean_field(campos.get("folio"))

    # Patron: referencia == folio (copia exacta)
    if ref and folio and ref == folio:
        penalty += 15
        anomalias.append({
            "tipo": "referencia_igual_folio",
            "descripcion": "La referencia y el folio son identicos. Patron inusual en comprobantes reales.",
            "severidad": "media"
        })

    # Patron: campos con muy poca variacion (111111, 000000)
    for field_name, field_val in [("referencia", ref), ("folio", folio)]:
        if field_val and len(field_val) >= 4:
            if len(set(field_val)) <= 2:
                penalty += 12
                anomalias.append({
                    "tipo": "campo_repetitivo_" + field_name,
                    "descripcion": "El campo '" + field_name + "' tiene muy poca variacion de caracteres: '" + field_val + "'.",
                    "severidad": "media"
                })
            if field_val in ["123456", "000000", "111111", "999999", "123123"]:
                penalty += 20
                anomalias.append({
                    "tipo": "campo_generico_" + field_name,
                    "descripcion": "El campo '" + field_name + "' tiene un valor generico o de prueba: '" + field_val + "'.",
                    "severidad": "alta"
                })

    # Validar formato de clave de rastreo
    if clave:
        clave_result = validate_clave_rastreo_format(clave)
        if clave_result["anomalia"]:
            penalty += clave_result["penalty"]
            anomalias.append(clave_result["anomalia"])

    # NOTA: No penalizamos por:
    # - Concepto libre o inusual (tacos, renta, etc.) — es normal
    # - Ausencia de concepto — es opcional en SPEI
    # - Tipo de cuenta origen vs concepto — no hay relacion obligatoria
    # - Leyendas como "datos no verificados por esta institucion" — son estandar bancario

    return {
        "penalty": round(penalty, 2),
        "anomalias": anomalias
    }


# ─────────────────────────────────────────────
# CAPA DE APRENDIZAJE — Fingerprint de comprobante
# ─────────────────────────────────────────────

def generate_fingerprint(campos: dict, banco: str, score: float) -> dict:
    """
    Genera un fingerprint del comprobante para la base de aprendizaje.
    Se guarda en Supabase para mejorar el analisis con el tiempo.
    """
    clave = clean_field(campos.get("clave_rastreo") or "")
    ref = clean_field(campos.get("referencia") or "")
    folio = clean_field(campos.get("folio") or "")

    return {
        "banco": normalize_bank_name(banco),
        "longitud_clave": len(clave),
        "longitud_referencia": len(ref),
        "longitud_folio": len(folio),
        "entropia_clave": round(entropy(clave), 4),
        "tiene_concepto": bool(campos.get("concepto")),
        "tiene_folio": bool(folio),
        "tiene_clave_rastreo": bool(clave),
        "score_iat": round(score, 2),
        "timestamp": datetime.now().isoformat(),
    }


# ─────────────────────────────────────────────
# FUNCION PRINCIPAL DEL MOTOR IAT
# ─────────────────────────────────────────────

def calculate_iat(campos: dict, banco_origen: Optional[str] = None) -> dict:
    banco_norm = normalize_bank_name(banco_origen)
    bank_stats = BANK_STATS.get(banco_norm, BANK_STATS["DEFAULT"])

    clave_rastreo = clean_field(campos.get("clave_rastreo"))

    entropy_result  = analyze_entropy(clave_rastreo, bank_stats)
    lengths_result  = analyze_field_lengths(campos, bank_stats)
    temporal_result = analyze_temporal(campos.get("fecha"), campos.get("hora"))
    monto_result    = analyze_monto(campos.get("monto"))
    patterns_result = analyze_combined_patterns(campos, banco_norm)

    total_penalty = (
        entropy_result["penalty"] +
        sum(lengths_result["penalties"].values()) +
        temporal_result["penalty"] +
        monto_result["penalty"] +
        patterns_result["penalty"]
    )

    iat_score = max(0.0, min(100.0, 100.0 - total_penalty))

    anomalias = []
    if entropy_result["anomalia"]:
        anomalias.append(entropy_result["anomalia"])
    anomalias.extend(lengths_result["anomalias"])
    anomalias.extend(temporal_result["anomalias"])
    anomalias.extend(monto_result["anomalias"])
    anomalias.extend(patterns_result["anomalias"])

    fingerprint = generate_fingerprint(campos, banco_origen or "", iat_score)

    return {
        "iat_score": round(iat_score, 2),
        "banco_analizado": banco_norm,
        "anomalias": anomalias,
        "fingerprint": fingerprint,
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
    return round(0.7 * claude_score + 0.3 * iat_score, 2)


def iat_anomalias_to_validaciones(anomalias: list) -> list:
    severidad_to_status = {
        "alta": "fail",
        "media": "warn",
        "info": "info",
    }
    result = []
    for a in anomalias:
        result.append({
            "categoria": "reputacion",
            "nombre": "IAT: " + a.get("tipo", "anomalia").replace("_", " ").title(),
            "status": severidad_to_status.get(a.get("severidad", "media"), "warn"),
            "detalle": a.get("descripcion", "")
        })
    return result


def normalize_monto_compare(monto1: str, monto2: str) -> bool:
    """Compara dos montos normalizados. 180 == 180.00"""
    return normalize_monto(monto1) == normalize_monto(monto2)

    return normalize_monto(monto1) == normalize_monto(monto2)

