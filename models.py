import datetime
from sqlalchemy import Column, Integer, BigInteger, String, Text, Float, Boolean, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

class Language(Base):
    __tablename__ = 'languages'
    code = Column(String(10), primary_key=True)
    name = Column(String(255), nullable=False)
    native_name = Column(String(255))
    users = relationship('User', back_populates='language', cascade='all, delete-orphan')
    tour_routes = relationship('TourRoute', back_populates='language', cascade='all, delete-orphan')
    quizzes = relationship('Quiz', back_populates='language', cascade='all, delete-orphan')
    locations = relationship('Location', back_populates='language', cascade='all, delete-orphan')

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)
    username = Column(String(255))
    first_name = Column(String(255))
    last_name = Column(String(255))
    language_code = Column(String(10), ForeignKey('languages.code'), default='en', nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)

    language = relationship('Language', back_populates='users')
    badges = relationship('UserBadge', back_populates='user', cascade='all, delete-orphan')
    quiz_results = relationship('UserQuizResult', back_populates='user', cascade='all, delete-orphan')
    answers = relationship('UserAnswer', back_populates='user', cascade='all, delete-orphan')
    scratch_map = relationship('ScratchMap', uselist=False, back_populates='user', cascade='all, delete-orphan')
    recommendations = relationship('Recommendation', back_populates='user', cascade='all, delete-orphan')

class Chat(Base):
    __tablename__ = 'chats'
    id = Column(BigInteger, primary_key=True)
    type = Column(String(20))
    title = Column(String(255))
    username = Column(String(255))
    first_name = Column(String(255))
    last_name = Column(String(255))
    language_code = Column(String(10))
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)

class TourRoute(Base):
    __tablename__ = 'tour_routes'
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    language_code = Column(String(10), ForeignKey('languages.code'), nullable=False)
    published = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)

    language = relationship('Language', back_populates='tour_routes')
    points = relationship('RoutePoint', back_populates='route', cascade='all, delete-orphan')

class RoutePoint(Base):
    __tablename__ = 'route_points'
    id = Column(Integer, primary_key=True)
    route_id = Column(Integer, ForeignKey('tour_routes.id', ondelete='CASCADE'), nullable=False, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    description = Column(Text)
    order_index = Column(Integer, nullable=False)

    route = relationship('TourRoute', back_populates='points')

class Quiz(Base):
    __tablename__ = 'quizzes'
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    language_code = Column(String(10), ForeignKey('languages.code'), nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)

    language = relationship('Language', back_populates='quizzes')
    questions = relationship('Question', back_populates='quiz', cascade='all, delete-orphan')

class Question(Base):
    __tablename__ = 'questions'
    id = Column(Integer, primary_key=True)
    quiz_id = Column(Integer, ForeignKey('quizzes.id', ondelete='CASCADE'), nullable=False, index=True)
    text = Column(Text, nullable=False)
    order_index = Column(Integer, nullable=False)

    quiz = relationship('Quiz', back_populates='questions')
    choices = relationship('Choice', back_populates='question', cascade='all, delete-orphan')

class Choice(Base):
    __tablename__ = 'choices'
    id = Column(Integer, primary_key=True)
    question_id = Column(Integer, ForeignKey('questions.id', ondelete='CASCADE'), nullable=False, index=True)
    text = Column(Text, nullable=False)
    is_correct = Column(Boolean, default=False, nullable=False)

    question = relationship('Question', back_populates='choices')

class UserQuizResult(Base):
    __tablename__ = 'user_quiz_results'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    quiz_id = Column(Integer, ForeignKey('quizzes.id', ondelete='CASCADE'), nullable=False)
    score = Column(Integer, nullable=False)
    completed_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)

    user = relationship('User', back_populates='quiz_results')
    quiz = relationship('Quiz')

class UserAnswer(Base):
    __tablename__ = 'user_answers'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey('questions.id', ondelete='CASCADE'), nullable=False, index=True)
    choice_id = Column(Integer, ForeignKey('choices.id', ondelete='SET NULL'))
    answered_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint('user_id', 'question_id', name='uix_user_question_answer'),
    )

    user = relationship('User', back_populates='answers')
    question = relationship('Question')
    choice = relationship('Choice')

class Badge(Base):
    __tablename__ = 'badges'
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text)
    icon = Column(String(255))
    trigger_event = Column(String(100))
    criteria = Column(JSONB, default=dict)

    user_badges = relationship('UserBadge', back_populates='badge', cascade='all, delete-orphan')

class UserBadge(Base):
    __tablename__ = 'user_badges'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    badge_id = Column(Integer, ForeignKey('badges.id', ondelete='CASCADE'), nullable=False)
    awarded_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint('user_id', 'badge_id', name='uix_user_badge'),
    )

    user = relationship('User', back_populates='badges')
    badge = relationship('Badge', back_populates='user_badges')

class ScratchMap(Base):
    __tablename__ = 'scratch_maps'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False)
    progress = Column(JSONB, default=dict)
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship('User', back_populates='scratch_map')

class Location(Base):
    __tablename__ = 'locations'
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    latitude = Column(Float)
    longitude = Column(Float)
    category = Column(String(100))
    language_code = Column(String(10), ForeignKey('languages.code'), nullable=False)

    language = relationship('Language', back_populates='locations')
    recommendations = relationship('Recommendation', back_populates='location', cascade='all, delete-orphan')

class Recommendation(Base):
    __tablename__ = 'recommendations'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    location_id = Column(Integer, ForeignKey('locations.id', ondelete='CASCADE'), nullable=False, index=True)
    recommended_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint('user_id', 'location_id', name='uix_user_location'),
    )

    user = relationship('User', back_populates='recommendations')
    location = relationship('Location', back_populates='recommendations')