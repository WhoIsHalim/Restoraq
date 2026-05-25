# Restoraq - Multi-tenant Restaurant POS SaaS

**[English](#english) | [العربية](#arabic)**

---

<a name="english"></a>
## 🇬🇧 English

Django modular monolith for restaurant POS, subscriptions, feature flags, inventory, reporting, printing, and audit logging.

### Docker Quick Start (Recommended)
To run the application easily on any machine via containers:

1. Clone the repository and navigate to the project directory.
2. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
   *(Note: Ensure your database credentials in `.env` match the defaults or update `docker-compose.yml` accordingly).*
3. Run with Docker Compose:
   ```bash
   docker-compose up --build
   ```
4. In another terminal, run initial setup:
   ```bash
   docker-compose exec web python manage.py migrate
   docker-compose exec web python manage.py seed_roles
   docker-compose exec web python manage.py seed_plans
   docker-compose exec web python manage.py seed_features
   docker-compose exec web python manage.py createsuperuser
   ```
5. The app will be available at `http://localhost:8000`

### Local Setup (Without Docker)

1. Create virtual environment and install dependencies:
   - Windows: `python -m venv .venv` then `.venv\Scripts\activate`
   - Mac/Linux: `python3 -m venv .venv` then `source .venv/bin/activate`
   - `pip install -r requirements.txt`

2. Configure env:
   - `cp .env.example .env` (or `copy .env.example .env` on Windows)

3. Run setup:
   - `python manage.py migrate`
   - `python manage.py seed_roles`
   - `python manage.py seed_plans`
   - `python manage.py seed_features`
   - `python manage.py createsuperuser`

4. Run app:
   - `python manage.py runserver`

### System Admin Quick Actions

- System dashboard: `/system/`
- Create new restaurant tenant from UI: `/system/tenants/new/`
- Website (marketing) is isolated from the internal workspace:
  - Public site: `/`, `/features/`, `/pricing/`
  - Login workspace: `/accounts/login/`
  - After login:
    - System roles -> `/system/`
    - Restaurant users -> `/dashboard/`
- System admin can enter a specific restaurant workspace from:
  - `/system/tenants/<slug>/` -> click **Enter This Tenant**
  - Then open `/dashboard/` to operate inside that tenant context.
- Default website language is Arabic (`ar`) for first visit; users can switch to English from top navbar.
- Public website content on home/features/pricing is loaded from `helping-data/*.txt` when available.
- System pages are fully bilingual (Arabic/English) based on the selected user language.

### Optional Commands

- Manual backup: `python manage.py backup_run`
- Build full Pro demo dataset (tenant, branches, users, menu, inventory, orders, printing, reports):
  - `python manage.py seed_demo_pro --reset`
- Run demo smoke test (UI pages + key APIs + data checks):
  - `python manage.py demo_smoke_test`

### Production Baseline

- Gunicorn + Nginx
- PostgreSQL + Redis
- Celery worker + beat
- Docker Compose: `docker-compose.prod.yml`

---

<a name="arabic"></a>
## 🇸🇦 العربية

# ريستوراك (Restoraq) - نظام نقاط بيع (POS) للمطاعم بنظام SaaS متعدد المستأجرين

مشروع مبني بإطار عمل Django يعمل كنظام نقاط بيع للمطاعم، ويدعم الاشتراكات، وإدارة الميزات (Feature flags)، والمخزون، والتقارير، والطباعة، وسجل التدقيق (Audit logging).

### البدء السريع عبر الحاويات (Docker) - موصى به

لتشغيل المشروع بسهولة على أي جهاز باستخدام Docker:

1. قم بنسخ ملف البيئة الأساسي:
   ```bash
   cp .env.example .env
   ```
2. تشغيل الحاويات:
   ```bash
   docker-compose up --build
   ```
3. في نافذة أوامر (Terminal) أخرى، قم بتشغيل الإعداد الأولي:
   ```bash
   docker-compose exec web python manage.py migrate
   docker-compose exec web python manage.py seed_roles
   docker-compose exec web python manage.py seed_plans
   docker-compose exec web python manage.py seed_features
   docker-compose exec web python manage.py createsuperuser
   ```
4. يمكنك الوصول للتطبيق عبر الرابط `http://localhost:8000`

### التشغيل المحلي (بدون Docker)

1. إنشاء بيئة افتراضية وتثبيت المتطلبات:
   - `python -m venv .venv`
   - تفعيل البيئة (ويندوز): `.venv\Scripts\activate` أو (ماك/لينكس): `source .venv/bin/activate`
   - `pip install -r requirements.txt`
2. تهيئة المتغيرات: `cp .env.example .env`
3. تشغيل أوامر التهيئة (انظر أوامر الإعداد في القسم الإنجليزي).
4. تشغيل الخادم: `python manage.py runserver`

### إجراءات سريعة لمدير النظام

- لوحة تحكم النظام: `/system/`
- إنشاء مستأجر/مطعم جديد من الواجهة: `/system/tenants/new/`
- الموقع التعريفي معزول عن مساحة العمل الداخلية:
  - الموقع العام: `/`, `/features/`, `/pricing/`
  - مساحة عمل تسجيل الدخول: `/accounts/login/`
  - بعد تسجيل الدخول:
    - أدوار النظام -> `/system/`
    - مستخدمو المطعم -> `/dashboard/`
- يمكن لمدير النظام الدخول إلى مساحة عمل مطعم معين من:
  - `/system/tenants/<slug>/` -> انقر **Enter This Tenant**
  - ثم افتح `/dashboard/` للعمل داخل سياق هذا المستأجر.
- اللغة الافتراضية للموقع هي العربية (`ar`) للزيارة الأولى؛ يمكن للمستخدمين التبديل للإنجليزية من الشريط العلوي.
- صفحات النظام ثنائية اللغة بالكامل (عربي/إنجليزي).

### أوامر إضافية

- النسخ الاحتياطي اليدوي: `python manage.py backup_run`
- إنشاء بيانات تجريبية كاملة لباقة Pro:
  - `python manage.py seed_demo_pro --reset`
- إجراء اختبارات الدخان (Smoke test):
  - `python manage.py demo_smoke_test`

### بنية الإنتاج

- Gunicorn + Nginx
- PostgreSQL + Redis
- Celery worker + beat
- تشغيل الإنتاج عبر حاويات: `docker-compose.prod.yml`
