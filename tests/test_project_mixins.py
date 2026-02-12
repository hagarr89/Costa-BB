"""
Tests for project-scoped model mixins.

Tests cover:
- ProjectScopedMixin: project_id requirement and storage
- SoftDeleteMixin: deleted_at behavior
- BaseProjectModel: Combined functionality
- BaseProjectModelWithSoftDelete: Full feature set
"""

import uuid
from datetime import datetime

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.base_project import (
    BaseProjectModel,
    BaseProjectModelWithSoftDelete,
    ProjectScopedMixin,
    SoftDeleteMixin,
)
from tests.conftest import (
    TestProject,
    TestProjectModel,
    TestProjectModelWithSoftDelete,
)


class TestProjectScopedMixin:
    """Tests for ProjectScopedMixin functionality."""

    async def test_model_has_project_id_attribute(
        self, test_session, test_project_id
    ):
        """Model should have project_id attribute."""
        assert hasattr(TestProjectModel, "project_id")

    async def test_cannot_insert_without_project_id(self, test_session):
        """Should raise IntegrityError when project_id is missing."""
        instance = TestProjectModel(name="Test", description="Description")
        test_session.add(instance)

        with pytest.raises(IntegrityError):
            await test_session.commit()

    async def test_project_id_is_stored_correctly(
        self, test_session, test_project_id, test_project
    ):
        """Should store project_id correctly in database."""
        instance = TestProjectModel(
            project_id=test_project_id,
            name="Test Item",
            description="Test Description",
        )
        test_session.add(instance)
        await test_session.commit()
        await test_session.refresh(instance)

        assert instance.project_id == test_project_id
        assert isinstance(instance.project_id, uuid.UUID)

    async def test_project_id_is_not_nullable(
        self, test_session, test_project_id, test_project
    ):
        """project_id should be NOT NULL constraint."""
        # Try to create instance with None project_id
        instance = TestProjectModel(
            project_id=None,  # type: ignore
            name="Test",
        )
        test_session.add(instance)

        with pytest.raises((IntegrityError, ValueError)):
            await test_session.commit()

    async def test_project_id_has_foreign_key_constraint(
        self, test_session, test_project_id
    ):
        """Should enforce foreign key constraint on project_id."""
        invalid_project_id = uuid.uuid4()  # Non-existent project

        instance = TestProjectModel(
            project_id=invalid_project_id,
            name="Test",
        )
        test_session.add(instance)

        with pytest.raises(IntegrityError):
            await test_session.commit()

    async def test_project_id_is_indexed(
        self, test_session, test_project_id, test_project
    ):
        """project_id should have an index for query performance."""
        # Check that project_id column has index
        table = TestProjectModel.__table__
        project_id_column = table.c.project_id

        # Verify index exists
        indexes = [idx for idx in table.indexes if project_id_column in idx.columns]
        assert len(indexes) > 0, "project_id should have an index"


