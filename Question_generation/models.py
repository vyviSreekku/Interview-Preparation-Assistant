from sqlalchemy import create_engine, Column, Integer, Float, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime
import os

Base = declarative_base()

class InterviewQA(Base):
    __tablename__ = 'interview_qa'

    id = Column(Integer, primary_key=True)
    user_id = Column(String(50), default="guest", nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=True)  # Answer can be null initially
    difficulty = Column(String(20), nullable=False)
    score = Column(Float, default=0.0, nullable=False)
    feedback = Column(Text, nullable=True)  # Feedback is optional
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    confidence_score = Column(Float, default=0.0, nullable=True)  # Speech confidence score
    confidence_feedback = Column(Text, nullable=True)  # Speech confidence feedback

# SQLite database file
db_path = 'interview.db'
engine = create_engine(f'sqlite:///{db_path}', connect_args={'check_same_thread': False})

# Create tables if they don't exist
Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
session = Session()
