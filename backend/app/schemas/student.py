from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


Participation = Literal["Baja", "Media", "Alta"]


class StudentFeatures(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asistencia_pct: float = Field(ge=0, le=100)
    promedio_parcial: float = Field(ge=0, le=20)
    horas_estudio: float = Field(ge=0)
    tareas_entregadas_pct: float = Field(ge=0, le=100)
    participacion_aula: Participation
    cursos_desaprobados: int = Field(ge=0)
    actividad_plataforma: int = Field(ge=0)


class ManualPredictionRequest(StudentFeatures):
    estudiante_id: str = Field(min_length=1, max_length=80)

    @field_validator("estudiante_id")
    @classmethod
    def clean_student_id(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("El código del estudiante es obligatorio.")
        return cleaned

