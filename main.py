from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from models import Base, User, Category, FridgeStock, HistoryLog
from database import engine, get_db
from datetime import datetime
from datetime import timedelta
from sqlalchemy import func
from models import AlarmSchedule
from pydantic import BaseModel
from typing import Optional
from apscheduler.schedulers.background import BackgroundScheduler





# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI()

scheduler = BackgroundScheduler()


def check_alarms(db: Session):
    current_time = datetime.now()
    
    # Query alarms that are due to go off
    due_alarms = db.query(AlarmSchedule).filter(
        AlarmSchedule.alarm_time <= current_time
    ).all()

    for alarm in due_alarms:
        print(f"Alarm triggered: {alarm.label} at {alarm.alarm_time}")

        alarm.triggered_count += 1

        
        if alarm.triggered_count >= 3:
            if alarm.is_recurring:
                
                alarm.daily_recurrence = True
                alarm.alarm_time = current_time + timedelta(days=1)
            else:
                db.delete(alarm)
        else:
            
            if not alarm.is_recurring:
                db.delete(alarm)
            else:
                
                alarm.alarm_time = current_time + timedelta(days=1)

        db.commit()


scheduler.add_job(lambda: check_alarms(next(get_db())), 'interval', minutes=1)
scheduler.start()


# Pydantic model for update
class UpdateAlarmSchedule(BaseModel):
    alarm_time: Optional[datetime] = None
    label: Optional[str] = None
    is_recurring: Optional[bool] = None

class AlarmScheduleCreate(BaseModel):
    alarm_time: datetime
    label: Optional[str] = None
    is_recurring: Optional[bool] = False
    triggered_count: Optional[int] = 0  


# 1. REGISTER a new user
@app.post("/register/")
def register(username: str, password: str, db: Session = Depends(get_db)):
    user = User(username=username, password=password)
    db.add(user)
    db.commit()
    return {"msg": "User created successfully"}

# 2. LOGIN a user (simple)
@app.post("/login/")
def login(username: str, password: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username, User.password == password).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid credentials")
    return {"msg": "Login successful"}

# 3. CREATE a new category
@app.post("/categories/")
def create_category(category_name: str, description: str, db: Session = Depends(get_db)):
    category = Category(category_name=category_name, description=description)
    db.add(category)
    db.commit()
    return {"msg": "Category created"}

# 4. VIEW all categories
@app.get("/categories/")
def get_categories(db: Session = Depends(get_db)):
    return db.query(Category).all()

# 5. UPDATE a category
@app.put("/categories/{category_id}")
def update_category(category_id: int, category_name: str, description: str, db: Session = Depends(get_db)):
    category = db.query(Category).filter(Category.id == category_id).first()
    if category:
        category.category_name = category_name
        category.description = description
        db.commit()
        return {"msg": "Category updated"}
    raise HTTPException(status_code=404, detail="Category not found")

# 6. DELETE a category
@app.delete("/categories/{category_id}")
def delete_category(category_id: int, db: Session = Depends(get_db)):
    category = db.query(Category).filter(Category.id == category_id).first()
    if category:
        db.delete(category)
        db.commit()
        return {"msg": "Category deleted"}
    raise HTTPException(status_code=404, detail="Category not found")

# 7. CREATE a fridge stock
@app.post("/fridge_stocks/")
def create_stock(unit_name: str, category: str, description: str, quantity: int, unit: str, price: float, expiration_date: datetime, db: Session = Depends(get_db)):
    stock = FridgeStock(
        unit_name=unit_name,
        category=category,
        description=description,  # Add description
        quantity=quantity,
        unit=unit,  # Add unit (like kg, liters, etc.)
        price=price,
        expiration_date=expiration_date,
        added_date=datetime.now()  # Timestamp for when the stock is added
    )
    db.add(stock)
    db.commit()
    return {"msg": "Stock added"}


# 8. VIEW all fridge stocks
@app.get("/fridge_stocks/")
def get_stocks(db: Session = Depends(get_db)):
    return db.query(FridgeStock).all()

# 9. UPDATE fridge stock
@app.put("/fridge_stocks/{stock_id}")
def update_stock(stock_id: int, unit_name: str, quantity: int, db: Session = Depends(get_db)):
    stock = db.query(FridgeStock).filter(FridgeStock.id == stock_id).first()
    if stock:
        stock.unit_name = unit_name
        stock.quantity = quantity
        db.commit()
        return {"msg": "Stock updated"}
    raise HTTPException(status_code=404, detail="Stock not found")

# 10. DELETE fridge stock
@app.delete("/fridge_stocks/{stock_id}")
def delete_stock(stock_id: int, db: Session = Depends(get_db)):
    # Fetch the stock that needs to be deleted
    stock = db.query(FridgeStock).filter(FridgeStock.id == stock_id).first()
    
    if not stock:
        return {"msg": "Stock not found"}
    
    # Create a history log entry before deleting the stock
    history_log = HistoryLog(
        unit_name=stock.unit_name,
        quantity=stock.quantity,
        added_date=stock.added_date  # Keeping the original added_date from fridge stock
    )
    
    # Add history log to the database
    db.add(history_log)
    
    # Delete the stock from the fridge
    db.delete(stock)
    db.commit()
    
    return {"msg": "Stock deleted and history logged"}

