# השתמש בדימוי בסיסי של Python
FROM python:3.9-slim

# הגדר משתני סביבה כדי לייעל את הריצה
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# צור תיקייה לעבודה
WORKDIR /app

# העתק את קובץ ה-requirements.txt והתקן את הספריות
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# העתק את כל קבצי הבוט לתיקיית העבודה
COPY . .

# הפעל את הבוט
CMD ["python", "main.py"]
