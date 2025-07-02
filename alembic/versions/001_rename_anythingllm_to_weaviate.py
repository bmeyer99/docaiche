"""Rename AnythingLLM columns to Weaviate

Revision ID: 001
Revises: 
Create Date: 2025-07-02 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Rename columns in content_metadata table
    with op.batch_alter_table('content_metadata') as batch_op:
        batch_op.alter_column('anythingllm_workspace', new_column_name='weaviate_workspace')
        batch_op.alter_column('anythingllm_document_id', new_column_name='weaviate_document_id')


def downgrade():
    # Revert column names in content_metadata table
    with op.batch_alter_table('content_metadata') as batch_op:
        batch_op.alter_column('weaviate_workspace', new_column_name='anythingllm_workspace')
        batch_op.alter_column('weaviate_document_id', new_column_name='anythingllm_document_id')