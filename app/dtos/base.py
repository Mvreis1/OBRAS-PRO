"""DTOs base - Base classes and common types for data transfer"""

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from typing import Any, Generic, TypeVar

T = TypeVar('T')


@dataclass
class PaginatedResponse:
    """Generic paginated response wrapper"""

    items: list[Any]
    total: int
    page: int
    per_page: int
    pages: int
    has_next: bool
    has_prev: bool

    def to_dict(self) -> dict:
        return {
            'items': [item.to_dict() if hasattr(item, 'to_dict') else item for item in self.items],
            'total': self.total,
            'page': self.page,
            'per_page': self.per_page,
            'pages': self.pages,
            'has_next': self.has_next,
            'has_prev': self.has_prev,
        }


@dataclass
class ApiResponse:
    """Generic API response wrapper"""

    success: bool
    data: Any | None = None
    message: str | None = None
    errors: list[str] | None = None

    def to_dict(self) -> dict:
        result = {'success': self.success}
        if self.data is not None:
            if hasattr(self.data, 'to_dict'):
                result['data'] = self.data.to_dict()
            elif isinstance(self.data, list):
                result['data'] = [
                    item.to_dict() if hasattr(item, 'to_dict') else item for item in self.data
                ]
            else:
                result['data'] = self.data
        if self.message:
            result['message'] = self.message
        if self.errors:
            result['errors'] = self.errors
        return result


class BaseDTO:
    """Base class for all DTOs with common methods"""

    def to_dict(self) -> dict[str, Any]:
        """Convert DTO to dictionary"""
        result = asdict(self)
        # Convert date/datetime objects to ISO strings
        for key, value in result.items():
            if isinstance(value, (date, datetime)):
                result[key] = value.isoformat()
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'BaseDTO':
        """Create DTO from dictionary"""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def update(self, data: dict[str, Any]) -> None:
        """Update DTO fields from dictionary"""
        for key, value in data.items():
            if key in self.__dataclass_fields__:
                setattr(self, key, value)
