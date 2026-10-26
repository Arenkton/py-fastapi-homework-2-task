from fastapi import APIRouter, Depends, HTTPException, Query, Request, Body, Response
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from pydantic import ValidationError

from database import get_db, MovieModel
from database.models import CountryModel, GenreModel, ActorModel, LanguageModel
from schemas.movies import (
    MovieListResponseSchema,
    MovieCreateSchema,
    MovieDetailSchema,
    MovieUpdateSchema,
)

router = APIRouter()


@router.get("/movies/", response_model=MovieListResponseSchema)
async def get_movies(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
):
    total_items = await db.scalar(
        select(func.count()).select_from(MovieModel)
    )

    query = (
        select(MovieModel)
        .order_by(MovieModel.id.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )

    result = await db.execute(query)
    movies = result.scalars().all()

    if not movies:
        raise HTTPException(
            status_code=404,
            detail="No movies found."
        )

    total_pages = (total_items + per_page - 1) // per_page

    base_url = request.url.path.replace("/api/v1", "", 1)

    prev_page = (
        f"{base_url}?page={page - 1}&per_page={per_page}"
        if page > 1 else None
    )

    next_page = (
        f"{base_url}?page={page + 1}&per_page={per_page}"
        if page < total_pages else None
    )

    return {
        "movies": movies,
        "prev_page": prev_page,
        "next_page": next_page,
        "total_pages": total_pages,
        "total_items": total_items,
    }


@router.post(
    "/movies/",
    response_model=MovieDetailSchema,
    status_code=201
)
async def create_movie(
    payload: dict = Body(...),
    db: AsyncSession = Depends(get_db),
):
    try:
        data = MovieCreateSchema.model_validate(payload)
    except ValidationError:
        raise HTTPException(
            status_code=400,
            detail="Invalid input data."
        )

    existing_movie = await db.scalar(
        select(MovieModel).where(
            MovieModel.name == data.name,
            MovieModel.date == data.date
        )
    )

    if existing_movie:
        raise HTTPException(
            status_code=409,
            detail=(
                f"A movie with the name '{data.name}' "
                f"and release date '{data.date}' already exists."
            )
        )

    country = await db.scalar(
        select(CountryModel).where(
            CountryModel.code == data.country
        )
    )

    if country is None:
        country = CountryModel(
            code=data.country,
            name=None
        )
        db.add(country)

    async def get_or_create(model, names):
        entities = []

        for name in dict.fromkeys(names):
            entity = await db.scalar(
                select(model).where(model.name == name)
            )

            if entity is None:
                entity = model(name=name)
                db.add(entity)

            entities.append(entity)

        return entities

    genres = await get_or_create(GenreModel, data.genres)
    actors = await get_or_create(ActorModel, data.actors)
    languages = await get_or_create(LanguageModel, data.languages)

    movie = MovieModel(
        name=data.name,
        date=data.date,
        score=data.score,
        overview=data.overview,
        status=data.status,
        budget=data.budget,
        revenue=data.revenue,
        country=country,
        genres=genres,
        actors=actors,
        languages=languages
    )

    db.add(movie)

    try:
        await db.flush()
        movie_id = movie.id
        await db.commit()

    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Invalid input data."
        )

    result = await db.execute(
        select(MovieModel)
        .options(
            selectinload(MovieModel.country),
            selectinload(MovieModel.genres),
            selectinload(MovieModel.actors),
            selectinload(MovieModel.languages)
        )
        .where(MovieModel.id == movie_id)
    )

    return result.scalar_one()


@router.get(
    "/movies/{movie_id}/",
    response_model=MovieDetailSchema
)
async def get_movie(
    movie_id: int,
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(MovieModel)
        .options(
            selectinload(MovieModel.country),
            selectinload(MovieModel.genres),
            selectinload(MovieModel.actors),
            selectinload(MovieModel.languages)
        )
        .where(MovieModel.id == movie_id)
    )

    result = await db.execute(query)
    movie = result.scalar_one_or_none()

    if movie is None:
        raise HTTPException(
            status_code=404,
            detail="Movie with the given ID was not found."
        )

    return movie


@router.delete(
    "/movies/{movie_id}/",
    status_code=204
)
async def delete_movie(
    movie_id: int,
    db: AsyncSession = Depends(get_db),
):
    movie = await db.get(MovieModel, movie_id)

    if movie is None:
        raise HTTPException(
            status_code=404,
            detail="Movie with the given ID was not found."
        )

    await db.delete(movie)
    await db.commit()

    return Response(status_code=204)


@router.patch("/movies/{movie_id}/")
async def update_movie(
    movie_id: int,
    payload: dict = Body(...),
    db: AsyncSession = Depends(get_db),
):
    movie = await db.get(MovieModel, movie_id)

    if movie is None:
        raise HTTPException(
            status_code=404,
            detail="Movie with the given ID was not found."
        )

    try:
        data = MovieUpdateSchema.model_validate(payload)
        update_data = data.model_dump(exclude_unset=True)
    except ValidationError:
        raise HTTPException(
            status_code=400,
            detail="Invalid input data."
        )

    for field, value in update_data.items():
        setattr(movie, field, value)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Invalid input data."
        )

    return {"detail": "Movie updated successfully."}
