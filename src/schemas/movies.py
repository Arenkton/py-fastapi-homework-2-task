import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MovieListItemSchema(BaseModel):
    id: int
    name: str
    date: datetime.date
    score: float
    overview: str

    model_config = ConfigDict(from_attributes=True)


class MovieListResponseSchema(BaseModel):
    movies: list[MovieListItemSchema]
    prev_page: str | None
    next_page: str | None
    total_pages: int
    total_items: int


class MovieCreateSchema(BaseModel):
    name: str = Field(max_length=255)
    date: datetime.date
    score: float = Field(ge=0, le=100)
    overview: str
    status: Literal[
        "Released",
        "Post Production",
        "In Production"
    ]
    budget: Decimal = Field(ge=0)
    revenue: Decimal = Field(ge=0)
    country: str = Field(min_length=2, max_length=3)
    genres: list[str]
    actors: list[str]
    languages: list[str]

    @field_validator("date")
    @classmethod
    def validate_date(
        cls,
        value: datetime.date
    ) -> datetime.date:
        today = datetime.date.today()

        try:
            max_date = today.replace(year=today.year + 1)
        except ValueError:
            max_date = today.replace(
                year=today.year + 1,
                day=28
            )

        if value > max_date:
            raise ValueError(
                "Release date cannot be more than one year in the future."
            )

        return value


class CountrySchema(BaseModel):
    id: int
    code: str
    name: str | None

    model_config = ConfigDict(from_attributes=True)


class RelatedEntitySchema(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class MovieDetailSchema(BaseModel):
    id: int
    name: str
    date: datetime.date
    score: float
    overview: str
    status: str
    budget: float
    revenue: float
    country: CountrySchema
    genres: list[RelatedEntitySchema]
    actors: list[RelatedEntitySchema]
    languages: list[RelatedEntitySchema]

    model_config = ConfigDict(from_attributes=True)


class MovieUpdateSchema(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    date: datetime.date | None = None
    score: float | None = Field(default=None, ge=0, le=100)
    overview: str | None = None
    status: Literal[
        "Released",
        "Post Production",
        "In Production"
    ] | None = None
    budget: Decimal | None = Field(default=None, ge=0)
    revenue: Decimal | None = Field(default=None, ge=0)

    @field_validator(
        "name",
        "date",
        "score",
        "overview",
        "status",
        "budget",
        "revenue",
        mode="before"
    )
    @classmethod
    def reject_null(cls, value):
        if value is None:
            raise ValueError("Field cannot be null.")
        return value

    @field_validator("date")
    @classmethod
    def validate_date(
        cls,
        value: datetime.date | None
    ) -> datetime.date | None:
        if value is None:
            return value

        today = datetime.date.today()

        try:
            max_date = today.replace(year=today.year + 1)
        except ValueError:
            max_date = today.replace(
                year=today.year + 1,
                day=28
            )

        if value > max_date:
            raise ValueError(
                "Release date cannot be more than one year in the future."
            )

        return value
