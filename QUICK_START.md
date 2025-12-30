# 🚀 CodeVI - Quick Start Guide

## שלב 1: התקנת ספריות

פתח PowerShell או CMD והרץ:

```powershell
# עבור לתיקיית הפרויקט
cd "C:\Users\omert\New folder"

# התקן את כל הספריות (כולל החדשות)
pip install -r backend/requirements.txt
```

**הערה:** ההתקנה עלולה לקחת כמה דקות כי `sentence-transformers` מוריד מודל גדול.

## שלב 2: הרצת השרתים

### אופציה א' - הרצה אוטומטית (מומלץ):

```powershell
python run_all.py
```

זה יריץ:
- ✅ הכל על `http://localhost:8000`
  - Frontend: `http://localhost:8000`
  - API: `http://localhost:8000/api/v1`

### אופציה ב' - הרצה ידנית:

**טרמינל 1 - Backend:**
```powershell
cd backend
python main.py
```

**טרמינל 2 - Frontend:**
```powershell
cd frontend
python -m http.server 5500
```

## שלב 3: פתיחת האתר

פתח בדפדפן:
👉 **http://127.0.0.1:8000**

## שלב 4: סריקת קודבייס (BM25 - חיפוש רגיל)

1. באתר, הזן את הנתיב לקודבייס שלך (למשל: `C:\Users\omert\MyProject`)
2. לחץ על **"Scan Codebase"**
3. חכה לסיום הסריקה

## שלב 5: בניית אינדקס סמנטי (אופציונלי - לחיפוש חכם)

### דרך API:

```powershell
# PowerShell
$body = @{
    root_path = "C:\Users\omert\MyProject"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/v1/build_semantic_index" `
    -Method POST `
    -ContentType "application/json" `
    -Body $body
```

### דרך Frontend (אם תוסיף כפתור):

עדיין לא מוכן - צריך להוסיף כפתור ב-frontend.

## שלב 6: חיפוש

### חיפוש רגיל (BM25):
- השתמש ב-frontend או ב-API:
```powershell
$body = @{
    query = "login function"
    max_results = 10
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/v1/search" `
    -Method POST `
    -ContentType "application/json" `
    -Body $body
```

### חיפוש סמנטי (חכם):
```powershell
$body = @{
    query = "Where is authentication handled?"
    max_results = 5
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/v1/semantic_search" `
    -Method POST `
    -ContentType "application/json" `
    -Body $body
```

## 🔑 הגדרת OpenAI API Key (אופציונלי)

אם תרצה הסברים אוטומטיים בתוצאות החיפוש הסמנטי:

```powershell
# Windows PowerShell
$env:OPENAI_API_KEY="sk-your-api-key-here"

# או ב-CMD
set OPENAI_API_KEY=sk-your-api-key-here
```

**הערה:** ללא API Key, החיפוש הסמנטי יעבוד אבל לא יהיו הסברים.

## 🐛 פתרון בעיות

### שגיאת Port תפוס:
```powershell
# הרץ את זה כדי לשחרר את הפורט
.\kill_port_8000.bat
```

### שגיאת ModuleNotFoundError:
```powershell
# ודא שהתקנת את כל הספריות
pip install -r backend/requirements.txt
```

### שגיאת OpenAI:
- אם אין לך API Key, זה בסדר - החיפוש הסמנטי יעבוד בלי הסברים
- אם יש לך API Key, ודא שהגדרת את המשתנה `OPENAI_API_KEY`

## 📝 סיכום

1. ✅ `pip install -r backend/requirements.txt`
2. ✅ `python run_all.py`
3. ✅ פתח `http://127.0.0.1:5500`
4. ✅ סרוק קודבייס דרך האתר
5. ✅ (אופציונלי) בנה אינדקס סמנטי דרך API
6. ✅ חפש!

## 🎯 מה עובד עכשיו?

- ✅ חיפוש BM25 (חיפוש רגיל לפי מילות מפתח)
- ✅ חיפוש סמנטי (חיפוש חכם לפי משמעות)
- ✅ גרף קשרים (Related Files)
- ✅ Frontend מלא עם UI יפה

## 🚧 מה עדיין לא מוכן?

- ⏳ כפתור "Build Semantic Index" ב-frontend
- ⏳ כפתור "Semantic Search" ב-frontend
- ⏳ תצוגת הסברים בתוצאות החיפוש הסמנטי

