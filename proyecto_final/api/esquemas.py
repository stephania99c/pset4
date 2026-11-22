"""Esquemas de entrada y salida de la API.

La entrada coincide con la firma del modelo registrada en MLflow (mismas
columnas y tipos), sin gestionado_7d: al armar la lista todavia no se sabe a
quien se llamara, asi que la API lo fija en 1 por dentro.

Los rangos rechazan valores imposibles en el negocio (error 422).
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class Credito(BaseModel):
    # Mora y cuotas (plazo maximo: 6 anos; casos especiales hasta 8)
    dias_mora: int = Field(ge=1, le=2190)
    cuotas_mora: int = Field(ge=1, le=96)
    cuotas_por_pagar: int = Field(ge=1, le=96)
    cuotas_pagadas: int = Field(ge=0, le=96)
    total_cuotas: float = Field(ge=1, le=96)

    # Montos en dolares (no hay montos negativos)
    capital_insoluto: float = Field(ge=0)
    capital_vencido: float = Field(ge=0)
    saldo_cuota_mas_vencida: float = Field(ge=0)
    valor_deuda_exigible: float = Field(ge=0)
    valor_cuota_exigible_vigente: float = Field(ge=0)
    monto_financiado: float = Field(gt=0)

    # Condiciones del credito y gestion
    tasa_nominal: float = Field(ge=0, le=1)
    num_gestiones_dia: int = Field(ge=0, le=20)
    estado_operacion: Literal["CASTIGADA", "NON ACCRUAL", "VENCIDO"]
    dia_pago: int = Field(ge=1, le=31)
    plazo_terminado: Literal[0, 1]
    compromiso_semana_previa: Literal[0, 1]


class Prediccion(BaseModel):
    id_prediccion: str
    decision: Literal["gestionar", "no gestionar"]
    probabilidad: Optional[float]
    puntaje: float
    nota_corte: float
    efecto_incremental: Optional[float]
    interpretacion_efecto: str
    version_modelo: Optional[str]
    uso_respaldo: bool