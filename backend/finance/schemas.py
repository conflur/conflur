"""Schemas de finanzas (motor de costos)."""
import uuid
from datetime import date, datetime
from pydantic import BaseModel, Field

TIPOS = ("durable", "fijo", "variable")


class ExpenseCreate(BaseModel):
    fecha: date
    tipo: str  # durable | fijo | variable
    descripcion: str = Field(min_length=1, max_length=255)
    monto: float = Field(gt=0)
    categoria: str | None = Field(default=None, max_length=100)
    currency: str | None = Field(default=None, max_length=10)
    payment_status: str = "paid"
    useful_life_months: int | None = Field(default=None, ge=1)  # requerido si durable
    notes: str | None = None


class ExpenseUpdate(BaseModel):
    fecha: date | None = None
    descripcion: str | None = Field(default=None, min_length=1, max_length=255)
    monto: float | None = Field(default=None, gt=0)
    categoria: str | None = Field(default=None, max_length=100)
    payment_status: str | None = None
    useful_life_months: int | None = Field(default=None, ge=1)
    notes: str | None = None


class ExpenseOut(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    fecha: date
    tipo: str
    descripcion: str
    categoria: str | None
    monto: float
    currency: str | None
    payment_status: str
    useful_life_months: int | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RecurringExpenseCreate(BaseModel):
    concepto: str = Field(min_length=1, max_length=255)
    monthly_amount: float = Field(gt=0)
    valid_from: date
    categoria: str | None = Field(default=None, max_length=100)
    currency: str | None = Field(default=None, max_length=10)
    notes: str | None = None


class RecurringExpenseOut(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    concepto: str
    categoria: str | None
    monthly_amount: float
    currency: str | None
    valid_from: date
    valid_until: date | None
    notes: str | None

    class Config:
        from_attributes = True


class RecurringChangeAmount(BaseModel):
    """Cambia el monto sin destruir historial: cierra el vigente y crea uno nuevo."""
    new_monthly_amount: float = Field(gt=0)
    effective_from: date


class MonthlySettingUpsert(BaseModel):
    year: int = Field(ge=2020, le=2100)
    month: int = Field(ge=1, le=12)
    planned_hours: float = Field(ge=0)
    opening_cash_balance: float = 0


class MonthlySettingOut(BaseModel):
    year: int
    month: int
    planned_hours: float
    opening_cash_balance: float

    class Config:
        from_attributes = True


class IncomeCreate(BaseModel):
    fecha: date
    amount: float = Field(gt=0)
    patient_id: uuid.UUID | None = None
    professional_user_id: uuid.UUID | None = None
    session_type_id: uuid.UUID | None = None
    appointment_id: uuid.UUID | None = None
    currency: str | None = Field(default=None, max_length=10)
    notes: str | None = None


class IncomeOut(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    fecha: date
    patient_id: uuid.UUID | None
    professional_user_id: uuid.UUID | None
    session_type_id: uuid.UUID | None
    appointment_id: uuid.UUID | None
    amount: float
    currency: str | None
    notes: str | None

    class Config:
        from_attributes = True


class CollectionCreate(BaseModel):
    fecha: date
    amount: float = Field(gt=0)
    patient_id: uuid.UUID | None = None
    income_record_id: uuid.UUID | None = None
    payment_method: str | None = Field(default=None, max_length=50)
    currency: str | None = Field(default=None, max_length=10)
    notes: str | None = None


class CollectionOut(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    fecha: date
    patient_id: uuid.UUID | None
    income_record_id: uuid.UUID | None
    amount: float
    currency: str | None
    payment_method: str | None
    notes: str | None

    class Config:
        from_attributes = True


class CostoHoraOut(BaseModel):
    year: int
    month: int
    fixed_recurring: float
    amortization: float
    total_fixed: float
    planned_hours: float | None
    costo_hora: float | None
    needs_setup: bool


class EstadoResultadoOut(BaseModel):
    ingresos: float
    costos_variables: float
    costos_fijos: float
    resultado_neto: float
    margen_neto_pct: float | None


class FlujoCajaOut(BaseModel):
    saldo_inicial: float
    entradas: float
    salidas: float
    flujo_neto: float
    saldo_final: float


class MatrizSaludOut(BaseModel):
    codigo: str
    label: str
    detalle: str


class KpisOut(BaseModel):
    atenciones: int
    ticket_promedio: float | None
    pct_cobro: float | None
    costo_por_paciente: float | None
    rentabilidad_por_hora: float | None


class PrecioSugeridoOut(BaseModel):
    session_type_id: uuid.UUID
    nombre: str
    duracion_horas: float
    costo_hora: float | None
    costo_estructura: float | None
    costo_variable: float
    margen_pct: float
    precio_sugerido: float | None
    precio_actual: float | None
    diferencia_pct: float | None  # actual vs sugerido (negativo = por debajo del costo+margen)
    needs_setup: bool


class AnnualGoalUpsert(BaseModel):
    year: int = Field(ge=2020, le=2100)
    meta_margen_neto: float | None = Field(default=None, ge=0)
    meta_ticket_promedio: float | None = Field(default=None, ge=0)
    meta_rentabilidad_por_hora: float | None = Field(default=None, ge=0)


class AnnualGoalOut(BaseModel):
    year: int
    meta_margen_neto: float | None
    meta_ticket_promedio: float | None
    meta_rentabilidad_por_hora: float | None

    class Config:
        from_attributes = True


class DashboardOut(BaseModel):
    year: int
    month: int
    estado_resultado: EstadoResultadoOut
    flujo_caja: FlujoCajaOut
    matriz_salud: MatrizSaludOut
    kpis: KpisOut
    metas: AnnualGoalOut | None
    alertas: list[str]
