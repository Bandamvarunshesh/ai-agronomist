"""crop stage advisory

Revision ID: 20260707_0006
Revises: 20260707_0005
Create Date: 2026-07-07 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260707_0006"
down_revision = "20260707_0005"
branch_labels = None
depends_on = None


GENERIC_CROP_ID = "00000000-0000-4000-8000-000000000901"


def uuid_pk_column() -> sa.Column:
    return sa.Column(
        "id",
        postgresql.UUID(as_uuid=True),
        server_default=sa.text("gen_random_uuid()"),
        nullable=False,
    )


def timestamp_columns() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def upgrade() -> None:
    op.create_table(
        "crops",
        uuid_pk_column(),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("normalized_name", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("duration_days", sa.Integer(), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        *timestamp_columns(),
        sa.CheckConstraint(
            "duration_days IS NULL OR duration_days > 0",
            name=op.f("ck_crops_duration_days_positive"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_crops")),
        sa.UniqueConstraint(
            "normalized_name",
            name=op.f("uq_crops_normalized_name"),
        ),
    )
    op.create_index(
        op.f("ix_crops_is_active"),
        "crops",
        ["is_active"],
        unique=False,
    )
    op.create_index(
        op.f("ix_crops_normalized_name"),
        "crops",
        ["normalized_name"],
        unique=False,
    )

    op.create_table(
        "crop_stages",
        uuid_pk_column(),
        sa.Column("crop_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("stage_name", sa.String(length=100), nullable=False),
        sa.Column("stage_order", sa.Integer(), nullable=False),
        sa.Column("start_day", sa.Integer(), nullable=False),
        sa.Column("end_day", sa.Integer(), nullable=False),
        sa.Column(
            "important_actions",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "risk_factors",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "ai_recommendations",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        *timestamp_columns(),
        sa.CheckConstraint(
            "stage_order >= 0",
            name=op.f("ck_crop_stages_stage_order_non_negative"),
        ),
        sa.CheckConstraint(
            "start_day >= 0",
            name=op.f("ck_crop_stages_start_day_non_negative"),
        ),
        sa.CheckConstraint(
            "end_day >= start_day",
            name=op.f("ck_crop_stages_end_day_after_start_day"),
        ),
        sa.ForeignKeyConstraint(
            ["crop_id"],
            ["crops.id"],
            name=op.f("fk_crop_stages_crop_id_crops"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_crop_stages")),
        sa.UniqueConstraint(
            "crop_id",
            "stage_name",
            name=op.f("uq_crop_stages_crop_stage"),
        ),
        sa.UniqueConstraint(
            "crop_id",
            "stage_order",
            name=op.f("uq_crop_stages_crop_order"),
        ),
    )
    op.create_index(
        op.f("ix_crop_stages_crop_id"),
        "crop_stages",
        ["crop_id"],
        unique=False,
    )

    op.execute(
        f"""
        INSERT INTO crops (
            id,
            name,
            normalized_name,
            category,
            duration_days,
            metadata
        )
        VALUES (
            '{GENERIC_CROP_ID}',
            'Generic crop',
            'generic',
            'generic',
            130,
            '{{"source": "phase_9_seed", "fallback": true}}'::jsonb
        )
        """
    )
    op.execute(
        f"""
        INSERT INTO crop_stages (
            crop_id,
            stage_name,
            stage_order,
            start_day,
            end_day,
            important_actions,
            risk_factors,
            ai_recommendations,
            metadata
        )
        VALUES
        (
            '{GENERIC_CROP_ID}',
            'Germination and establishment',
            0,
            0,
            14,
            '["Check emergence and plant stand", "Keep soil moist but not waterlogged", "Fill gaps where crop establishment is poor"]'::jsonb,
            '["Poor germination", "Seedling damping-off", "Soil crusting or early moisture stress"]'::jsonb,
            '["Inspect seedlings every 2 to 3 days", "Use light irrigation when the topsoil dries", "Contact an extension officer if large patches fail to emerge"]'::jsonb,
            '{{"generic": true}}'::jsonb
        ),
        (
            '{GENERIC_CROP_ID}',
            'Vegetative growth',
            1,
            15,
            40,
            '["Scout for weeds and early pest damage", "Maintain even soil moisture", "Plan nutrition based on soil and crop condition"]'::jsonb,
            '["Weed competition", "Nutrient deficiency symptoms", "Early sucking pests or leaf damage"]'::jsonb,
            '["Prioritize field scouting before interventions", "Avoid precise fertilizer or pesticide dosages without local soil-test or label guidance", "Keep records of irrigation and field observations"]'::jsonb,
            '{{"generic": true}}'::jsonb
        ),
        (
            '{GENERIC_CROP_ID}',
            'Flowering and reproductive initiation',
            2,
            41,
            65,
            '["Avoid water stress around flowering", "Protect pollination conditions", "Scout for disease and pest pressure in the canopy"]'::jsonb,
            '["Flower drop from heat or moisture stress", "High disease pressure in humid weather", "Pest damage to reproductive parts"]'::jsonb,
            '["Avoid disruptive operations during peak flowering", "Use weather windows for any spray operations", "Seek local agronomist advice for severe flowering losses"]'::jsonb,
            '{{"generic": true}}'::jsonb
        ),
        (
            '{GENERIC_CROP_ID}',
            'Fruiting or grain filling',
            3,
            66,
            95,
            '["Maintain consistent moisture", "Monitor crop load and lodging risk", "Scout for late pests, diseases, and nutrient stress"]'::jsonb,
            '["Yield loss from moisture swings", "Fruit or grain quality problems", "Late-season disease pressure"]'::jsonb,
            '["Keep irrigation steady rather than erratic", "Inspect fields after rain or strong wind", "Escalate fast-spreading disease symptoms to an agronomist"]'::jsonb,
            '{{"generic": true}}'::jsonb
        ),
        (
            '{GENERIC_CROP_ID}',
            'Maturity and harvest preparation',
            4,
            96,
            130,
            '["Track maturity signs", "Prepare harvest labor, tools, and storage", "Avoid unnecessary late chemical applications"]'::jsonb,
            '["Harvest delays from rain", "Storage quality losses", "Lodging or shattering in wind"]'::jsonb,
            '["Plan harvest around dry weather windows", "Dry and grade produce before storage where applicable", "Follow label pre-harvest intervals for any regulated input"]'::jsonb,
            '{{"generic": true}}'::jsonb
        ),
        (
            '{GENERIC_CROP_ID}',
            'Post-harvest and field reset',
            5,
            131,
            365,
            '["Clean field residues as appropriate", "Review yield and input records", "Plan rotation, soil improvement, and storage checks"]'::jsonb,
            '["Stored produce spoilage", "Carry-over pests and disease", "Missed rotation or soil recovery planning"]'::jsonb,
            '["Separate damaged produce during storage", "Document disease or pest hotspots for the next season", "Discuss rotation and soil health with a local extension officer"]'::jsonb,
            '{{"generic": true}}'::jsonb
        )
        """
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_crop_stages_crop_id"), table_name="crop_stages")
    op.drop_table("crop_stages")
    op.drop_index(op.f("ix_crops_normalized_name"), table_name="crops")
    op.drop_index(op.f("ix_crops_is_active"), table_name="crops")
    op.drop_table("crops")