# 11. Reduce fridge stock and log it
@app.post("/fridge_stocks/{stock_id}/reduce")
def reduce_stock(stock_id: int, quantity: int, db: Session = Depends(get_db)):
    stock = db.query(FridgeStock).filter(FridgeStock.id == stock_id).first()
    if stock and stock.quantity >= quantity:
        stock.quantity -= quantity
        log = HistoryLog(unit_name=stock.unit_name, quantity=quantity)
        db.add(log)
        db.commit()
        return {"msg": "Stock reduced and logged"}
    raise HTTPException(status_code=400, detail="Not enough stock")

# 12. View total fridge stock quantity
@app.get("/fridge_stocks/total")
def total_stocks(db: Session = Depends(get_db)):
    total = db.query(FridgeStock).with_entities(func.sum(FridgeStock.quantity)).scalar()
    return {"total_stock": total}

#13. View total number of categories
@app.get("/categories/total")
def total_categories(db: Session = Depends(get_db)):
    total = db.query(Category).count()
    return {"total_categories": total}



#14. View fridge stocks with less than 1 month left before expiration
@app.get("/fridge_stocks/expiring_soon")
def expiring_soon(db: Session = Depends(get_db)):
    today = datetime.utcnow()
    one_month_later = today + timedelta(days=30)
    
    expiring_stocks = db.query(FridgeStock).filter(
        FridgeStock.expiration_date <= one_month_later
    ).all()
    
    return {"expiring_soon": expiring_stocks}


#15. View total price of fridge stocks added in the last 15 days
@app.get("/fridge_stocks/total_price_15_days")
def total_price_15_days(db: Session = Depends(get_db)):
    today = datetime.now()
    fifteen_days_ago = today - timedelta(days=15)

    # Query for total price of stocks added in the last 15 days
    total_price = db.query(func.sum(FridgeStock.price)).filter(
        FridgeStock.added_date >= fifteen_days_ago
    ).scalar()

    return {"total_price_last_15_days": total_price or 0}  # Return 0 if no stocks found

#16.Retrieve all history log records
@app.get("/history_log/")
def get_history(db: Session = Depends(get_db)):
    history_logs = db.query(HistoryLog).all()  # Retrieve all history log records
    return history_logs





#17.create alarm_schedules
@app.post("/alarm_schedules/")
def create_alarm_schedule(alarm_data: AlarmScheduleCreate, db: Session = Depends(get_db)):
    new_alarm_schedule = AlarmSchedule(
        alarm_time=alarm_data.alarm_time,
        label=alarm_data.label,
        is_recurring=alarm_data.is_recurring,
        triggered_count=alarm_data.triggered_count,  # Include triggered_count here
    )
    
    db.add(new_alarm_schedule)
    db.commit()
    db.refresh(new_alarm_schedule)

    return {"msg": "Alarm schedule created", "alarm_schedule": new_alarm_schedule}

#18.view alarm_schedules
@app.get("/alarm_schedules/")
def get_all_alarm_schedules(db: Session = Depends(get_db)):
    alarm_schedules = db.query(AlarmSchedule).all()
    return alarm_schedules

#19.view alarm_schedules
@app.get("/alarm_schedules/{alarm_id}")
def get_alarm_schedule(alarm_id: int, db: Session = Depends(get_db)):
    alarm_schedule = db.query(AlarmSchedule).filter(AlarmSchedule.id == alarm_id).first()
    if alarm_schedule is None:
        return {"error": "Alarm schedule not found"}
    return alarm_schedule

#20. Update an existing alarm schedule by ID
@app.put("/alarm_schedules/{alarm_id}")
def update_alarm_schedule(alarm_id: int, alarm_data: UpdateAlarmSchedule, db: Session = Depends(get_db)):
    # Query the database for the alarm schedule with the provided ID
    alarm_schedule = db.query(AlarmSchedule).filter(AlarmSchedule.id == alarm_id).first()

    # If the alarm schedule does not exist, raise a 404 error
    if alarm_schedule is None:
        raise HTTPException(status_code=404, detail="Alarm schedule not found")

    # Update fields only if provided in the request body
    if alarm_data.alarm_time is not None:
        alarm_schedule.alarm_time = alarm_data.alarm_time
    if alarm_data.label is not None:
        alarm_schedule.label = alarm_data.label
    if alarm_data.is_recurring is not None:
        alarm_schedule.is_recurring = alarm_data.is_recurring

    # Commit the changes to the database
    db.commit()
    db.refresh(alarm_schedule)  # Refresh the updated object from the DB to return the latest data

    # Return the updated alarm schedule along with a success message
    return {"msg": "Alarm schedule updated", "alarm_schedule": alarm_schedule}


#21. Delete an alarm schedule by ID
@app.delete("/alarm_schedules/{alarm_id}")
def delete_alarm_schedule(alarm_id: int, db: Session = Depends(get_db)):
    alarm_schedule = db.query(AlarmSchedule).filter(AlarmSchedule.id == alarm_id).first()

    if alarm_schedule is None:
        raise HTTPException(status_code=404, detail="Alarm schedule not found")

    db.delete(alarm_schedule)
    db.commit()

    return {"msg": "Alarm schedule deleted", "alarm_id": alarm_id}