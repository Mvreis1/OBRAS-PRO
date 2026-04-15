"""Base Service - Common patterns for all services"""

from typing import Any, Optional

from sqlalchemy.orm import Query

from app.models import db


class BaseService:
    """Base class with common patterns for all services"""

    @staticmethod
    def get_by_id(model, entity_id: int, empresa_id: int | None = None):
        """
        Get entity by ID with optional empresa filter

        Args:
            model: SQLAlchemy model class
            entity_id: Entity ID
            empresa_id: Optional empresa_id for tenant isolation

        Returns:
            Entity instance or None
        """
        query = model.query
        if empresa_id:
            query = query.filter_by(empresa_id=empresa_id)
        return query.filter_by(id=entity_id).first()

    @staticmethod
    def get_or_404(model, entity_id: int, empresa_id: int | None = None):
        """
        Get entity by ID or raise 404

        Args:
            model: SQLAlchemy model class
            entity_id: Entity ID
            empresa_id: Optional empresa_id for tenant isolation

        Returns:
            Entity instance

        Raises:
            404: If entity not found
        """
        query = model.query
        if empresa_id:
            query = query.filter_by(empresa_id=empresa_id)
        return query.filter_by(id=entity_id).first_or_404()

    @staticmethod
    def get_all(model, empresa_id: int, filters: dict | None = None, order_by=None):
        """
        Get all entities with optional filters

        Args:
            model: SQLAlchemy model class
            empresa_id: Empresa ID for tenant isolation
            filters: Optional dict of filter conditions
            order_by: Optional order by column

        Returns:
            Query object
        """
        query = model.query.filter_by(empresa_id=empresa_id)

        if filters:
            for key, value in filters.items():
                if value is not None:
                    query = query.filter(getattr(model, key) == value)

        if order_by:
            query = query.order_by(order_by)

        return query

    @staticmethod
    def search(
        model,
        empresa_id: int,
        search_term: str,
        search_fields: list[str],
        filters: dict | None = None,
    ):
        """
        Search entities by text in multiple fields

        Args:
            model: SQLAlchemy model class
            empresa_id: Empresa ID
            search_term: Text to search
            search_fields: List of field names to search
            filters: Optional additional filters

        Returns:
            Query object
        """
        query = model.query.filter_by(empresa_id=empresa_id)

        if search_term:
            conditions = []
            for field in search_fields:
                conditions.append(getattr(model, field).ilike(f'%{search_term}%'))
            query = query.filter(db.or_(*conditions))

        if filters:
            for key, value in filters.items():
                if value is not None:
                    query = query.filter(getattr(model, key) == value)

        return query

    @staticmethod
    def paginate_query(query, page: int = 1, per_page: int = 20):
        """
        Paginate a query

        Args:
            query: SQLAlchemy Query object
            page: Page number (1-based)
            per_page: Items per page

        Returns:
            Pagination object
        """
        return query.paginate(page=page, per_page=per_page, error_out=False)

    @staticmethod
    def validate_unique(
        model, field: str, value: Any, exclude_id: int | None = None
    ) -> tuple[bool, str | None]:
        """
        Validate that a field value is unique

        Args:
            model: SQLAlchemy model class
            field: Field name to check
            value: Value to validate
            exclude_id: Optional ID to exclude (for updates)

        Returns:
            Tuple (is_valid, error_message)
        """
        query = model.query.filter_by(**{field: value})
        if exclude_id:
            query = query.filter(model.id != exclude_id)

        if query.first():
            return False, f'{field} já está em uso'
        return True, None

    @staticmethod
    def bulk_delete(model, ids: list[int], empresa_id: int) -> tuple[int, str | None]:
        """
        Delete multiple entities by ID

        Args:
            model: SQLAlchemy model class
            ids: List of IDs to delete
            empresa_id: Empresa ID for tenant isolation

        Returns:
            Tuple (deleted_count, error_message)
        """
        entities = model.query.filter(model.id.in_(ids), model.empresa_id == empresa_id).all()

        if not entities:
            return 0, 'Nenhuma entidade encontrada'

        for entity in entities:
            db.session.delete(entity)

        db.session.commit()
        return len(entities), None

    @staticmethod
    def bulk_update(
        model, ids: list[int], empresa_id: int, updates: dict
    ) -> tuple[int, str | None]:
        """
        Update multiple entities by ID

        Args:
            model: SQLAlchemy model class
            ids: List of IDs to update
            empresa_id: Empresa ID for tenant isolation
            updates: Dict of fields to update

        Returns:
            Tuple (updated_count, error_message)
        """
        entities = model.query.filter(model.id.in_(ids), model.empresa_id == empresa_id).all()

        if not entities:
            return 0, 'Nenhuma entidade encontrada'

        for entity in entities:
            for field, value in updates.items():
                if hasattr(entity, field):
                    setattr(entity, field, value)

        db.session.commit()
        return len(entities), None

    @staticmethod
    def count(model, empresa_id: int, filters: dict | None = None) -> int:
        """
        Count entities with optional filters

        Args:
            model: SQLAlchemy model class
            empresa_id: Empresa ID
            filters: Optional filter conditions

        Returns:
            Count integer
        """
        query = model.query.filter_by(empresa_id=empresa_id)

        if filters:
            for key, value in filters.items():
                if value is not None:
                    query = query.filter(getattr(model, key) == value)

        return query.count()