class TestSoftDeleteMixin:
    """Tests for SoftDeleteMixin functionality."""

    async def test_model_has_deleted_at_attribute(self, test_session):
        """Model should have deleted_at attribute."""
        assert hasattr(TestProjectModelWithSoftDelete, "deleted_at")

    async def test_deleted_at_is_null_by_default(
        self, test_session, test_project_id, test_project
    ):
        """deleted_at should be None by default."""
        instance = TestProjectModelWithSoftDelete(
            project_id=test_project_id,
            name="Test Item",
        )
        test_session.add(instance)
        await test_session.commit()
        await test_session.refresh(instance)

        assert instance.deleted_at is None

    async def test_deleted_at_is_nullable(self, test_session, test_project_id, test_project):
        """deleted_at should be nullable."""
        instance = TestProjectModelWithSoftDelete(
            project_id=test_project_id,
            name="Test",
            deleted_at=None,
        )
        test_session.add(instance)
        await test_session.commit()
        await test_session.refresh(instance)

        assert instance.deleted_at is None

    async def test_can_set_deleted_at(
        self, test_session, test_project_id, test_project
    ):
        """Should be able to set deleted_at timestamp."""
        deleted_time = datetime.now()
        instance = TestProjectModelWithSoftDelete(
            project_id=test_project_id,
            name="Test",
            deleted_at=deleted_time,
        )
        test_session.add(instance)
        await test_session.commit()
        await test_session.refresh(instance)

        assert instance.deleted_at is not None
        assert isinstance(instance.deleted_at, datetime)

    async def test_soft_deleted_rows_remain_in_db(
        self, test_session, test_project_id, test_project
    ):
        """Soft deleted rows should remain in database."""
        instance = TestProjectModelWithSoftDelete(
            project_id=test_project_id,
            name="Test Item",
        )
        test_session.add(instance)
        await test_session.commit()
        await test_session.refresh(instance)

        instance_id = instance.id

        # Soft delete
        instance.deleted_at = datetime.now()
        await test_session.commit()

        # Verify still exists in DB
        query = select(TestProjectModelWithSoftDelete).where(
            TestProjectModelWithSoftDelete.id == instance_id
        )
        result = await test_session.execute(query)
        found_instance = result.scalar_one_or_none()

        assert found_instance is not None
        assert found_instance.deleted_at is not None

    async def test_can_filter_out_deleted_rows(
        self, test_session, test_project_id, test_project
    ):
        """Should be able to filter out soft-deleted rows in queries."""
        # Create active instance
        active_instance = TestProjectModelWithSoftDelete(
            project_id=test_project_id,
            name="Active Item",
        )
        test_session.add(active_instance)

        # Create deleted instance
        deleted_instance = TestProjectModelWithSoftDelete(
            project_id=test_project_id,
            name="Deleted Item",
            deleted_at=datetime.now(),
        )
        test_session.add(deleted_instance)

        await test_session.commit()

        # Query without deleted
        query = select(TestProjectModelWithSoftDelete).where(
            TestProjectModelWithSoftDelete.deleted_at.is_(None)
        )
        result = await test_session.execute(query)
        active_items = result.scalars().all()

        assert len(active_items) == 1
        assert active_items[0].id == active_instance.id
        assert active_items[0].name == "Active Item"

        # Query with deleted
        query_all = select(TestProjectModelWithSoftDelete)
        result_all = await test_session.execute(query_all)
        all_items = result_all.scalars().all()

        assert len(all_items) == 2

    async def test_deleted_at_is_indexed(
        self, test_session, test_project_id, test_project
    ):
        """deleted_at should have an index for query performance."""
        table = TestProjectModelWithSoftDelete.__table__
        deleted_at_column = table.c.deleted_at

        # Verify index exists
        indexes = [idx for idx in table.indexes if deleted_at_column in idx.columns]
        assert len(indexes) > 0, "deleted_at should have an index"


class TestBaseProjectModel:
    """Tests for BaseProjectModel (project_id + UUID PK)."""

    async def test_inherits_project_id(
        self, test_session, test_project_id, test_project
    ):
        """Should inherit project_id from ProjectScopedMixin."""
        instance = TestProjectModel(
            project_id=test_project_id,
            name="Test",
        )
        test_session.add(instance)
        await test_session.commit()
        await test_session.refresh(instance)

        assert hasattr(instance, "project_id")
        assert instance.project_id == test_project_id

    async def test_inherits_uuid_primary_key(
        self, test_session, test_project_id, test_project
    ):
        """Should inherit UUID primary key from BaseUUIDModel."""
        instance = TestProjectModel(
            project_id=test_project_id,
            name="Test",
        )
        test_session.add(instance)
        await test_session.commit()
        await test_session.refresh(instance)

        assert hasattr(instance, "id")
        assert isinstance(instance.id, uuid.UUID)

    async def test_no_soft_delete_by_default(
        self, test_session, test_project_id, test_project
    ):
        """Should not have soft delete capability by default."""
        instance = TestProjectModel(
            project_id=test_project_id,
            name="Test",
        )
        test_session.add(instance)
        await test_session.commit()
        await test_session.refresh(instance)

        assert not hasattr(instance, "deleted_at")


