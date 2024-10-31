from sqlalchemy import Column, Integer, String, DateTime, Boolean
from database import Base
from datetime import datetime

class User(Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False)
    password = Column(String(100), nullable=False)

class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    category_name = Column(String(100), nullable=False)
    description = Column(String(200), nullable=False)

class FridgeStock(Base):
    __tablename__ = "fridge_stocks"

    id = Column(Integer, primary_key=True, index=True)
    unit_name = Column(String(100))
    category = Column(String(100))
    description = Column(String(100))  
    quantity = Column(Integer)
    unit = Column(String(50))  
    price = Column(Integer)  
    expiration_date = Column(DateTime)
    added_date = Column(DateTime, default=datetime.now)  

class HistoryLog(Base):
    __tablename__ = "history_log"
    id = Column(Integer, primary_key=True, index=True)
    unit_name = Column(String(100), nullable=False)
    quantity = Column(Integer, nullable=False)
    added_date = Column(DateTime, default=datetime.now)  # Keeping the original date from fridge_stocks



class AlarmSchedule(Base):
    __tablename__ = 'alarm_schedules'
    
    id = Column(Integer, primary_key=True, index=True)
    alarm_time = Column(DateTime, nullable=False)  # Ensure this is DateTime
    label = Column(String, nullable=False)
    is_recurring = Column(Boolean, default=False)
    triggered_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
    
    