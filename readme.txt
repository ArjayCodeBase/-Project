to run the main.py
uvicorn main:app --reload

create a env
python -m venv myenv
myenv\Scripts\activate
pip install fastapi
pip install sqlalchemy 
pip install uvicorn
pip install apscheduler


{
  "alarm_time": "2024-09-19T07:30:00",
  "label": "Morning workout",
  "is_recurring": true
}