class TestBaseProjectModelWithSoftDelete:
    """Tests for BaseProjectModelWithSoftDelete (full feature set)."""

    async def test_has_all_features(
        self, test_session, test_project_id, test_project
    ):
        """Should have project_id, UUID PK, and soft delete."""
        instance = TestProjectModelWithSoftDelete(
            project_id=test_project_id,
            name="Test",
        )
        test_session.add(instance)
        await test_session.commit()
        await test_session.refresh(instance)

        # Check all features
        assert hasattr(instance, "id")
        assert isinstance(instance.id, uuid.UUID)

        assert hasattr(instance, "project_id")
        assert instance.project_id == test_project_id

        assert hasattr(instance, "deleted_at")
        assert instance.deleted_at is None

    async def test_soft_delete_workflow(
        self, test_session, test_project_id, test_project
    ):
        """Test complete soft delete workflow."""
        # Create instance
        instance = TestProjectModelWithSoftDelete(
            project_id=test_project_id,
            name="Test Item",
        )
        test_session.add(instance)
        await test_session.commit()
        await test_session.refresh(instance)

        original_id = instance.id
        assert instance.deleted_at is None

        # Soft delete
        instance.deleted_at = datetime.now()
        await test_session.commit()
        await test_session.refresh(instance)

        assert instance.deleted_at is not None

        # Verify can still query with include_deleted
        query = select(TestProjectModelWithSoftDelete).where(
            TestProjectModelWithSoftDelete.id == original_id
        )
        result = await test_session.execute(query)
        found = result.scalar_one_or_none()

        assert found is not None
        assert found.deleted_at is not None


class TestMultiTenantIsolation:
    """Tests for multi-tenant isolation using project_id."""

    async def test_records_isolated_by_project_id(
        self,
        test_session,
        test_project_id,
        test_project_id_2,
        test_project,
        test_project_2,
    ):
        """Records from different projects should be isolated."""
        # Create records in project 1
        item1 = TestProjectModel(
            project_id=test_project_id,
            name="Project 1 Item",
        )
        test_session.add(item1)

        # Create records in project 2
        item2 = TestProjectModel(
            project_id=test_project_id_2,
            name="Project 2 Item",
        )
        test_session.add(item2)

        await test_session.commit()

        # Query project 1 records
        query1 = select(TestProjectModel).where(
            TestProjectModel.project_id == test_project_id
        )
        result1 = await test_session.execute(query1)
        project1_items = result1.scalars().all()

        assert len(project1_items) == 1
        assert project1_items[0].project_id == test_project_id
        assert project1_items[0].name == "Project 1 Item"

        # Query project 2 records
        query2 = select(TestProjectModel).where(
            TestProjectModel.project_id == test_project_id_2
        )
        result2 = await test_session.execute(query2)
        project2_items = result2.scalars().all()

        assert len(project2_items) == 1
        assert project2_items[0].project_id == test_project_id_2
        assert project2_items[0].name == "Project 2 Item"

    async def test_cannot_access_other_project_data(
        self,
        test_session,
        test_project_id,
        test_project_id_2,
        test_project,
        test_project_2,
    ):
        """Should not be able to access data from other projects."""
        # Create item in project 1
        item1 = TestProjectModel(
            project_id=test_project_id,
            name="Project 1 Item",
        )
        test_session.add(item1)
        await test_session.commit()
        await test_session.refresh(item1)

        item1_id = item1.id

        # Try to query with wrong project_id
        query = select(TestProjectModel).where(
            TestProjectModel.id == item1_id,
            TestProjectModel.project_id == test_project_id_2,  # Wrong project
        )
        result = await test_session.execute(query)
        found = result.scalar_one_or_none()

        assert found is None, "Should not find item from different project"
