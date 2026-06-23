"""Tests de estructura del modelo de tenancy (no requieren DB)."""
import pytest

from models import (
    Base, Tenant, User, Membership, UserPasskey,
    Patient, PatientAccess, Appointment, ClinicalNote,
    Subscription, NoteFeedback,
)

pytestmark = pytest.mark.unit

# Tablas tenant-scoped: tenant_id debe apuntar a tenants.id y tener RLS.
TENANT_SCOPED = [
    Membership, Patient, PatientAccess, Appointment,
    ClinicalNote, Subscription, NoteFeedback,
]


def _fk_target(model, column):
    col = model.__table__.c[column]
    assert col.foreign_keys, f"{model.__tablename__}.{column} sin FK"
    return {fk.column.table.name for fk in col.foreign_keys}


def test_tenant_scoped_tables_point_tenant_id_to_tenants():
    """tenant_id de toda tabla tenant-scoped apunta a tenants.id (no a users)."""
    for model in TENANT_SCOPED:
        assert "tenant_id" in model.__table__.c, f"{model.__tablename__} sin tenant_id"
        assert _fk_target(model, "tenant_id") == {"tenants"}, (
            f"{model.__tablename__}.tenant_id no apunta a tenants"
        )


def test_user_has_no_role_column():
    """El rol vive en memberships, no en users. users solo tiene is_platform_admin."""
    assert "role" not in User.__table__.c
    assert "is_platform_admin" in User.__table__.c


def test_membership_links_user_and_tenant_uniquely():
    assert _fk_target(Membership, "user_id") == {"users"}
    assert _fk_target(Membership, "tenant_id") == {"tenants"}
    uniques = {
        tuple(sorted(c.name for c in con.columns))
        for con in Membership.__table__.constraints
        if con.__class__.__name__ == "UniqueConstraint"
    }
    assert ("tenant_id", "user_id") in uniques


def test_clinical_note_has_author_and_patient():
    """La nota referencia autor (profesional) y paciente — base de la visibilidad clínica."""
    assert _fk_target(ClinicalNote, "author_user_id") == {"users"}
    assert _fk_target(ClinicalNote, "patient_id") == {"patients"}


def test_patient_access_shape():
    """patient_access liga paciente ↔ profesional con tipo, expiración y revocación."""
    cols = PatientAccess.__table__.c
    for expected in ("patient_id", "professional_user_id", "access_type", "expires_at", "revoked_at", "granted_by_user_id"):
        assert expected in cols, f"patient_access sin {expected}"
    uniques = {
        tuple(sorted(c.name for c in con.columns))
        for con in PatientAccess.__table__.constraints
        if con.__class__.__name__ == "UniqueConstraint"
    }
    assert ("patient_id", "professional_user_id") in uniques


def test_subscription_is_tenant_scoped_not_user():
    """La suscripción es del consultorio, no del usuario."""
    assert "tenant_id" in Subscription.__table__.c
    assert "user_id" not in Subscription.__table__.c


def test_appointment_has_professional():
    assert _fk_target(Appointment, "professional_user_id") == {"users"}
