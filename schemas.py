from typing import List, Optional, Generic, TypeVar
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl, conint, confloat, validator, root_validator
from pydantic.generics import GenericModel

T = TypeVar('T')

class Response(GenericModel, Generic[T]):
    success: bool = Field(..., example=True)
    message: Optional[str] = Field(None, example="Operation completed successfully")
    data: Optional[T] = Field(None)

class PaginatedResponse(GenericModel, Generic[T]):
    success: bool = Field(..., example=True)
    message: Optional[str] = Field(None)
    data: List[T] = Field(default_factory=list)
    total: int = Field(..., ge=0, example=0)
    page: int = Field(..., ge=1, example=1)
    size: int = Field(..., ge=1, example=10)

class LanguageEnum(str, Enum):
    en = "en"
    ru = "ru"
    be = "be"

class RouteDifficultyEnum(str, Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"

class Coordinates(BaseModel):
    lat: confloat(ge=-90, le=90) = Field(..., example=53.9006)
    lon: confloat(ge=-180, le=180) = Field(..., example=27.5590)

class RouteWaypoint(BaseModel):
    location: Coordinates
    description: str = Field(..., example="Saints Simon and Helena Church")

    @validator('description')
    def description_not_empty(cls, v):
        if not v.strip():
            raise ValueError('Waypoint description must not be empty')
        return v

class RouteBase(BaseModel):
    title: str = Field(..., example="Historic Minsk Tour")
    description: str = Field(..., example="A walking tour through Minsk historic sites")
    language: LanguageEnum = Field(..., example=LanguageEnum.en)
    waypoints: List[RouteWaypoint] = Field(..., min_items=2)
    difficulty: RouteDifficultyEnum = Field(..., example=RouteDifficultyEnum.easy)
    duration_minutes: conint(gt=0) = Field(..., example=120)
    distance_km: confloat(gt=0) = Field(..., example=5.0)
    tags: List[str] = Field(default_factory=list, example=["history", "walking"])

    @validator('title', 'description')
    def not_empty(cls, v):
        if not v.strip():
            raise ValueError('Field must not be empty')
        return v

class RouteCreate(RouteBase):
    pass

class RouteUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    language: Optional[LanguageEnum] = None
    waypoints: Optional[List[RouteWaypoint]] = None
    difficulty: Optional[RouteDifficultyEnum] = None
    duration_minutes: Optional[conint(gt=0)] = None
    distance_km: Optional[confloat(gt=0)] = None
    tags: Optional[List[str]] = None

    @validator('title', 'description')
    def not_empty(cls, v):
        if v is not None and not v.strip():
            raise ValueError('Field must not be empty')
        return v

    @validator('waypoints')
    def min_waypoints(cls, v):
        if v is not None and len(v) < 2:
            raise ValueError('At least two waypoints are required')
        return v

class RouteRead(RouteBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class UserBase(BaseModel):
    telegram_id: int = Field(..., example=123456789)
    username: Optional[str] = Field(None, example="john_doe")
    first_name: Optional[str] = Field(None, example="John")
    last_name: Optional[str] = Field(None, example="Doe")
    language: LanguageEnum = Field(..., example=LanguageEnum.en)

class UserCreate(UserBase):
    pass

class UserUpdate(BaseModel):
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    language: Optional[LanguageEnum] = None

    @validator('username', 'first_name', 'last_name')
    def not_empty_str(cls, v):
        if v is not None and not v.strip():
            raise ValueError('Field must not be empty')
        return v

class BadgeBase(BaseModel):
    name: str = Field(..., example="Explorer")
    description: str = Field(..., example="Visited 10 different locations")
    icon_url: HttpUrl = Field(..., example="https://example.com/badges/explorer.png")

class BadgeCreate(BadgeBase):
    pass

class BadgeRead(BadgeBase):
    id: int

    class Config:
        orm_mode = True

class ScratchMap(BaseModel):
    visited_regions: List[str] = Field(default_factory=list, example=["Minsk", "Brest"])
    updated_at: datetime

    class Config:
        orm_mode = True

class UserRead(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime
    badges: List[BadgeRead] = []
    points: int = Field(0, ge=0, example=100)
    scratch_map: ScratchMap

    class Config:
        orm_mode = True

class QuizQuestionBase(BaseModel):
    question_text: str = Field(..., example="What is the capital of Belarus?")
    options: List[str] = Field(..., min_items=2, example=["Minsk", "Gomel", "Brest"])
    explanation: Optional[str] = Field(None, example="Minsk has been the capital since 1919")
    category: Optional[str] = Field(None, example="geography")
    language: LanguageEnum = Field(..., example=LanguageEnum.en)
    tags: List[str] = Field(default_factory=list, example=["capital", "capital cities"])

    @validator('question_text')
    def question_not_empty(cls, v):
        if not v.strip():
            raise ValueError('Question text must not be empty')
        return v

class QuizQuestionCreate(QuizQuestionBase):
    correct_option_index: conint(ge=0) = Field(..., example=0)

    @root_validator
    def check_correct_option_index(cls, values):
        options = values.get('options')
        idx = values.get('correct_option_index')
        if options is not None and idx is not None and idx >= len(options):
            raise ValueError('correct_option_index must be less than number of options')
        return values

class QuizQuestionUpdate(BaseModel):
    question_text: Optional[str] = None
    options: Optional[List[str]] = None
    explanation: Optional[str] = None
    category: Optional[str] = None
    language: Optional[LanguageEnum] = None
    tags: Optional[List[str]] = None
    correct_option_index: Optional[conint(ge=0)] = None

    @validator('question_text')
    def question_not_empty(cls, v):
        if v is not None and not v.strip():
            raise ValueError('Question text must not be empty')
        return v

    @validator('options')
    def min_options(cls, v):
        if v is not None and len(v) < 2:
            raise ValueError('At least two options are required')
        return v

    @root_validator
    def check_correct_index_with_options(cls, values):
        options = values.get('options')
        idx = values.get('correct_option_index')
        if idx is not None and options is not None and idx >= len(options):
            raise ValueError('correct_option_index must be less than number of options')
        return values

class QuizQuestionRead(QuizQuestionBase):
    id: int

    class Config:
        orm_mode = True

class QuizAnswerCreate(BaseModel):
    user_id: int
    question_id: int
    selected_option_index: conint(ge=0)

class QuizAnswerRead(BaseModel):
    id: int
    user_id: int
    question_id: int
    selected_option_index: int
    correct: bool
    answered_at: datetime

    class Config:
        orm_mode = True

class LocationRecommendationBase(BaseModel):
    name: str = Field(..., example="Mir Castle")
    description: str = Field(..., example="A UNESCO World Heritage Site")
    location: Coordinates
    category: Optional[str] = Field(None, example="historical")
    tags: List[str] = Field(default_factory=list, example=["castle", "UNESCO"])
    language: LanguageEnum = Field(..., example=LanguageEnum.en)

    @validator('name', 'description')
    def name_not_empty(cls, v):
        if not v.strip():
            raise ValueError('Field must not be empty')
        return v

class LocationRecommendationCreate(LocationRecommendationBase):
    pass

class LocationRecommendationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    location: Optional[Coordinates] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    language: Optional[LanguageEnum] = None

    @validator('name', 'description')
    def not_empty(cls, v):
        if v is not None and not v.strip():
            raise ValueError('Field must not be empty')
        return v

class LocationRecommendationRead(LocationRecommendationBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True

class UserLocationUpdate(BaseModel):
    latitude: confloat(ge=-90, le=90)
    longitude: confloat(ge=-180, le=180)

class Token(BaseModel):
    access_token: str
    token_type: str = Field("bearer", example="bearer")