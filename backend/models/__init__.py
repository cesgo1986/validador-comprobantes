"""
models/__init__.py

Importa todos los modelos aqui para que SQLAlchemy resuelva correctamente
las relationship() declaradas como string (ej. relationship("Empresa", ...)).
Sin esto, importar un solo modelo de forma aislada (ej. solo HashDocumento)
puede fallar con "failed to locate a name" porque SQLAlchemy no ha visto
todavia las clases que esa relationship necesita resolver.
"""
from models.empresa import Empresa  # noqa: F401
from models.usuario import Usuario  # noqa: F401
from models.hash_documento import HashDocumento  # noqa: F401
from models.analisis import Analisis  # noqa: F401